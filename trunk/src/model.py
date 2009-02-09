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
import os
import os.path as path
import sys
import filecmp
import subprocess as subp
import shutil
import configuration as conf
import itertools

import logging
# import all customized exceptions
from errors import *

# flag variable indicating if parent DataItem should be notified
# when children's status is changed
propagateStatus = True

# status of data items
# normal status
STATUS_COMMON_SAME = 'common same'
STATUS_COMMON_DIFF = 'common diff'
STATUS_LEFT_ONLY = 'left only'
STATUS_RIGHT_ONLY = 'right only'
# abnormal status
# note that STATUS_UNKNOWN_COMMON can be further divided to
# "both unknown", "left unknown" and "right unknown", though we don't care for now
STATUS_UNKNOWN_COMMON = 'unknown common'
STATUS_UNKNOWN_LEFT = 'unknown left'
STATUS_UNKNOWN_RIGHT = 'unknown right'

##############################
# data model                 #
##############################
class DataItem(object):
    """Represents one entry in the result of the comparison."""
    # TODO consider slots

    __status = None
    def onStatusRead(self):
        return self.__status
    def onStatusChange(self, newStatus):
        oldStatus = self.__status
        if newStatus is not self.__status:
            self.__status = newStatus
            # the controller observes model
            self.updateUI()
            # oldStatus is None means this is the first time set
            # it's parent should not be notified in this case
            if propagateStatus and oldStatus and self.parent:
                self.parent.notifyChildUpdate(self)
    status = property(fget=onStatusRead, fset=onStatusChange)

    # the parent DataItem representing the directory it's in
    parent = None

    # locations of this DataItem
    leftLocation = None
    rightLocation = None

    # full name = location + short name
    def onLeftFullNameRead(self):
        if not self.leftLocation:
            return None
        else:
            return path.join(self.leftLocation, self.name)
    def onRightFullNameRead(self):
        if not self.rightLocation:
            return None
        else:
            return path.join(self.rightLocation, self.name)
    leftFullName = property(fget=onLeftFullNameRead)
    rightFullName = property(fget=onRightFullNameRead)

    def onLeftExistsRead(self):
        return path.exists(self.leftFullName)
    def onRightExistsRead(self):
        return path.exists(self.rightFullName)
    leftExists = property(fget=onLeftExistsRead)
    rightExists = property(fget=onRightExistsRead)

    def __init__(self, *args):
        raise InvalidMethodInvocationError('Please choose a subclass to initialize.')

    def baseinit(self, name, leftLocation, rightLocation):
        # ONLY when it's root DataItem, the name can be an empty string
        # but it's never an empty value
        def assertNotNone(v):
            if v is None:
                raise(InvalidValueError('name, leftLocation and rightLocation can\'t be None.'))
        map(assertNotNone, (name, leftLocation, rightLocation))
        self.name = name
        self.leftLocation = leftLocation
        self.rightLocation = rightLocation

    # operations
    def _precopy(self, srcSide, destSide):
        if self.status not in (STATUS_COMMON_DIFF, STATUS_LEFT_ONLY, STATUS_RIGHT_ONLY):
            # we don't raise exceptions here since we want the program continue to run
            logging.debug('copy operation on '
                    + str(self)
                    + ' not executed, since self.status is'
                    + self.status
                    + '.')
            return None, None

        if not getattr(self, srcSide + 'Exists'):
            # we don't raise exceptions here, too for the same reason
            logging.debug('copy operation on '
                    + str(self)
                    + ' not executed, since the file on '
                    + srcSide
                    + 'does not exist.')
            return None, None

        src = getattr(self, srcSide + 'FullName')
        dest = getattr(self, destSide + 'FullName')

        return src, dest

    def _delete(self, delCmd, side):
        target = getattr(self, side + 'FullName')
        if not getattr(self, side + 'Exists'):
            logging.debug('delete operation on '
                    + str(self)
                    + ' not executed, since the file on'
                    + side
                    + 'does not exist.')
        else:
            delCmd(target)
        if self.leftExists:
            self.status = STATUS_LEFT_ONLY
        elif self.rightExists:
            self.status = STATUS_RIGHT_ONLY
        else:
            self.status = None

    # overrides
    def __cmp__(self, o):
        """Used by list.sort().
        Folders are always put before files. Comparisons between same types
        are decided by their names. Ignores case."""
        if type(self) != type(o):
            if self.isDir() and o.isFile():
                return -1
            elif self.isFile() and o.isDir():
                return 1
            else:
                raise TypeError()
        return cmp(self.name.lower(), (o.name.lower()))

    def __repr__(self):
        """Used when in a list or tuple.
        Presumably called by list.__str__()."""
        return self.__str__()

