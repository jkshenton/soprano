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
NMR Data

Data on NMR relevant properties of elements and isotopes - spin, gyromagnetic
ratio and quadrupole moment.
"""

import json
import pkgutil
import re

import numpy as np
import scipy.constants as cnst

# EFG conversion constant.
# Units chosen so that EFG_TO_CHI*Quadrupolar moment*Vzz = Hz
EFG_TO_CHI = (
    cnst.physical_constants["atomic unit of electric field " "gradient"][0]
    * cnst.e
    * 1e-31
    / cnst.h
)

try:
    _nmr_data = pkgutil.get_data("soprano", "data/nmrdata.json").decode("utf-8")
    _nmr_data = json.loads(_nmr_data)
except OSError:
    _nmr_data = None


def _get_nmr_data():

    if _nmr_data is not None:
        return _nmr_data
    else:
        raise RuntimeError(
            "NMR data not available. Something may be "
            "wrong with this installation of Soprano"
        )

def _get_isotope_list(elems, isotopes=None, isotope_list=None, use_q_isotopes=False):
    '''
    elems can be a single element string or a list of elements
    returns the isotope number for each element elems
    '''
    if isotopes is None:
        isotopes = {}
    if isinstance(elems, str):
        elems = [elems]  # It's a single element

    isotopelist = np.zeros(len(elems), dtype=int)
    nmr_data = _get_nmr_data()

    for i, e in enumerate(elems):

        if e not in nmr_data:
            # Non-existing element
            raise RuntimeError(f"No NMR data on element {e}")

        iso = nmr_data[e]["iso"]
        if use_q_isotopes and nmr_data[e]["Q_iso"] is not None:
            iso = nmr_data[e]["Q_iso"]
        if e in isotopes:
            iso = isotopes[e]
        if isotope_list is not None and isotope_list[i] is not None:
            iso = isotope_list[i]
        isotopelist[i] = iso
    return isotopelist

def _get_isotope_data(elems, key, isotopes={}, isotope_list=None, use_q_isotopes=False):
    isotopelist = _get_isotope_list(elems, isotopes=isotopes, isotope_list=isotope_list, use_q_isotopes=use_q_isotopes)

    data = np.zeros(len(elems))
    nmr_data = _get_nmr_data()

    for i, iso in enumerate(isotopelist):
        el = elems[i]
        try:
            data[i] = nmr_data[el][str(iso)][key]
        except KeyError:
            raise RuntimeError(
                f"Data {key} does not exist for isotope {iso} of "
                f"element {el}.\n"
                "Edit the file soprano/data/nmrdata.json to add custom isotopes."
            )

    return data


def _el_iso(sym):
    """Utility function: split isotope and element in conventional
    representation.
    """

    nmr_data = _get_nmr_data()

    match = re.findall("([0-9]*)([A-Za-z]+)", sym)
    if len(match) != 1:
        raise ValueError("Invalid isotope symbol")
    elif match[0][1] not in nmr_data:
        raise ValueError("Invalid element symbol")

    el = match[0][1]
    # What about the isotope?
    iso = str(nmr_data[el]["iso"]) if match[0][0] == "" else match[0][0]

    if iso not in nmr_data[el]:
        raise ValueError(f"No data on isotope {iso} for element {el}")

    return el, iso


def nmr_gamma(el, iso=None):
    """Gyromagnetic ratio for an element

    Return the gyromagnetic ratio for the given element and isotope, in
    rad/(s*T)

    | Args:
    |   el (str):   element symbol
    |   iso (int):  isotope. Default is the most abundant one.

    | Returns:
    |   gamma (float):  gyromagnetic ratio in rad/(s*T)
    """

    isotopes = {}
    if iso is not None:
        isotopes[el] = iso

    return _get_isotope_data([el], "gamma", isotopes=isotopes)[0]


def nmr_spin(el, iso=None):
    """Nuclear spin for an element

    Return the nuclear spin for the given element and isotope, in
    Bohr magnetons

    | Args:
    |   el (str):   element symbol
    |   iso (int):  isotope. Default is the most abundant one.

    | Returns:
    |   I (float):  nuclear spin in Bohr magnetons
    """

    isotopes = {}
    if iso is not None:
        isotopes[el] = iso

    return _get_isotope_data([el], "I", isotopes=isotopes)[0]


def nmr_quadrupole(el, iso=None):
    """Quadrupole moment for an element

    Return the quadrupole moment for the given element and isotope, in
    millibarn

    | Args:
    |   el (str):   element symbol
    |   iso (int):  isotope. Default is the most abundant one.

    | Returns:
    |   Q (float):  quadrupole moment in  millibarn
    """

    isotopes = {}
    if iso is not None:
        isotopes[el] = iso

    return _get_isotope_data([el], "Q", isotopes=isotopes)[0]
