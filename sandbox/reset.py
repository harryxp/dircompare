#    -*- coding: utf-8 -*-
#    Utility script for resetting the DirCompare test sandbox.
#
#    Copyright (C) 2008  Pan Xingzhi
#    http://code.google.com/p/dircompare/
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path as path
import sys
join = path.join

# sandboxDir is where reset.py resides
sandboxDir = path.dirname(sys.modules[__name__].__file__)

leftDir = join(sandboxDir, 'leftDir')
rightDir = join(sandboxDir, 'rightDir')

# clean up
import shutil
shutil.rmtree(leftDir, ignore_errors=True)
shutil.rmtree(rightDir, ignore_errors=True)

# dirs to be created
allDirs = [leftDir, rightDir]

# files to be created
allFiles = []

def createSub(baseDir, level=3, subDirPrefix='sub', subDirPerLevel=3, filePrefix='f', filePerLevel=4):
    """Creates sub dirs and files for given base dir.
    Needs global vars: allDirs, allFiles."""

    def createFullNames(base, childPrefix, childrenPerLevl, all):
        """Uses os.path.join to give full names of sub items."""
        children = map(join,
                    (base, ) * childrenPerLevl,
                    map(lambda childPrefix, number: childPrefix + str(number),
                        (childPrefix, ) * childrenPerLevl,
                        range(0, childrenPerLevl)))
        all.extend(children)
        return children

    if level:
        subDirs = createFullNames(baseDir, subDirPrefix, subDirPerLevel, allDirs)
        for sub in subDirs:
            # recursive call
            createSub(sub, level=level - 1,
                        subDirPrefix=subDirPrefix*2, subDirPerLevel=subDirPerLevel,
                        filePrefix=filePrefix*2, filePerLevel=filePerLevel)
            createFullNames(sub, filePrefix, filePerLevel, allFiles)

createSub(leftDir)
createSub(rightDir)

# create dirs
import os
map(os.mkdir, allDirs)

# create files
for f in allFiles:
    fp = open(f, 'w')
    fp.close()

