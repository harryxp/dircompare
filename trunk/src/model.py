#    -*- coding: utf-8 -*-
#    Advanced directory compare tool in Python.
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

import os
import os.path as path
import sys
import filecmp
import subprocess as subp
import shutil
import configuration as conf
import itertools

import logging

# flag variable indicating if parent DataItem should be notified
# the children's status change
propagateStatus = True

##############################
# data model                 #
##############################
class DataItem(object):
    """Represents one entry in the result of the comparison."""
    # TODO consider slots

    # type is one of (None, 'dir', 'file')
    type = None
    TYPE_DIR = 'dir'
    TYPE_FILE = 'file'

    # status is one of:
    __status = None
    STATUS_SAME = 'common same'
    STATUS_DIFF = 'common diff'
    STATUS_COMMON_BOTH_UNKNOWN = 'common both unknown'
    STATUS_COMMON_LEFT_UNKNOWN = 'common left unknown'
    STATUS_COMMON_RIGHT_UNKNOWN = 'common right unknown'
    STATUS_LEFT_ONLY = 'left only'
    STATUS_RIGHT_ONLY = 'right only'
    STATUS_LEFT_ONLY_UNKNOWN = 'left only unknown'
    STATUS_RIGHT_ONLY_UNKNOWN = 'right only unknown'

    ignore = ()

    def onStatusRead(self):
        return self.__status
    def onStatusChange(self, newStatus):
        oldStatus = self.__status
        # TODO check if newStatus is valid
        if newStatus is not self.__status:
            self.__status = newStatus
            # tell the controller
            self.updateUI()
            # oldStatus is None means this is the first time set
            # it's parent should not be notified in this case
            if propagateStatus and oldStatus and self.parent:
                self.parent.notifyChildUpdate(self)
    status = property(fget=onStatusRead, fset=onStatusChange)

    # for file this attribute is always None
    # for directory, it's a list of DataItem objects
    children = None

    # the parent DataItem representing the directory it's in
    parent = None

    # locations of this DataItem
    leftLocation = None
    rightLocation = None

    # full name = location + short name
    def onLeftFilenameRead(self):
        if not self.leftLocation:
            return None
        else:
            return path.join(self.leftLocation, self.filename)
    def onRightFilenameRead(self):
        if not self.rightLocation:
            return None
        else:
            return path.join(self.rightLocation, self.filename)
    leftFile = property(fget=onLeftFilenameRead)
    rightFile = property(fget=onRightFilenameRead)

    def onLeftFileExistsRead(self):
        return path.exists(self.leftFile)
    def onRightFileExistsRead(self):
        return path.exists(self.rightFile)
    leftFileExists = property(fget=onLeftFileExistsRead)
    rightFileExists = property(fget=onRightFileExistsRead)

    def __init__(self, filename, leftLocation, rightLocation):
        # ONLY when it's root DataItem, the filename can be an empty string
        # but it's never an empty value
        def assertNotNone(v):
            if v is None:
                raise(ValueError('filename, leftLocation and rightLocation can\'t be None.'))
        map(assertNotNone, (filename, leftLocation, rightLocation))
        self.filename = filename
        self.leftLocation = leftLocation
        self.rightLocation = rightLocation

    # status calculator
    def decideDirItemStatus(self, ignore=()):
        self.ignore = ignore

        if self.leftFileExists and self.rightFileExists:
            self.__compareCommonDirs(ignore)
        elif self.leftFileExists:
            self.parent.__initOneSideItems(
                    (self.filename, ),
                    DataItem.TYPE_DIR,
                    DataItem.STATUS_LEFT_ONLY,
                    DataItem.STATUS_LEFT_ONLY_UNKNOWN,
                    self.ignore)
        elif self.rightFileExists:
            self.parent.__initOneSideItems(
                    (self.filename, ),
                    DataItem.TYPE_DIR,
                    DataItem.STATUS_RIGHT_ONLY,
                    DataItem.STATUS_RIGHT_ONLY_UNKNOWN,
                    self.ignore)
        else:
            self.status = None

    def __compareCommonDirs(self, ignore=()):
        """Returns the status and children of current (dir) DataItem instance being calculated."""
        if not isinstance(ignore, (tuple, )):
            raise ValueError('ignore must be an instance of <type \'tuple\'>.')

        if self.type is not DataItem.TYPE_DIR:
            raise TypeError, 'method <__compareCommonDirs> is only available to directories'

        # decide if self is one of <STATUS_COMMON_BOTH_UNKNOWN, STATUS_COMMON_LEFT_UNKNOWN, STATUS_COMMON_RIGHT_UNKNOWN>
        # TODO do more, deal with STATUS_COMMON_LEFT_UNKNOWN and STATUS_COMMON_RIGHT_UNKNOWN.
        
        if self.__decideUnknownWhenCommon():
            return

        # get necessary sets: commonFolders, commonFiles, lOnlyFolders, lOnlyFiles, rOnlyFolders, rOnlyFiles
        # lFolders, rFolders, lFiles, rFiles, commonFolders, commonFiles,
        # lOnlyFolders, rOnlyFolders, lOnlyFiles, rOnlyFiles are all short names
        lShortNames, rShortNames = \
            set(_filter(os.listdir(self.leftFile), ignore)), \
            set(_filter(os.listdir(self.rightFile), ignore))

        # seperate folders from files
        lFolders, rFolders = \
            set(name for name in lShortNames if path.isdir(path.join(self.leftFile, name))), \
            set(name for name in rShortNames if path.isdir(path.join(self.rightFile, name)))
        lFiles, rFiles = lShortNames.difference(lFolders), rShortNames.difference(rFolders)
        # common
        commonFolders = lFolders.intersection(rFolders)
        commonFiles = lFiles.intersection(rFiles)
        # one side
        lOnlyFolders, rOnlyFolders, lOnlyFiles, rOnlyFiles = map(set.difference,
                (lFolders, rFolders, lFiles, rFiles),
                (commonFolders, commonFolders, commonFiles, commonFiles))

        # deal with 'one side only' items
        self.children = []

        map(self.__initOneSideItems,
                (lOnlyFolders, rOnlyFolders, lOnlyFiles, rOnlyFiles),
                (DataItem.TYPE_DIR, DataItem.TYPE_DIR, DataItem.TYPE_FILE, DataItem.TYPE_FILE),
                (DataItem.STATUS_LEFT_ONLY, DataItem.STATUS_RIGHT_ONLY) * 2,
                (DataItem.STATUS_LEFT_ONLY_UNKNOWN, DataItem.STATUS_RIGHT_ONLY_UNKNOWN) * 2,
                (ignore, ) * 4)

        # deal with 'common' items
        self.__initCommonSubItems(commonFolders, DataItem.TYPE_DIR, ignore)
        self.__initCommonSubItems(commonFiles, DataItem.TYPE_FILE, ignore)

        # status of current dir comparison
        if [itm for itm in self.children if itm.status is not DataItem.STATUS_SAME]:
            self.status = DataItem.STATUS_DIFF
        else:
            self.status = DataItem.STATUS_SAME

        self.children.sort()

    def __decideUnknownWhenCommon(self):
        """Decides if self.leftFile and self.rightFile are in 'uncomparable' state."""
        lComparable, rComparable = _isComparable(self.leftFile), _isComparable(self.rightFile)

        # TODO init the 'known' side
        if not lComparable and not rComparable:
            self.status = DataItem.STATUS_COMMON_BOTH_UNKNOWN
            if self.type is DataItem.TYPE_DIR:
                self.children = []
        elif not lComparable:
            self.status = DataItem.STATUS_COMMON_LEFT_UNKNOWN
            if self.type is DataItem.TYPE_DIR:
                self.children = []
        elif not rComparable:
            self.status = DataItem.STATUS_COMMON_RIGHT_UNKNOWN
            if self.type is DataItem.TYPE_DIR:
                self.children = []
        else:
            return False
        return True

    def __initOneSideItems(self, names, type, status, badStatus, ignore=()):
        """Recursively creates DataItem objects for given dir with given status."""
        baseDir = self.leftFile if status is DataItem.STATUS_LEFT_ONLY else self.rightFile
        for each in names:
            # though it's only on one side, we still set the other side's location
            # it's useful for the Copy operation
            itm = DataItem(each, self.leftFile, self.rightFile)
            itm.type, itm.parent = type, self
            if _isComparable(path.join(baseDir, each)):
                itm.status = status
                if type is DataItem.TYPE_DIR:
                    # recursive call when <names> are dirs
                    itm.children = []
                    newBaseDir = itm.leftFile if status is DataItem.STATUS_LEFT_ONLY else itm.rightFile
                    shortNames = set(_filter(os.listdir(newBaseDir), ignore))
                    folders = set(name for name in shortNames if path.isdir(path.join(newBaseDir, name)))
                    files = shortNames.difference(folders)
                    itm.__initOneSideItems(folders, DataItem.TYPE_DIR, status, badStatus, ignore)
                    itm.__initOneSideItems(files, DataItem.TYPE_FILE, status, badStatus, ignore)
            else:
                itm.status = badStatus
            self.children.append(itm)

        self.children.sort()

    def __initCommonSubItems(self, names, type, ignore):
        """Creates DataItems that are common on both sides."""
        for each in names:
            itm = DataItem(each, self.leftFile, self.rightFile)
            itm.type, itm.parent = type, self
            if type is DataItem.TYPE_DIR:
                itm.__compareCommonDirs(ignore)
            else:
                if not itm.__decideUnknownWhenCommon():
                    itm.status = DataItem.STATUS_SAME \
                            if filecmp.cmp(itm.leftFile, itm.rightFile, shallow=conf.shallow) else \
                            DataItem.STATUS_DIFF
            self.children.append(itm)

    # operations
    def copyTo(self, srcSide, destSide):
        # copy/copytree
        # change left/right location
        # change self status
        # change parent status...pass up
        if self.status not in (DataItem.STATUS_DIFF, DataItem.STATUS_LEFT_ONLY, DataItem.STATUS_RIGHT_ONLY):
            logging.info('copy operation on ' + str(self) + ' not executed.')

        if not getattr(self, srcSide + 'FileExists'):
            return
        src = getattr(self, srcSide + 'File')
        dest = getattr(self, destSide + 'File')
        copycmd = shutil.copytree if self.type is DataItem.TYPE_DIR else shutil.copy

        if self.type is DataItem.TYPE_FILE:
            destLocation = getattr(self, destSide + 'Location')
            if not path.exists(destLocation):
                os.makedirs(destLocation)
            copycmd(src, dest)
        elif self.type is DataItem.TYPE_DIR:
            global propagateStatus
            oldPropagateStatus = propagateStatus
            propagateStatus = False
            if not getattr(self, destSide + 'FileExists'):
                # copy only when the dest directory is not there
                copycmd(src, dest)
                # TODO do this or call decideDirItemStatus?
                for each in self.children:
                    each.status = DataItem.STATUS_SAME
            else:
                for each in self.children:
                    each.copyTo(srcSide, destSide)
            propagateStatus = oldPropagateStatus
        else:
            raise ValueError('type is neither DataItem.TYPE_DIR nor DataItem.TYPE_FILE')
        self.status = DataItem.STATUS_SAME

    def delete(self, side):
        delcmd = shutil.rmtree if self.type is DataItem.TYPE_DIR else os.remove
        target = getattr(self, side + 'File')
        if getattr(self, side + 'FileExists'):
            delcmd(target)
        if self.leftFileExists:
            self.status = DataItem.STATUS_LEFT_ONLY
        elif self.rightFileExists:
            self.status = DataItem.STATUS_RIGHT_ONLY
        else:
            self.status = None
        if self.type is DataItem.TYPE_DIR:
            global propagateStatus
            oldPropagateStatus = propagateStatus
            propagateStatus = False
            for each in self.children:
                each.delete(side)
            propagateStatus = oldPropagateStatus

    def browse(self, side):
        if sys.platform == 'win32':
            if getattr(self, side + 'FileExists'):
                if self.type is self.TYPE_DIR:
                    subp.Popen(('explorer.exe', '/n,/e,', path.normpath(getattr(self, side + 'File'))))
                elif self.type is self.TYPE_FILE:
                    subp.Popen(('explorer.exe', '/n,/e,/select,', path.normpath(getattr(self, side + 'File'))))
                else:
                    raise ValueError('type is neither DataItem.TYPE_DIR nor DataItem.TYPE_FILE')

    def compareFiles(self):
        """only available to non-directories"""
        if self.type is not DataItem.TYPE_FILE:
            raise TypeError, 'method <compareLrFiles> is only available to non-directories'
        if self.status is DataItem.STATUS_DIFF:
            subp.Popen((conf.fileCmpCommand, '-d',
                self.leftFile, self.rightFile))
        # update status here.

    # trigger
    def notifyChildUpdate(self, child):
        """only available to directories"""
        if self.type is not DataItem.TYPE_DIR:
            raise TypeError, 'method <notifyChildUpdate> is only available to directories'
        print self.filename + ' notified'
        self.decideDirItemStatus(self.ignore)

    # overrides
    def __cmp__(self, o):
        """Used by list.sort().
        Folders are always put before files. Comparisons between same types
        are decided by their filenames. Ignores case."""
        if self.type != o.type:
            if self.type is DataItem.TYPE_DIR:
                return -1
            else:
                return 1
        return cmp(self.filename.lower(), (o.filename.lower()))

