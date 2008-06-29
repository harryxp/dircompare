# -*- coding: utf-8 -*-

import os, logging
import model, view
from configuration import *

# THINK upper limit
treeItemId = 0L

# event handlers
def genOnItemActivated(srcTree, otherTree):
    """Generates closures as handlers on item activated."""
    def handler(event):
        srcTreeItem = event.GetItem()
        pyData = srcTree.GetPyData(srcTreeItem)
        dataItem = pyData.data
        pair = itemDict[pyData]
        # this '==' cannot be replaced by 'is' since the TreeItemId object
        # returned by event.GetItem() is almost always different from the reserved one
        otherTreeItem = pair[1] if pair[0] == srcTreeItem else pair[0]
        if not srcTree.IsExpanded(srcTreeItem):
            #logging.debug('srcTreeItem not expanded. Expanding...')
            if dataItem.type is model.Item.TYPE_DIR \
                              and not srcTree.ItemHasChildren(srcTreeItem):
                #logging.debug('generating tree items...')
                genTrees(dataItem.children, *pair)
            elif dataItem.type is model.Item.TYPE_FILE:
                # TODO
                pass
            otherTree.Expand(otherTreeItem)
        else:
            #logging.debug('srcTreeItem already expanded. Collapsing...')
            otherTree.Collapse(otherTreeItem)
        srcTree.Refresh()
        otherTree.Refresh()
        event.Skip()
    return handler

def onScroll(event):
    logging.debug('scroll')

# ---------------------------------------------------

def genTrees(dataItems, lParent, rParent):
    """Populates the trees using given dataItems."""
    for dataItem in dataItems:
        dirFlag = dataItem.type is model.Item.TYPE_DIR
        if dataItem.status is model.Item.STATUS_LEFT_ONLY:
            lText, lColor, lBgColor = dataItem.text, oneSideTextColor, oneSideBgColor
            rText, rColor, rBgColor = '', oneSideTextColor, oneSideBgColor
            lImgOps = ((fldImg, view.wx.TreeItemIcon_Normal), (fldOpnImg, view.wx.TreeItemIcon_Expanded)) \
                if dirFlag \
                else ((fileImg, view.wx.TreeItemIcon_Normal), (fileImg, view.wx.TreeItemIcon_Selected))
            rImgOps = ((naImg, view.wx.TreeItemIcon_Normal), (naImg, view.wx.TreeItemIcon_Expanded)) \
                if dirFlag \
                else ((naImg, view.wx.TreeItemIcon_Normal), (naImg, view.wx.TreeItemIcon_Selected))
        elif dataItem.status is model.Item.STATUS_RIGHT_ONLY:
            lText, lColor, lBgColor = '', oneSideTextColor, oneSideBgColor
            rText, rColor, rBgColor = dataItem.text, oneSideTextColor, oneSideBgColor
            lImgOps = ((naImg, view.wx.TreeItemIcon_Normal), (naImg, view.wx.TreeItemIcon_Expanded)) \
                if dirFlag \
                else ((naImg, view.wx.TreeItemIcon_Normal), (naImg, view.wx.TreeItemIcon_Selected))
            rImgOps = ((fldImg, view.wx.TreeItemIcon_Normal), (fldOpnImg, view.wx.TreeItemIcon_Expanded)) \
                if dirFlag \
                else ((fileImg, view.wx.TreeItemIcon_Normal), (fileImg, view.wx.TreeItemIcon_Selected))
        elif dataItem.status is model.Item.STATUS_SAME:
            lText, lColor, lBgColor = dataItem.text, normalTextColor, normalBgColor
            rText, rColor, rBgColor = dataItem.text, normalTextColor, normalBgColor
            lImgOps = ((fldImg, view.wx.TreeItemIcon_Normal), (fldOpnImg, view.wx.TreeItemIcon_Expanded)) \
                if dirFlag \
                else ((fileImg, view.wx.TreeItemIcon_Normal), (fileImg, view.wx.TreeItemIcon_Selected))
            rImgOps = ((fldImg, view.wx.TreeItemIcon_Normal), (fldOpnImg, view.wx.TreeItemIcon_Expanded)) \
                if dirFlag \
                else ((fileImg, view.wx.TreeItemIcon_Normal), (fileImg, view.wx.TreeItemIcon_Selected))
        elif dataItem.status is model.Item.STATUS_DIFF:
            lText, lColor, lBgColor = dataItem.text, diffTextColor, diffBgColor
            rText, rColor, rBgColor = dataItem.text, diffTextColor, diffBgColor
            lImgOps = ((fldImg, view.wx.TreeItemIcon_Normal), (fldOpnImg, view.wx.TreeItemIcon_Expanded)) \
                if dirFlag \
                else ((fileImg, view.wx.TreeItemIcon_Normal), (fileImg, view.wx.TreeItemIcon_Selected))
            rImgOps = ((fldImg, view.wx.TreeItemIcon_Normal), (fldOpnImg, view.wx.TreeItemIcon_Expanded)) \
                if dirFlag \
                else ((fileImg, view.wx.TreeItemIcon_Normal), (fileImg, view.wx.TreeItemIcon_Selected))

        global treeItemId
        global itemDict
        
        lTreeItem = view.lTree.AppendItem(lParent, lText)
        view.lTree.SetItemTextColour(lTreeItem, lColor)
        view.lTree.SetItemBackgroundColour(lTreeItem, lBgColor)
        for op in lImgOps:
            view.lTree.SetItemImage(lTreeItem, op[0], op[1])
        
        rTreeItem = view.rTree.AppendItem(rParent, rText)
        view.rTree.SetItemTextColour(rTreeItem, rColor)
        view.rTree.SetItemBackgroundColour(rTreeItem, rBgColor)
        for op in rImgOps:
            view.rTree.SetItemImage(rTreeItem, op[0], op[1])

        pyData = PyData(treeItemId, dataItem)
        treeItemId += 1
        
        view.lTree.SetPyData(lTreeItem, pyData)
        view.rTree.SetPyData(rTreeItem, pyData)
        itemDict[pyData] = (lTreeItem, rTreeItem)
    
