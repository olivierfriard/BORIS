"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""

from optparse import OptionParser


def parse_arguments():
    # check if argument
    usage = 'usage: %prog [options] [-p PROJECT_PATH] [-o "OBSERVATION ID"]'
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug", action="store_true", default=False, dest="debug", help="Use debugging mode")
    parser.add_option("-v", "--version", action="store_true", default=False, dest="version", help="Print version")
    parser.add_option("-n", "--nosplashscreen", action="store_true", default=False, help="No splash screen")
    parser.add_option("-p", "--project", action="store", default="", dest="project", help="Project file")
    parser.add_option("-o", "--observation", action="store", default="", dest="observation", help="Observation id")
    parser.add_option(
        "-f",
        "--no-first-launch-dialog",
        action="store_true",
        default=False,
        dest="no_first_launch_dialog",
        help="No first launch dialog (for new version automatic check)",
    )

    return parser.parse_args()