class DirectoryDataItem(DataItem):
    def __init__(self, name, leftLocation, rightLocation):
        # sub data items
        self.children = []
        super(DirectoryDataItem, self).baseinit(name, leftLocation, rightLocation)
        if (self.leftExists and not path.isdir(self.leftFullName)) or \
           (self.rightExists and not path.isdir(self.rightFullName)):
            raise InvalidMethodInvocationError('DirectoryDataItem.__init__ should be invoked with dirs.')

    def compare(self, ignore=()):
        """Starts computing current DirectoryDataItem instance.
           The directories must exist on both sides."""

        if not self.leftExists or not self.rightExists:
            raise InvalidMethodInvocationError('method compare can only be called on common DirectoryDataItem(s).')

        if _isUnknown(self.leftFullName) or _isUnknown(self.rightFullName):
            status = STATUS_UNKNOWN_COMMON
            return

        # get necessary sets: commonFolders, commonFiles, lOnlyFolders, lOnlyFiles, rOnlyFolders, rOnlyFiles

        # lFolders, rFolders, lFiles, rFiles, commonFolders, commonFiles,
        # lOnlyFolders, rOnlyFolders, lOnlyFiles, rOnlyFiles are all short names
        lShortNames, rShortNames = \
            set(_filter(os.listdir(self.leftFullName), ignore)), \
            set(_filter(os.listdir(self.rightFullName), ignore))

        # seperate folders from files
        lFolders, rFolders = \
            set(name for name in lShortNames if path.isdir(path.join(self.leftFullName, name))), \
            set(name for name in rShortNames if path.isdir(path.join(self.rightFullName, name)))
        lFiles, rFiles = lShortNames.difference(lFolders), rShortNames.difference(rFolders)
        # common
        commonFolders = lFolders.intersection(rFolders)
        commonFiles = lFiles.intersection(rFiles)
        # one side
        lOnlyFolders, rOnlyFolders, lOnlyFiles, rOnlyFiles = map(set.difference,
                (lFolders, rFolders, lFiles, rFiles),
                (commonFolders, commonFolders, commonFiles, commonFiles))

        # deal with 'one side only' items
        map(self.__initOneSideSubItems,
                (lOnlyFolders, rOnlyFolders, lOnlyFiles, rOnlyFiles),
                (DirectoryDataItem, DirectoryDataItem, FileDataItem, FileDataItem),
                ('left', 'right') * 2,
                (ignore, ) * 4)

        # deal with 'common' items
        self.__initCommonSubItems(commonFolders, DirectoryDataItem, ignore)
        self.__initCommonSubItems(commonFiles, FileDataItem, ignore)

        # status of current dir comparison
        self.status = self.__diffOrSame()

        self.children.sort()

    def __diffOrSame(self):
        if not self.leftExists or not self.rightExists:
            raise InvalidMethodInvocationError('method __diffOrSame is meaningful only when called on common DirectoryDataItem(s).')
        if [itm for itm in self.children if itm.status is not STATUS_COMMON_SAME]:
            return STATUS_COMMON_DIFF
        else:
            return STATUS_COMMON_SAME

    def __initOneSideSubItems(self, names, itemType, side, ignore=()):
        """Recursively creates DataItem objects for given dir with given status."""
        status = globals()['STATUS_' + side.upper() + '_ONLY']
        badStatus = globals()['STATUS_UNKNOWN_' + side.upper()]
        baseDir = getattr(self, side + 'FullName')
        for each in names:
            # though it's only on one side, we still set the other side's location
            # it's useful for the Copy operation
            itm = itemType(each, self.leftFullName, self.rightFullName)
            itm.parent = self
            if not _isUnknown(path.join(baseDir, each)):
                itm.status = status
                if itemType is DirectoryDataItem:
                    # recursive call when <names> are dirs
                    newBaseDir = getattr(itm, side + 'FullName')
                    shortNames = set(_filter(os.listdir(newBaseDir), ignore))
                    folders = set(name for name in shortNames if path.isdir(path.join(newBaseDir, name)))
                    files = shortNames.difference(folders)
                    itm.__initOneSideSubItems(folders, DirectoryDataItem, side, ignore)
                    itm.__initOneSideSubItems(files, FileDataItem, side, ignore)
            else:
                itm.status = badStatus
            self.children.append(itm)

        self.children.sort()

    def __initCommonSubItems(self, names, itemType, ignore):
        """Creates DataItems that are common on both sides."""
        for each in names:
            itm = itemType(each, self.leftFullName, self.rightFullName)
            itm.parent = self
            if itemType is DirectoryDataItem:
                itm.compare(ignore)
            elif itemType is FileDataItem:
                if not _isUnknown(itm.leftFullName) and not _isUnknown(itm.rightFullName):
                    itm.status = STATUS_COMMON_SAME \
                            if filecmp.cmp(itm.leftFullName, itm.rightFullName, shallow=int(conf.shallow)) else \
                            STATUS_COMMON_DIFF
                else:
                    itm.status = STATUS_UNKNOWN_COMMON
            else:
                raise InvalidValueError()
            self.children.append(itm)

    # trigger
    def notifyChildUpdate(self, child):
        """only available to directories"""
        if child.status is None:
            self.children.remove(child)
        # decide self status. children all have correct status at this moment
        if self.leftExists and self.rightExists:
            self.status = self.__diffOrSame()
        elif self.leftExists:
            self.status = STATUS_LEFT_ONLY
        elif self.rightExists:
            self.status = STATUS_RIGHT_ONLY

    # operations
    def copyTo(self, srcSide, destSide):
        copyCmd = shutil.copytree
        src, dest = self._precopy(srcSide, destSide)
        if not src or not dest:
            return
        global propagateStatus
        oldPropagateStatus = propagateStatus
        # we'll decide self's status in another way
        # so we turn off children's status propagation
        propagateStatus = False
        if not getattr(self, destSide + 'Exists'):
            # copy the whole directory
            # only when the dest directory is not there
            copyCmd(src, dest)
            for each in self.children:
                each.status = STATUS_COMMON_SAME
        else:
            # if not, call copyTo on each children
            for each in self.children:
                each.copyTo(srcSide, destSide)
        propagateStatus = oldPropagateStatus
        self.status = self.__diffOrSame()

    def delete(self, side):
        delCmd = shutil.rmtree
        self._delete(delCmd, side)
        global propagateStatus
        oldPropagateStatus = propagateStatus
        # in _delete, we already decided self's status
        # so we turn off its children's status propagation here
        propagateStatus = False
        for each in self.children:
            each.delete(side)
        propagateStatus = oldPropagateStatus

    def browse(self, side):
        if sys.platform == 'win32':
            if getattr(self, side + 'Exists'):
                subp.Popen(('explorer.exe', '/n,/e,', path.normpath(getattr(self, side + 'FullName'))))

    # overrides
    def __str__(self):
        def replaceNone(s):
            return s if s is not None else 'None'
        return ''.join(('\ndir: ', replaceNone(self.name), ', ',
                         'status: ', replaceNone(self.status), ', ',
                         'leftLocation: ', replaceNone(self.leftLocation), ', ',
                         'rightLocation: ', replaceNone(self.rightLocation), ', '
                         'children: ', `self.children`, ''))

    # misc
    def isDir(self):
        return True

    def isFile(self):
        return False

