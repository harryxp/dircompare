#    -*- coding: utf-8 -*-
#    Advanced directory compare tool in Python.
#
#    Copyright (C) 2008, 2009  Pan Xingzhi
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

from __future__ import print_function
import ConfigParser as cp
config=cp.ConfigParser()
try:
    config.read(['DirCompare.rc'])
    def get(key):
        return config.get('default', key)
    defaultFrameSize = get('DEFAULT_FRAME_SIZE')
    normalTextColor = get('NORMAL_TEXT_COLOR')
    normalBgColor = get('NORMAL_BG_COLOR')
    oneSideTextColor = get('ONE_SIDE_TEXT_COLOR')
    oneSideBgColor = get('ONE_SIDE_BG_COLOR')
    diffTextColor = get('DIFF_TEXT_COLOR')
    diffBgColor = get('DIFF_BG_COLOR')
    loggingLevel = get('LOGGING_LEVEL')
    logFile = get('LOG_FILE')
    fileCmpCommand = get('FILE_CMP_COMMAND')
    shallow = get('SHALLOW')
except (cp.ParsingError, cp.NoSectionError) as e:
    # error(s) in the config file
    import sys
    print('Please check your config file "DirCompare.rc".',
            file=sys.stderr)
    print(e.message, file=sys.stderr)
    import sys
    sys.exit(1)

