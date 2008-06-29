# -*- coding: utf-8 -*-

# THINK upper limit
treeItemId = 0L

# event handlers
def genOnItemActivated(srcTree, otherTree):
    """Generates closures as handlers on tree item activated."""
    def handler(event):
        srcTreeItem = event.GetItem()
        pyData = srcTree.GetPyData(srcTreeItem)
        dataItem, pair = pyData.data, pyData.pair
        # this '==' cannot be replaced by 'is' since the TreeItemId object
        # returned by event.GetItem() is almost always different from the saved one
        otherTreeItem = pair[1] if pair[0] == srcTreeItem else pair[0]
        if not srcTree.IsExpanded(srcTreeItem):
            #logging.debug('srcTreeItem not expanded. Expanding...')
            if dataItem.type is DataItem.TYPE_DIR \
                              and not srcTree.ItemHasChildren(srcTreeItem):
                #logging.debug('generating tree items...')
                drawNodes(dataItem.children, *pair)
            elif dataItem.type is DataItem.TYPE_FILE:
                dataItem.compareLrFiles()
#                frame.Disable()
            otherTree.Expand(otherTreeItem)
        else:
            #logging.debug('srcTreeItem already expanded. Collapsing...')
            otherTree.Collapse(otherTreeItem)
        srcTree.Refresh()
        otherTree.Refresh()
        event.Skip()
    return handler

def genOnSelChanged(srcTree, otherTree):
    """Generates closures as handlers on tree item selection changed."""
    def handler(event):
        if otherTree:
            otherTree.UnselectAll()
#            pair = srcTree.GetPyData(event.GetItem()).pair
#            otherItem = pair[0] if otherTree is lTree else pair[1]
#            otherTree.SelectItem(otherItem)
        event.Skip()
    return handler

def genOnCopy(srcTree):
    """Generates closures as handlers on copying items from one side to the other."""
    def onCopy(event):
        for each in srcTree.GetSelections():
            dataItem = srcTree.GetPyData(each).data
            if dataItem.status not in (DataItem.STATUS_SAME, DataItem.STATUS_UNKNOWN):
                src, dest = 'leftLocation' if srcTree is lTree else 'rightLocation', \
                            'leftLocation' if srcTree is rTree else 'rightLocation'
                dataItem.copyTo(src, dest)
        event.Skip()
    return onCopy

def onDel(event):
    window = wx.Window.FindFocus()
    if window not in (lTree, rTree):
        return
    propName = 'absoluteLeftFilename' if window is lTree else 'absoluteRightFilename'
    for each in window.GetSelections():
        dataItem = window.GetPyData(each).data
        dataItem.remove(propName)

def onScroll(event):
    logging.debug('scroll')

# ---------------------------------------------------

class PyData(object):
    """A class for tracking tree items."""
    def __init__(self, id, data):
        self.id = id
        self.data = data

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        #return ' '.join(('id:', `self.id`, ',', 'data:', `self.data`))
        return ' '.join(('id:', `self.id`))

def figureTreeItemStyle(dataItem):
    dirFlag = dataItem.type is DataItem.TYPE_DIR
    if dataItem.status is DataItem.STATUS_LEFT_ONLY:
        lText = dataItem.filename
        rText = ''
        lTreeItemStyle = TreeItemStyle.DIR_ONESIDEONLY if dirFlag else TreeItemStyle.FILE_ONESIDEONLY
        rTreeItemStyle = TreeItemStyle.DIR_ABSENT if dirFlag else TreeItemStyle.FILE_ABSENT
    elif dataItem.status is DataItem.STATUS_RIGHT_ONLY:
        lTreeItemStyle = TreeItemStyle.DIR_ABSENT if dirFlag else TreeItemStyle.FILE_ABSENT
        rTreeItemStyle = TreeItemStyle.DIR_ONESIDEONLY if dirFlag else TreeItemStyle.FILE_ONESIDEONLY
        lText = ''
        rText = dataItem.filename
    elif dataItem.status is DataItem.STATUS_SAME:
        lText = dataItem.filename
        rText = dataItem.filename
        lTreeItemStyle = TreeItemStyle.DIR_SAME if dirFlag else TreeItemStyle.FILE_SAME
        rTreeItemStyle = TreeItemStyle.DIR_SAME if dirFlag else TreeItemStyle.FILE_SAME
    elif dataItem.status is DataItem.STATUS_DIFF:
        lText = dataItem.filename
        rText = dataItem.filename
        lTreeItemStyle = TreeItemStyle.DIR_DIFF if dirFlag else TreeItemStyle.FILE_DIFF
        rTreeItemStyle = TreeItemStyle.DIR_DIFF if dirFlag else TreeItemStyle.FILE_DIFF
    return lText, lTreeItemStyle, rText, rTreeItemStyle

