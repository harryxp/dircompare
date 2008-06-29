import os
import os.path as path
import filecmp

class Model():
    """The data model used by the controller to render the view."""

    # a list of Item objects. this is the only API to client code.
    items = []

    def __init__(self, dir1, dir2, ignore=None, hide=None):
        """Accepts 2 strings representing directories."""
        # TODO deal with non-existing dirs and covert files to dirs
        # THINK absolute/relative path
        # THINK funny ones
        dc = filecmp.dircmp(dir1, dir2, ignore, hide)
        rootStatus, self.items = self._genItems(dc)

    def _genItems(self, dc):
        """Based on filecmp.dircmp."""
        
        itmLst = []
        
        # dc.left and dc.right are based on the 2 dirs given to the original dircmp.
        # i.e., whether these 2 are absolute/relative depends on those 2.
        # see dircmp.phase4
        lDirSet, lFileSet = _sepDirsAndFiles(dc.left)
        rDirSet, rFileSet = _sepDirsAndFiles(dc.right)
        
        weavedDirs = list(lDirSet.union(rDirSet))
        weavedFiles = list(lFileSet.union(rFileSet))
        
        tmpLst = []
        
        for d in weavedDirs:
            itm = Item(d)
            itm.type = Item.TYPE_DIR
            if d not in dc.common_dirs:
                # left/right only
                dirStr, status = (path.join(dc.left, d), Item.STATUS_LEFT_ONLY) \
                    if d in dc.left_only \
                    else (path.join(dc.right, d), Item.STATUS_RIGHT_ONLY)
                itm.status, itm.children = _quickAndDirty(dirStr, status)
                if d in dc.left_only:
                    itm.leftLocation = dc.left
                else:
                    itm.rightLocation = dc.right
            else:
                # same or diff
                itm.status, itm.children = self._genItems(dc.subdirs[d])
                itm.leftLocation = dc.left
                itm.rightLocation = dc.right
            tmpLst.append(itm)
        
        tmpLst.sort()
        itmLst.extend(tmpLst)
        
        tmpLst = []
        
        for f in weavedFiles:
            itm = Item(f)
            itm.type = Item.TYPE_FILE
            if f in dc.left_only:
                itm.status = Item.STATUS_LEFT_ONLY
                itm.leftLocation = dc.left
            elif f in dc.right_only:
                itm.status = Item.STATUS_RIGHT_ONLY
                itm.rightLocation = dc.right
            elif f in dc.same_files:
                itm.status = Item.STATUS_SAME
                itm.leftLocation = dc.left
                itm.rightLocation = dc.right
            elif f in dc.diff_files:
                itm.status = Item.STATUS_DIFF
                itm.leftLocation = dc.left
                itm.rightLocation = dc.right
            elif f in dc.funny_files:
                itm.status = Item.STATUS_FUNNY
            tmpLst.append(itm)
        
        tmpLst.sort()
        itmLst.extend(tmpLst)
        
        # status of current dir comparison
        if [itm for itm in itmLst if itm.status is not Item.STATUS_SAME]:
            status = Item.STATUS_DIFF
        else:
            status = Item.STATUS_SAME
        
        return status, itmLst
        
    def __str__(self):
        temp = []
        for itm in self.items:
            temp.append(itm.__str__() + '\n')
        return ''.join(temp)

# helper
def _sepDirsAndFiles(d):
    """Seperates subdirs and files in a given dirs into two sets, and returns them."""
    names = os.listdir(d)
    dirSet = set([f for f in names if path.isdir(path.join(d, f))])
    fileSet = set(names).difference(dirSet)
    return dirSet, fileSet

def _quickAndDirty(baseDir, status):
    """Recursively creates Item objects for given dir using given status."""
    nameSet = set(os.listdir(baseDir))
    
    dirLst = [f for f in nameSet if path.isdir(path.join(baseDir, f))]
    fileSet = nameSet.difference(dirLst)
    
    itmList = []
    for i in os.listdir(baseDir):
        itm = Item(i)
        if status is Item.STATUS_LEFT_ONLY:
            itm.leftLocation = baseDir
        else: # must be Item.STATUS_RIGHT_ONLY
            itm.rightLocation = baseDir
        if path.isdir((path.join(baseDir, i))):
            itm.type = Item.TYPE_DIR
            itm.status, itm.children = _quickAndDirty(path.join(baseDir, i), status)
            itmList.append(itm)
        else:
            itm.type = Item.TYPE_FILE
            itm.status = status
            itmList.append(itm)
    return status, itmList

class Item():
    """Represents one entry in the result of the comparison."""

    # type is one of (None, 'dir', 'file')
    type = None
    TYPE_DIR = 'dir'
    TYPE_FILE = 'file'

    # status is one of (None, 'same', 'diff' 'leftOnly', 'rightOnly', 'funny')
    status = None
    STATUS_SAME = 'same'
    STATUS_DIFF = 'diff'
    STATUS_LEFT_ONLY = 'leftOnly'
    STATUS_RIGHT_ONLY = 'rightOnly'
    STATUS_FUNNY = 'funny'

    # for file this attr is always None
    # for directory, it's a list of Item objects
    children = None

    # locations of this item
    leftLocation = None
    rightLocation = None

    def __init__(self, text):
        self.text = text

    def lower(self):
        return self.text.lower()

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
        return ''.join(('\n[text: ', replaceNone(self.text), ', ',
                         'type: ', replaceNone(self.type), ', ',
                         'status: ', replaceNone(self.status), ', ',
                         'leftLocation: ', replaceNone(self.leftLocation), ', ',
                         'rightLocation: ', replaceNone(self.rightLocation), ', ',
                         'children: ', `self.children`, ']'))
    