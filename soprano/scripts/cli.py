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

'''Click command line interface for Soprano.'''


__author__ = "J. Kane Shenton"
__maintainer__ = "J. Kane Shenton"
__email__ = "kane.shenton@stfc.ac.uk"
__date__ = "July 04, 2022"


import click
from soprano.scripts import  nmr

epilog = f"""
    Author: {__author__} ({__email__})\n
    Last updated: {__date__}"""
@click.group(help="CLI tool to streamline common soprano tasks.", epilog=epilog)
def cli():
    pass

cli.add_command(nmr.nmr)

if __name__ == '__main__':
    cli()