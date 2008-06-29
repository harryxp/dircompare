# -*- coding: utf-8 -*-

import wx
import configuration as conf

#__all__ = ('showFrame')#, 'lTree', 'rTree')

class MainFrame(wx.Frame):
    # (textlabel, property name)
    # textlabel = None means a seperator
    toolbarData = ((' > ', 'btn_cplr'),
            (' < ', 'btn_cprl'),
            (None, None),
            (' D ', 'btn_del'),
            (None, None),
            (' C ', 'btn_cmp'),
            (None, None),
            (' ? ', 'btn_hlp'))
    def __init__(self):
        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY, size=conf.defaultFrameSize)
        self.SetTitle('DirCompare')
        self.CenterOnScreen()
        self.splitter = Splitter(self)
        self.createToolBar()

    def createToolBar(self):
        def createToolBarItem(label, attrName):
            if not label:
                toolBar.AddSeparator()
                return
            tool = toolBar.AddLabelTool(wx.ID_ANY, label, wx.NullBitmap)
            setattr(self, attrName, tool)
        toolBar = self.CreateToolBar(wx.TB_TEXT | wx.TB_NOICONS)
        map(createToolBarItem, *zip(*self.toolbarData))
        toolBar.Realize()

class Splitter(wx.SplitterWindow):
    def __init__(self, parent, id=wx.ID_ANY):
        wx.SplitterWindow.__init__(self, parent)
        global lTree
        lTree = Tree(self)
        global rTree
        rTree = Tree(self)
        self.SplitVertically(lTree, rTree)

class Tree(wx.TreeCtrl):
    style = wx.TR_NO_BUTTONS | wx.TR_NO_LINES | \
            wx.TR_MULTIPLE | wx.TR_FULL_ROW_HIGHLIGHT | \
            wx.TR_HIDE_ROOT #^(wx.VSCROLL | wx.HSCROLL

    # THINK shall we handle *args and **kwargs?
    def __init__(self, parent):
        wx.TreeCtrl.__init__(self, parent, style=Tree.style)

class TreeItemStyle(object):
    def __init__(self, color, bgColor, icons):
        self.color = color
        self.bgColor = bgColor
        self.icons = icons

app = wx.App(redirect=False)
frame = MainFrame()

lRoot = lTree.AddRoot('lroot')
rRoot = rTree.AddRoot('rroot')

# setup tree artworks
imgSz = (16, 16)
imgLst = wx.ImageList(*imgSz)
Tree.fldImg = imgLst.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, imgSz))
Tree.fldOpnImg = imgLst.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN, wx.ART_OTHER, imgSz))
Tree.fileImg = imgLst.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, imgSz))
Tree.naImg  = imgLst.Add(wx.ArtProvider_GetBitmap(wx.ART_MISSING_IMAGE, wx.ART_OTHER, imgSz))
lTree.SetImageList(imgLst)
rTree.SetImageList(imgLst)

# setup tree item styles
TreeItemStyle.FILE_SAME = TreeItemStyle(conf.normalTextColor, conf.normalBgColor,
                            ((Tree.fileImg, wx.TreeItemIcon_Normal),
                            (Tree.fileImg, wx.TreeItemIcon_Selected)))
TreeItemStyle.FILE_DIFF = TreeItemStyle(conf.diffTextColor, conf.diffBgColor,
                            ((Tree.fileImg, wx.TreeItemIcon_Normal),
                            (Tree.fileImg, wx.TreeItemIcon_Selected)))
TreeItemStyle.FILE_ONESIDEONLY = TreeItemStyle(conf.oneSideTextColor, conf.oneSideBgColor,
                            ((Tree.fileImg, wx.TreeItemIcon_Normal),
                            (Tree.fileImg, wx.TreeItemIcon_Selected)))
TreeItemStyle.FILE_ABSENT = TreeItemStyle(conf.oneSideTextColor, conf.oneSideBgColor,
                            ((Tree.naImg, wx.TreeItemIcon_Normal),
                            (Tree.naImg, wx.TreeItemIcon_Selected)))
TreeItemStyle.DIR_SAME = TreeItemStyle(conf.normalTextColor, conf.normalBgColor,
                            ((Tree.fldImg, wx.TreeItemIcon_Normal),
                            (Tree.fldOpnImg, wx.TreeItemIcon_Expanded)))
TreeItemStyle.DIR_DIFF = TreeItemStyle(conf.diffTextColor, conf.diffBgColor,
                            ((Tree.fldImg, wx.TreeItemIcon_Normal),
                            (Tree.fldOpnImg, wx.TreeItemIcon_Expanded)))
TreeItemStyle.DIR_ONESIDEONLY = TreeItemStyle(conf.oneSideTextColor, conf.oneSideBgColor,
                            ((Tree.fldImg, wx.TreeItemIcon_Normal),
                            (Tree.fldOpnImg, wx.TreeItemIcon_Expanded)))
TreeItemStyle.DIR_ABSENT = TreeItemStyle(conf.oneSideTextColor, conf.oneSideBgColor,
                            ((Tree.naImg, wx.TreeItemIcon_Normal),
                            (Tree.naImg, wx.TreeItemIcon_Expanded)))

def show():
    """Brings up the GUI."""
    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    show()

