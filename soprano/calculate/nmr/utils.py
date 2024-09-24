# Soprano - a library to crack crystals! by Simone Sturniolo
# Copyright (C) 2016 - Science and Technology Facility Council

# Soprano is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Soprano is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Helper functions for NMR calculations and plotting
"""

import logging
from ase import Atoms
import numpy as np
from scipy.optimize import minimize
from functools import wraps
from pkg_resources import resource_filename
from dataclasses import dataclass
import matplotlib
from typing import List, Tuple, Optional

from soprano.properties.labeling.labeling import MagresViewLabels
from soprano.utils import has_cif_labels

def get_force_matrix(
            positions: np.ndarray,
            positions_original: np.ndarray,
            C:float = 0.01,
            k:float = 0.00001):
    '''
    This is a vectorised version of the above function, which is much faster

    Parameters
    ----------
    positions : np.array
        The y coordinates of the annotations
    positions_original : np.array
        The original y coordinates of the annotations
    C : float, optional
        The repulsive force constant between annotations, by default 0.01
    k : float, optional
        The spring force constant for the spring holding the annotation to it's original position, by default 0.00001

    '''
    Fmat = np.zeros((len(positions), len(positions)))
    # force from other annotations -- ignore the diagonal elements
    displacement_matrix = positions[:, np.newaxis] - positions[np.newaxis, :]
    diag_mask = np.eye(displacement_matrix.shape[0],dtype=bool)
    off_diag_mask = ~diag_mask

    # for any non-zero displacements, calculate the repulsive force
    non_zero_displacements = np.abs(displacement_matrix) > 1e-8
    off_diag_mask = np.logical_and(off_diag_mask, non_zero_displacements)
    # Fmat[off_diag_mask][non_zero_displacements] = -C * displacement_matrix[off_diag_mask][non_zero_displacements] / (np.abs(displacement_matrix[off_diag_mask][non_zero_displacements]))**3
    
    Fmat[off_diag_mask] += C * displacement_matrix[off_diag_mask] / (np.abs(displacement_matrix[off_diag_mask]))**4

    # if any off-diagonal elements are zero, then set a random force
    zero_off_diag_mask = np.logical_and(off_diag_mask, ~non_zero_displacements)
    # count the number of zero displacements
    if np.sum(zero_off_diag_mask) > 0:
        Fmat[zero_off_diag_mask] = np.random.randn(np.sum(zero_off_diag_mask)) * C * (1/0.05**2)
    # spring force from original position
    Fmat[diag_mask] = -2*k * (positions - positions_original)
    return Fmat

def get_total_forces(
            positions: np.ndarray,
            positions_original: np.ndarray,
            C:float = 0.01,
            k:float = 0.00001):
    '''
    Parameters
    ----------
    positions : np.array
        The y coordinates of the annotations
    positions_original : np.array
        The original y coordinates of the annotations
    C : float, optional
        The repulsive force constant between annotations, by default 0.01
    k : float, optional
        The spring force constant for the spring holding the annotation to it's original position, by default 0.00001
    '''
    Fmat = get_force_matrix(positions, positions_original, C, k)
    # sum over the columns to get the total force on each annotation
    return np.sum(Fmat, axis=1)

def get_total_forces(
            positions: np.ndarray,
            positions_original: np.ndarray,
            C:float = 0.01,
            k:float = 0.00001):
    '''
    Parameters
    ----------
    positions : np.array
        The y coordinates of the annotations
    positions_original : np.array
        The original y coordinates of the annotations
    C : float, optional
        The repulsive force constant between annotations, by default 0.01
    k : float, optional
        The spring force constant for the spring holding the annotation to it's original position, by default 0.00001
    '''
    sign = -1 # trial and error to get the right sign wrt the energy..
    Fmat = sign * get_force_matrix(positions, positions_original, C, k)
    # sum over the columns to get the total force on each annotation
    return np.sum(Fmat, axis=1)
def get_energy(positions, positions_original, C, k):
    '''
    Compute the total energy of the system

    '''
    # compute the energy
    # coulomb energy is the sum of the coulomb energy between each pair of annotations
    # spring energy is the sum of the spring energy for each annotation
    coulomb_energy = 0
    for i in range(len(positions)):
        for j in range(i+1, len(positions)):
            if np.abs(positions[i] - positions[j]) > 1e-8:
                coulomb_energy += C / np.abs(positions[i] - positions[j])**2

    

    spring_energy = 0.5 * k * np.sum((positions - positions_original)**2)
    # print(f'coulomb_energy: {coulomb_energy}, spring_energy: {spring_energy}')
    energy = spring_energy + coulomb_energy
    return energy


def optimise_annotations(positions, max_iters=10000, C=0.01, k=0.00001, ftol = 1e-3):
    '''
    Parameters
    ----------
    positions : list or np.array
        The x or y coordinates of the annotations to be optimised
    max_iters : int, optional
        The maximum number of iterations to run for, by default 10000
    C : float, optional
        The repulsive force constant between annotations, by default 0.01
    k : float, optional
        The spring force constant for the spring holding the annotation to it's original position, by default 0.00001
    ftol : float, optional
        The tolerance for the forces, by default 1e-3. If all the net forces are below this value, the optimisation will stop
        even if the maximum number of iterations has not been reached.

    '''
    if len(positions) < 3:
        return positions
    # convert to numpy array
    positions = np.array(positions)
    # store original order
    order =  np.argsort(positions)
    # invert order
    inverted_order = np.argsort(order)

    # sort positions 
    positions = positions[order]
    ## deep copy of the sorted positions
    positions_original = positions.copy()

    # normalise the positions to the range of the original positions
    original_range = np.max(positions_original) - np.min(positions_original)
    min_pos = np.min(positions_original)
    positions = (positions - np.min(positions_original)) / original_range
    positions_original = (positions_original - min_pos) / original_range

    res = minimize(
            get_energy,
            positions,
            args=(positions_original, C, k),
            jac = get_total_forces,
            # method='BFGS',
            options={'disp': False, 'maxiter':max_iters},
            tol=ftol,
            # add a constraint to keep the first and last annotation in the same place
            constraints = [
                {'type': 'eq', 'fun': lambda x: x[0] - positions_original[0]},
                {'type': 'eq', 'fun': lambda x: x[-1] - positions_original[-1]},
                # another set of constraints to keep all values between 0 and 1 in fractional space
                {'type': 'ineq', 'fun': lambda x: x},
                {'type': 'ineq', 'fun': lambda x: 1-x},
            ]
        )
    new_pos_frac = res.x
    
    # convert back to original range
    new_pos = new_pos_frac * original_range + min_pos
    positions = new_pos





    # return to original order
    positions = positions[inverted_order]
    return positions



@dataclass
class Peak2D:
    '''
    Class to hold peak data. This is used to store the peak data for a correlation peak in a 2D NMR spectrum.

    The data stored includes:
    - the peak position in x and y
    - the correlation strength
    - the x and y labels for the peak
    - the color of the peak
    - the index of the x and y labels in the list of all labels

    '''  
    x: float
    y: float
    xlabel: str
    ylabel: str
    correlation_strength: float = 1
    color: str = 'C0'
    idx_x: Optional[int] = None
    idx_y: Optional[int] = None

    def __repr__(self):
        return f'Peak({self.x}, {self.y}, {self.correlation_strength}, {self.xlabel}, {self.ylabel}, {self.color})'
    
    def equivalent_to(self, other, xtol=0.005, ytol=0.005, corr_tol=0.1, ignore_correlation_strength=False):
        '''
        Check if two peaks are equivalent. We compare the x and y coordinates and the correlation strength.

        Args:
            other (Peak2D): The other peak to compare to
            xtol (float, optional): The tolerance for the x coordinate. Defaults to 0.005.
            ytol (float, optional): The tolerance for the y coordinate. Defaults to 0.005.
            corr_tol (float, optional): The tolerance for the correlation strength. Defaults to 0.1.
        
        Returns:
            bool: True if the peaks are equivalent, False otherwise
        '''
        x_match = np.abs(self.x - other.x) < xtol
        y_match = np.abs(self.y - other.y) < ytol
        
        if ignore_correlation_strength:
            corr_match = True
        else:
            corr_match = np.abs(self.correlation_strength - other.correlation_strength) < corr_tol

        return x_match and y_match and corr_match

        


def lorentzian(X: np.ndarray, x0: float, Y: np.ndarray, y0: float, x_broadening: float, y_broadening: float) -> np.ndarray:
    """
    Calculate the Lorentzian broadening function.

    .. math::
        f(x, y) = \\frac{1}{((x - x_0) / w_x)^2 + ((y - y_0) / w_y)^2 + 1}

    where :math:`w_x` and :math:`w_y` are the broadening factors in the x and y directions, respectively. These
    correspond to the half-width at half-maximum (HWHM) of the Lorentzian function.

    Args:
        X (np.ndarray): Array of x values.
        x0 (float): x-coordinate of the peak.
        Y (np.ndarray): Array of y values.
        y0 (float): y-coordinate of the peak.
        x_broadening (float): Broadening factor in the x direction.
        y_broadening (float): Broadening factor in the y direction.

    Returns:
        np.ndarray: Array of intensity values.
    """
    return np.exp(-((X - x0)**2 / (2 * x_broadening**2) + (Y - y0)**2 / (2 * y_broadening**2)))

def gaussian(X: np.ndarray, x0: float, Y: np.ndarray, y0: float, x_broadening: float, y_broadening: float) -> np.ndarray:
    """
    Calculate the Gaussian broadening function.

    .. math::
        f(x, y) = \\exp\\left(-\\frac{(x - x_0)^2}{2 w_x^2} - \\frac{(y - y_0)^2}{2 w_y^2}\\right)

    where :math:`w_x` and :math:`w_y` are the broadening factors in the x and y directions, respectively. These
    correspond to the standard deviation of the Gaussian function.

    Args:
        X (np.ndarray): Array of x values.
        x0 (float): x-coordinate of the peak.
        Y (np.ndarray): Array of y values.
        y0 (float): y-coordinate of the peak.
        x_broadening (float): Broadening factor in the x direction.
        y_broadening (float): Broadening factor in the y direction.

    Returns:
        np.ndarray: Array of intensity values.
    """
    return np.exp(-((X - x0)**2 / (2 * x_broadening**2) + (Y - y0)**2 / (2 * y_broadening**2)))

def generate_contour_map(
    peaks: List[Peak2D], 
    grid_size: int = 100, 
    broadening: str = 'gaussian', 
    x_broadening: float = 1.0, 
    y_broadening: float = 1.0, 
    xlims: Optional[Tuple[float, float]] = None, 
    ylims: Optional[Tuple[float, float]] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate a contour map based on the provided peaks and broadening parameters.

    Args:
        peaks (List[Peak2D]): List of Peak2D objects containing x, y coordinates and correlation strength.
        grid_size (int, optional): Size of the grid for the contour map. Default is 100.
        broadening (str, optional): Type of broadening function to use ('lorentzian' or 'gaussian'). Default is 'lorentzian'.
        x_broadening (float, optional): Broadening factor in the x direction. Default is 1.0.
        y_broadening (float, optional): Broadening factor in the y direction. Default is 1.0.
        xlims (Optional[Tuple[float, float]], optional): Limits for the x-axis. Default is None.
        ylims (Optional[Tuple[float, float]], optional): Limits for the y-axis. Default is None.

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: Meshgrid arrays X, Y and the intensity grid Z.
    """
    broadening = broadening.lower()
    # Create a grid of x, y values
    if xlims is None:
        x_min, x_max = min(peak.x for peak in peaks), max(peak.x for peak in peaks)
    else:
        x_min, x_max = xlims
    if ylims is None:
        y_min, y_max = min(peak.y for peak in peaks), max(peak.y for peak in peaks)
    else:
        y_min, y_max = ylims
    
    # Create a grid of x, y values, broadening the grid by 5 times the broadening factor
    x = np.linspace(x_min - 5 * x_broadening, x_max + 5 * x_broadening, grid_size)
    y = np.linspace(y_min - 5 * y_broadening, y_max + 5 * y_broadening, grid_size)
    X, Y = np.meshgrid(x, y)

    # Initialize the intensity grid
    Z = np.zeros_like(X)

    # Apply broadening for each peak, adding to the intensity grid
    for peak in peaks:
        x0, y0, strength = peak.x, peak.y, peak.correlation_strength
        if broadening == 'lorentzian':
            Z += strength * lorentzian(X, x0, Y, y0, x_broadening, y_broadening)
        elif broadening == 'gaussian':
            Z += strength * gaussian(X, x0, Y, y0, x_broadening, y_broadening)
        else:
            raise ValueError(f'Unknown broadening function: {broadening}')
    
    return X, Y, Z