class PyData():
    """A class for tracking tree items."""
    def __init__(self, id, data):
        self.id = id
        self.data = data

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        #return ' '.join(('id:', `self.id`, ',', 'data:', `self.data`))
        return ' '.join(('id:', `self.id`))

# ---------------------------------------------------

logging.basicConfig(level=eval(loggingLevel),
				format='%(asctime)s %(levelname)s %(message)s')
				#filename='app.log',
				#filemode='w')

app = view.wx.App(redirect=False)
mod = model.Model(leftPath, rightPath, ignore, hide)
dataItems = mod.items
itemDict = {}

frame = view.MainFrame()

lRoot = view.lTree.AddRoot('lroot')
rRoot = view.rTree.AddRoot('rroot')

pyData = PyData(treeItemId, model.Item('root'))
treeItemId += 1

view.lTree.SetPyData(lRoot, pyData)
view.rTree.SetPyData(rRoot, pyData)
itemDict[pyData] = (lRoot, rRoot)

# binding handlers
view.lTree.Bind(view.wx.EVT_TREE_ITEM_ACTIVATED, genOnItemActivated(view.lTree, view.rTree))
view.rTree.Bind(view.wx.EVT_TREE_ITEM_ACTIVATED, genOnItemActivated(view.rTree, view.lTree))

imgSz = (16, 16)
imgLst = view.wx.ImageList(imgSz[0], imgSz[1])
fldImg = imgLst.Add(view.wx.ArtProvider_GetBitmap(view.wx.ART_FOLDER, view.wx.ART_OTHER, imgSz))
fldOpnImg = imgLst.Add(view.wx.ArtProvider_GetBitmap(view.wx.ART_FILE_OPEN, view.wx.ART_OTHER, imgSz))
fileImg = imgLst.Add(view.wx.ArtProvider_GetBitmap(view.wx.ART_NORMAL_FILE, view.wx.ART_OTHER, imgSz))
naImg  = imgLst.Add(view.wx.ArtProvider_GetBitmap(view.wx.ART_MISSING_IMAGE, view.wx.ART_OTHER, imgSz))

view.lTree.SetImageList(imgLst)
view.rTree.SetImageList(imgLst)

genTrees(dataItems, view.lTree.GetRootItem(), view.rTree.GetRootItem())
frame.Show()
app.MainLoop()
