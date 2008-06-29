# -*- coding: utf-8 -*-

import os
import os.path as path
import filecmp
import subprocess as subp
import shutil
import configuration as conf

#__all__ = ('DataItem', 'start')

class DataItem(object):
    """Represents one entry in the result of the comparison."""
    # THINK consider slots

    # type is one of (None, 'dir', 'file')
    type = None
    TYPE_DIR = 'dir'
    TYPE_FILE = 'file'

    # status is one of (None, 'same', 'diff' 'leftOnly', 'rightOnly', 'unknown')
    _status = None
    STATUS_SAME = 'same'
    STATUS_DIFF = 'diff'
    STATUS_LEFT_ONLY = 'leftOnly'
    STATUS_RIGHT_ONLY = 'rightOnly'
    STATUS_UNKNOWN = 'unknown'
    def onStatusRead(self):
        return self._status
    def onStatusChange(self, newStatus):
        oldStatus = self._status
        if newStatus is not self._status:
            self._status = newStatus
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

    #
    def onAbsoluteLeftFilenameRead(self):
        if not self.leftLocation:
            return None
        else:
            return path.join(self.leftLocation, self.filename)
    def onAbsoluteRightFilenameRead(self):
        if not self.rightLocation:
            return None
        else:
            return path.join(self.rightLocation, self.filename)
    absoluteLeftFilename = property(fget=onAbsoluteLeftFilenameRead)
    absoluteRightFilename = property(fget=onAbsoluteRightFilenameRead)

    def __init__(self, filename):
        self.filename = filename

    def initChildrenDataItems(self, dc, ignore=None):
        """Based on filecmp.dircmp.
           Takes the compare result of filecmp.dircmp, 
           returns the status and children of current DataItem instance being calculated."""

        itmLst = []

        # dc.left and dc.right are based on the 2 dirs given to the original dircmp.
        # i.e., whether these 2 are absolute/relative depends on those 2.
        # see dircmp.phase4
        lDirSet, lFileSet = _sepDirsAndFiles(dc.left, ignore)
        rDirSet, rFileSet = _sepDirsAndFiles(dc.right, ignore)

        weavedDirs = list(lDirSet.union(rDirSet))
        weavedFiles = list(lFileSet.union(rFileSet))

        tmpLst = []

        for d in weavedDirs:
            itm = DataItem(d)
            itm.type, itm.parent = DataItem.TYPE_DIR, self
            if d not in dc.common_dirs:
                # left/right only
                itm.status = DataItem.STATUS_LEFT_ONLY if d in dc.left_only else DataItem.STATUS_RIGHT_ONLY
                leftDir = path.join(dc.left, d)
                rightDir = path.join(dc.right, d)
                itm.children = _quickAndDirty(leftDir, rightDir, itm.status, itm, ignore)
            else:
                # same or diff
                itm.status, itm.children = itm.initChildrenDataItems(dc.subdirs[d], ignore)

            itm.leftLocation = dc.left
            itm.rightLocation = dc.right
            tmpLst.append(itm)

        tmpLst.sort()
        itmLst.extend(tmpLst)

        tmpLst = []

        for f in weavedFiles:
            itm = DataItem(f)
            itm.type, itm.parent = DataItem.TYPE_FILE, self
            if f in dc.left_only:
                itm.status = DataItem.STATUS_LEFT_ONLY
    #            itm.leftLocation = dc.left
            elif f in dc.right_only:
                itm.status = DataItem.STATUS_RIGHT_ONLY
    #            itm.rightLocation = dc.right
            elif f in dc.same_files:
                itm.status = DataItem.STATUS_SAME
    #            itm.leftLocation = dc.left
    #            itm.rightLocation = dc.right
            elif f in dc.diff_files:
                itm.status = DataItem.STATUS_DIFF
    #            itm.leftLocation = dc.left
    #            itm.rightLocation = dc.right
            elif f in dc.funny_files:
                itm.status = DataItem.STATUS_UNKNOWN
            itm.leftLocation = dc.left
            itm.rightLocation = dc.right
            tmpLst.append(itm)

        tmpLst.sort()
        itmLst.extend(tmpLst)

        # status of current dir comparison
        if [itm for itm in itmLst if itm.status is not DataItem.STATUS_SAME]:
            status = DataItem.STATUS_DIFF
        else:
            status = DataItem.STATUS_SAME

        return status, itmLst

    def copyTo(self, src, dest):
        # copy/copytree
        # change left/right location
        # change self status
        # change parent status...pass up
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

    def remove(self, propName):
        delcmd = os.rmdir if self.type is DataItem.TYPE_DIR else os.remove
        delcmd(getattr(self, propName))
        if path.exists(self.absoluteLeftFilename):
            self.status = DataItem.STATUS_LEFT_ONLY
        elif path.exists(self.absoluteRightFilename):
            self.status = DataItem.STATUS_RIGHT_ONLY
        else:
            self.status = None

    # only available to non-directories
    def compareLrFiles(self):
        if self.type is not DataItem.TYPE_FILE:
            raise TypeError, 'method <compareLrFiles> is only available to non-directories'
        if self.status is DataItem.STATUS_DIFF:
            subp.Popen((conf.fileCmpCommand, '-d',
                self.absoluteLeftFilename, self.absoluteRightFilename))
        # update status here.

    # only available to directories
    def notifyChildUpdate(self, child):
        if self.type is not DataItem.TYPE_DIR:
            raise TypeError, 'method <notifyChildUpdate> is only available to directories'
        if self.status is DataItem.STATUS_DIFF and child.status is DataItem.STATUS_SAME:
            for each in self.children:
                if each.status is not DataItem.STATUS_SAME:
                    return
            # this will trigger 'onPropertyChange'
            self.status = DataItem.STATUS_SAME