#    def __lt__(self, o):
#        """Used by list.sort(). Ignores case."""
#        return self.filename.lower().__le__(o.lower())

    def __repr__(self):
        """Used when in a list or tuple.
        Presumably called by list.__str__()."""
        return self.__str__()

    def __str__(self):
        def replaceNone(s):
            return s if s is not None else 'None'
        return ''.join(('\nfilename: ', replaceNone(self.filename), ', ',
                         'type: ', replaceNone(self.type), ', ',
                         'status: ', replaceNone(self.status), ', ',
                         'leftLocation: ', replaceNone(self.leftLocation), ', ',
                         'rightLocation: ', replaceNone(self.rightLocation), ', '))
#                         'children: ', `self.children`, ']'))

class CompareSession(object):
    def __init__(self, leftPath='', rightPath='', ignore=()):
        self.leftPath = leftPath
        self.rightPath = rightPath
        self.ignore = ignore

##############################
# helpers                    #
##############################
def _sepDirsAndFiles(d, ignore=()):
    """Seperates subdirs and files in a given dirs into two sets, and returns them."""
    # os.listdir gives names without paths
    nameSet = set(os.listdir(d))
    if ignore:
        nameSet = nameSet.difference(ignore)
    dirSet = set([f for f in nameSet if path.isdir(path.join(d, f))])
    fileSet = nameSet.difference(dirSet)
    return dirSet, fileSet

def _isComparable(filename):
    """Used to decide whether a folder/file is comparable.
    Returns:
            True if comparable
            False if not"""
    try:
        os.stat(filename)
        if(path.isdir(filename)):
            os.listdir(filename)
        return True
    except Exception, e:
        logging.warn('uncomparable file/folder found: ' + filename + ', with exception ' + str(e))
        return False

def _filter(filelist, skip):
    return list(itertools.ifilterfalse(skip.__contains__, filelist))

# TODO command line usage: generate report
# K:\DirCompare\trunk\src>python model.py ..\..\sandbox\leftDir ..\..\sandbox\rightDir
if __name__ == '__main__':
    DataItem.updateUI = lambda self: None
    try:
        leftPath, rightPath = sys.argv[1], sys.argv[2] 
    except IndexError, e:
        print "Usage: python model.py leftPath rightPath"
        sys.exit(1)
    rootDataItem = DataItem('', leftPath, rightPath)
    rootDataItem.type = DataItem.TYPE_DIR
    rootDataItem.decideDirItemStatus()
    print rootDataItem