class FileDataItem(DataItem):
    def __init__(self, name, leftLocation, rightLocation):
        super(FileDataItem, self).baseinit(name, leftLocation, rightLocation)
        if (self.leftExists and not path.isfile(self.leftFullName)) or \
           (self.rightExists and not path.isfile(self.rightFullName)):
            raise InvalidMethodInvocationError('FileDataItem.__init__ should be invoked with files.')

    # operations
    def copyTo(self, srcSide, destSide):
        copyCmd = shutil.copy
        src, dest = self._precopy(srcSide, destSide)
        if not src or not dest:
            return
        destLocation = getattr(self, destSide + 'Location')
        if not path.exists(destLocation):
            os.makedirs(destLocation)
        copyCmd(src, dest)
        self.status = STATUS_COMMON_SAME

    def delete(self, side):
        delCmd = os.remove
        self._delete(delCmd, side)

    def browse(self, side):
        if sys.platform == 'win32':
            if getattr(self, side + 'Exists'):
                subp.Popen(('explorer.exe', '/n,/e,/select,', path.normpath(getattr(self, side + 'FullName'))))

    def compare(self):
        if self.status is STATUS_COMMON_DIFF:
            subp.Popen((conf.fileCmpCommand, '-d',
                self.leftFullName, self.rightFullName))
        else:
            logging.debug('file compare is not executed since the status is not STATUS_COMMON_DIFF')
        # TODO update status here.

    # overrides
    def __str__(self):
        def replaceNone(s):
            return s if s is not None else 'None'
        return ''.join(('\nfile: ', replaceNone(self.name), ', ',
                         'status: ', replaceNone(self.status), ', ',
                         'leftLocation: ', replaceNone(self.leftLocation), ', ',
                         'rightLocation: ', replaceNone(self.rightLocation), ', '))

    # misc
    def isDir(self):
        return False

    def isFile(self):
        return True

class CompareSession(object):
    def __init__(self, leftPath='', rightPath='', ignore=()):
        self.leftPath = leftPath
        self.rightPath = rightPath
        self.ignore = ignore

##############################
# helpers                    #
##############################
def _isUnknown(name):
    """Used to decide whether a folder/file is comparable.
    Returns:
            True if unknown
            False if not"""
    try:
        os.stat(name)
        if(path.isdir(name)):
            os.listdir(name)
        return False
    except Exception, e:
        logging.warn('unknown file/folder found: ' + name + ', with exception ' + str(e))
        return True

def _filter(filelist, skip):
    return list(itertools.ifilterfalse(skip.__contains__, filelist))

# TODO command line usage: generate report
# K:\DirCompare\trunk\src>python model.py ..\..\sandbox\leftDir ..\..\sandbox\rightDir
if __name__ == '__main__':
    DataItem.updateUI = lambda self: None
    try:
        leftPath, rightPath = sys.argv[1], sys.argv[2]
    except IndexError, e:
        print("Usage: python model.py leftPath rightPath")
        sys.exit(1)
    rootDataItem = DirectoryDataItem('', leftPath, rightPath)
    rootDataItem.compare()
    print(rootDataItem)