#           pair_of_tree_items
#                    ^
#                    |
#                    |
#                    |     ------> data_item
#                 py_data  <------
#
def drawNodes(dataItems, lParent, rParent):
    """Populates the trees using given dataItems."""

    for dataItem in dataItems:
        global treeItemId

        pyData = PyData(treeItemId, dataItem)
        dataItem.pyData = pyData
        treeItemId += 1

        lTreeItem = lTree.AppendItem(lParent, '')
        rTreeItem = rTree.AppendItem(rParent, '')
        lTree.SetPyData(lTreeItem, pyData)
        rTree.SetPyData(rTreeItem, pyData)

        pyData.pair = lTreeItem, rTreeItem

        updateTreeItemPairUI(dataItem)

def updateTreeItemPairUI(dataItem):
    lTreeItem, rTreeItem = dataItem.pyData.pair

    if not dataItem.status:
        lTree.Delete(lTreeItem)
        rTree.Delete(rTreeItem)
        return

    lText, lTreeItemStyle, rText, rTreeItemStyle = figureTreeItemStyle(dataItem)

    def updateTreeItemUI(tree, treeItem, text, treeItemStyle):
        tree.SetItemText(treeItem, text)
        tree.SetItemTextColour(treeItem, treeItemStyle.color)
        tree.SetItemBackgroundColour(treeItem, treeItemStyle.bgColor)
        for icon in treeItemStyle.icons:
            tree.SetItemImage(treeItem, *icon)

    updateTreeItemUI(lTree, lTreeItem, lText, lTreeItemStyle)
    updateTreeItemUI(rTree, rTreeItem, rText, rTreeItemStyle)

def updateUI(self):
    """Listener on the model."""
    try:
        pair = self.pyData.pair
        updateTreeItemPairUI(self)
    except AttributeError:
        pass

# -------------------------start-------------------------
import configuration as conf

import logging
logging.basicConfig(level=eval(conf.loggingLevel),
                format='%(asctime)s %(levelname)s %(message)s')
                #filename='app.log',
                #filemode='w')

# check path
import os.path as path
if not (path.isdir(conf.leftPath) and path.isdir(conf.rightPath)):
    msg = 'Invalid given path(s).'
    logging.info(msg)
    import sys
    sys.exit(msg)
#else:
    # make paths absolute
#    conf.leftPath = path.abs(conf.leftPath)
#    conf.rightPath = path.abs(conf.rightPath)

import cmprslt, view
# install shortcuts for performance
DataItem = cmprslt.DataItem
Tree = view.Tree
lTree = view.lTree
rTree = view.rTree
lRoot = view.lRoot
rRoot = view.rRoot
TreeItemStyle = view.TreeItemStyle
frame = view.frame

# install listener
DataItem.updateUI = updateUI

# start comparison
rootDataItem = cmprslt.start(conf.leftPath, conf.rightPath, conf.ignore)
topItems = rootDataItem.children
drawNodes(topItems, lRoot, rRoot)

pyData = PyData(treeItemId, rootDataItem)
pyData.pair = lRoot, rRoot
treeItemId += 1

lTree.SetPyData(lRoot, pyData)
rTree.SetPyData(rRoot, pyData)

# binding handlers
import wx
lTree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, genOnItemActivated(lTree, rTree))
rTree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, genOnItemActivated(rTree, lTree))
lTree.Bind(wx.EVT_TREE_SEL_CHANGED, genOnSelChanged(lTree, rTree))
rTree.Bind(wx.EVT_TREE_SEL_CHANGED, genOnSelChanged(rTree, lTree))
frame.Bind(wx.EVT_MENU, genOnCopy(lTree), frame.btn_cplr)
frame.Bind(wx.EVT_MENU, genOnCopy(rTree), frame.btn_cprl)
frame.Bind(wx.EVT_MENU, onDel, frame.btn_del)

view.show()

