#    -*- coding: utf-8 -*-
#    Advanced directory compare tool in Python.
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
import filecmp
import subprocess as subp
import shutil
import configuration as conf
import itertools

import logging

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

    def onStatusRead(self):
        return self.__status
    def onStatusChange(self, newStatus):
        oldStatus = self.__status
        # TODO check if newStatus is valid
        if newStatus is not self.__status:
            self.__status = newStatus
            self.updateUI()
            # oldStatus is None means this is the first time set
            # it's parent should not be notified in this case
            if oldStatus and self.parent:
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

    # sub items initializers
    def initChildrenItems(self, ignore=None):
        """Returns the status and children of current DataItem instance being calculated."""
        if not isinstance(ignore, (list, )): 
            raise ValueError('ignore must be an instance of <type \'list\'>.')

        if self.type is not DataItem.TYPE_DIR:
            raise TypeError, 'method <initChildrenItems> is only available to directories'

        # decide if self is one of <STATUS_COMMON_BOTH_UNKNOWN, STATUS_COMMON_LEFT_UNKNOWN, STATUS_COMMON_RIGHT_UNKNOWN>
        self.__decideItemCommonUnknown()
        # TODO do more, deal with STATUS_COMMON_LEFT_UNKNOWN and STATUS_COMMON_RIGHT_UNKNOWN.
        if self.status:
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
        self.__initCommonItems(commonFolders, DataItem.TYPE_DIR, ignore)
        self.__initCommonItems(commonFiles, DataItem.TYPE_FILE, ignore)

        # status of current dir comparison
        if [itm for itm in self.children if itm.status is not DataItem.STATUS_SAME]:
            self.status = DataItem.STATUS_DIFF
        else:
            self.status = DataItem.STATUS_SAME

        self.children.sort()

    def __decideItemCommonUnknown(self):
        """Decides if self.leftFile and self.rightFile are in 'uncomparable' state."""
        lComparable, rComparable = _isComparable(self.leftFile), _isComparable(self.rightFile)

        # TODO init the 'known' side
        if not lComparable and not rComparable:
            self.status = DataItem.STATUS_COMMON_BOTH_UNKNOWN
            self.children = []
        elif not lComparable:
            self.children = []
            self.status = DataItem.STATUS_COMMON_LEFT_UNKNOWN
        elif not rComparable:
            self.children = []
            self.status = DataItem.STATUS_COMMON_RIGHT_UNKNOWN

    def __initOneSideItems(self, names, type, status, badStatus, ignore=None):
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

    def __initCommonItems(self, names, type, ignore):
        """Creates DataItems that are common on both sides."""
        for each in names:
            itm = DataItem(each, self.leftFile, self.rightFile)
            itm.type, itm.parent = type, self
            if type is DataItem.TYPE_DIR:
                itm.initChildrenItems(ignore)
            else:
                itm.__decideItemCommonUnknown()
                if not itm.status:
                    itm.status = DataItem.STATUS_SAME \
                            if filecmp.cmp(itm.leftFile, itm.rightFile, shallow=conf.shallow) else \
                            DataItem.STATUS_DIFF
            self.children.append(itm)

    # operations
    def copyTo(self, src, dest):
        # copy/copytree
        # change left/right location
        # change self status
        # change parent status...pass up
        if self.status not in (DataItem.STATUS_DIFF, DataItem.STATUS_LEFT_ONLY, DataItem.STATUS_RIGHT_ONLY):
            logging.info('copy operation on ' + str(self) + ' not executed.')
        srcLocation = getattr(self, src)
        if srcLocation:
            src = path.join(srcLocation, self.filename)
        else:
            src = path.join(getattr(self.parent, src))
        destLocation = getattr(self, dest)
        if destLocation:
            dest = path.join(destLocation, self.filename)
        else:
            dest = path.join(getattr(self.parent, dest))

        copycmd = shutil.copytree if self.type is DataItem.TYPE_DIR else shutil.copy
        copycmd(src, dest)
        # this will trigger 'onPropertyChange'
        # and eventually, 'notifyChildUpdate'
        self.status = DataItem.STATUS_SAME

    def delete(self, propName):
        delcmd = shutil.rmtree if self.type is DataItem.TYPE_DIR else os.remove
        delcmd(getattr(self, propName))
        if self.leftFileExists:
            self.status = DataItem.STATUS_LEFT_ONLY
        elif self.rightFileExists:
            self.status = DataItem.STATUS_RIGHT_ONLY
        else:
            self.status = None

    def browse(self, propName):
        import sys
        if sys.platform == 'win32':
            if getattr(self, propName + 'Exists'):
                if self.type is self.TYPE_DIR:
                    subp.Popen(('explorer.exe', '/n,/e,', path.normpath(getattr(self, propName))))
                elif self.type is self.TYPE_FILE:
                    subp.Popen(('explorer.exe', '/n,/e,/select,', path.normpath(getattr(self, propName))))

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
#        if self.status is DataItem.STATUS_DIFF and child.status is DataItem.STATUS_SAME:
#            for each in self.children:
#                if each.status is not DataItem.STATUS_SAME:
#                    return
#            # this will trigger 'onPropertyChange'
#            self.status = DataItem.STATUS_SAME

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
        return ''.join(('\n[filename: ', replaceNone(self.filename), ', ',
                         'type: ', replaceNone(self.type), ', ',
                         'status: ', replaceNone(self.status), ', ',
                         'leftLocation: ', replaceNone(self.leftLocation), ', ',
                         'rightLocation: ', replaceNone(self.rightLocation), ', ',
                         'children: ', `self.children`, ']'))

class CompareSession(object):

    def __init__(self, leftPath='', rightPath='', ignore=[]):
        self.leftPath = leftPath
        self.rightPath = rightPath
        self.ignore = ignore

##############################
# start                      #
##############################
def start(dir1, dir2, ignore=None):
    """Accepts 2 strings representing directories."""
    rootDataItem = DataItem('', dir1, dir2)
    rootDataItem.type = DataItem.TYPE_DIR
    rootDataItem.initChildrenItems(ignore=ignore)
    return rootDataItem


##############################
# helpers                    #
##############################
def _sepDirsAndFiles(d, ignore=None):
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