#    def installController(self, controller):
#        self.updateUI = controller.updateUI

    def refresh(self):
        pass

    def lower(self):
        return self.filename.lower()

    # THINK consider __cmp__
    def __lt__(self, o):
        """Used by list.sort(). Ignores case."""
        return self.lower().__le__(o.lower())

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

def start(dir1, dir2, ignore=None):
    """Accepts 2 strings representing directories."""
    # TODO deal with non-existing dirs and covert files to dirs
    # THINK absolute/relative path
    # THINK funny ones
    dc = filecmp.dircmp(dir1, dir2, ignore)
    rootDataItem = DataItem('rootDataItem')
    rootDataItem.type = DataItem.TYPE_DIR
    rootDataItem.status, rootDataItem.children = rootDataItem.initChildrenDataItems(dc, ignore=ignore)
    rootDataItem.leftLocation = dir1
    rootDataItem.rightLocation = dir2
    return rootDataItem


# ----------  helpers  ----------
def _sepDirsAndFiles(d, ignore=None):
    """Seperates subdirs and files in a given dirs into two sets, and returns them."""
    # os.listdir gives names without paths
    nameSet = set(os.listdir(d))
    if ignore:
        nameSet = nameSet.difference(ignore)
    dirSet = set([f for f in nameSet if path.isdir(path.join(d, f))])
    fileSet = nameSet.difference(dirSet)
    return dirSet, fileSet

def _quickAndDirty(leftBaseDir, rightBaseDir, status, parent, ignore=None):
    """Recursively creates DataItem objects for given dir using given status."""
    baseDir = leftBaseDir if status is DataItem.STATUS_LEFT_ONLY else rightBaseDir
    nameSet = set(os.listdir(baseDir))
    if ignore:
        nameSet = nameSet.difference(ignore)

    dirLst = [f for f in nameSet if path.isdir(path.join(baseDir, f))]
    fileSet = nameSet.difference(dirLst)

    itmList = []
    for i in os.listdir(baseDir):
        itm = DataItem(i)
        itm.parent = parent
        itm.leftLocation = leftBaseDir
        itm.rightLocation = rightBaseDir
        if path.isdir((path.join(baseDir, i))):
            itm.type = DataItem.TYPE_DIR
            itm.status, itm.children = _quickAndDirty(path.join(leftBaseDir, i),
                    path.join(rightBaseDir, i), status, itm, ignore)
            itmList.append(itm)
        else:
            itm.type = DataItem.TYPE_FILE
            itm.status = status
            itmList.append(itm)
    return itmList