nmr_base_style = resource_filename("soprano.calculate.nmr", "soprano_nmr_base.mplstyle")
nmr_2D_style   = resource_filename("soprano.calculate.nmr", "soprano_nmr_2D.mplstyle")

def styled_plot(*style_sheets):
    """Return a decorator that will apply matplotlib style sheets to a plot.
    ``style_sheets`` is a base set of styles, which will be ignored if
    ``no_base_style`` is set in the decorated function arguments.
    The style will further be overwritten by any styles in the ``style``
    optional argument of the decorated function.
    Args:
        style_sheets (:obj:`list`, :obj:`str`, or :obj:`dict`): Any matplotlib
            supported definition of a style sheet. Can be a list of style of
            style sheets.
    """

    def decorator(get_plot):
        @wraps(get_plot)
        def wrapper(*args, fonts=None, style=None, no_base_style=False, **kwargs):

            if no_base_style:
                list_style = []
            else:
                list_style = list(style_sheets)

            if style is not None:
                if isinstance(style, list):
                    list_style += style
                else:
                    list_style += [style]

            if fonts is not None:
                list_style += [{"font.family": "sans-serif", "font.sans-serif": fonts}]

            matplotlib.pyplot.style.use(list_style)
            return get_plot(*args, **kwargs)

        return wrapper

    return decorator


def get_atom_labels(atoms: Atoms, logger: Optional[logging.Logger] = None) -> np.ndarray:
    """
    Get the labels for the atoms in the Atoms object. If the labels are not present, they will be generated
    using the MagresViewLabels class.

    Args:
        atoms (ase.Atoms): Atoms object.
        logger (Optional[logging.Logger], optional): Logger object. Default is None.

    Returns:
        np.ndarray: Array of labels.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    if has_cif_labels(atoms):
        labels = atoms.get_array('labels')
    elif atoms.has('MagresView_labels'):
        # we might have already generated the MV style labels
        labels = atoms.get_array('MagresView_labels')
    else:
        logger.info('No labels found in the atoms object. Generating MagresView-style labels from scratch.')
        labels = MagresViewLabels.get(atoms)
        # convert to numpy array
        labels = np.array(labels, dtype='U25')
    return labels