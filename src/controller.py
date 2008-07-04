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

import os.path as path

##############################
# event handlers             #
##############################
def genOnItemActivated(srcTree, otherTree):
    """Generates closures as handlers on tree item activated."""
    def handler(event):
        srcTreeItem = event.GetItem()
        pyData = srcTree.GetPyData(srcTreeItem)
        dataItem, otherTreeItem = pyData.data, pyData.getOtherTreeItem(srcTreeItem)
        if not srcTree.IsExpanded(srcTreeItem):
            if dataItem.type is DataItem.TYPE_DIR \
                              and not srcTree.ItemHasChildren(srcTreeItem):
                drawNodes(dataItem.children, pyData.lTreeItem, pyData.rTreeItem)
            elif dataItem.type is DataItem.TYPE_FILE:
                if not path.exists(conf.fileCmpCommand):
                    alert('GVim installation not found. Please set it up correctly in configuration.py.')
                dataItem.compareFiles()
            otherTree.Expand(otherTreeItem)
        else:
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
    return handler

def genOnCopy(srcTree):
    """Generates closures as handlers on copying items from one side to the other."""
    # TODO multiple copy
    def onCopy(event):
        selections = srcTree.GetSelections()
        if len(selections) > 1:
            info('Copying multiple items is not allowed now',
                    caption='Operation not supported')
            return
        for each in selections:
            dataItem = srcTree.GetPyData(each).data
            src, dest = 'leftLocation' if srcTree is lTree else 'rightLocation', \
                        'leftLocation' if srcTree is rTree else 'rightLocation'
            dataItem.copyTo(src, dest)
        event.Skip()
    return onCopy

def onDel(event):
    # TODO multiple del
    window = wx.Window.FindFocus()
    if window not in (lTree, rTree):
        return
    propName = 'leftFile' if window is lTree else 'rightFile'
    selections = window.GetSelections()
    if len(selections) > 1:
        info('Deleting multiple items is not allowed now',
                caption='Operation not supported')
        return
    for each in selections:
        dataItem = window.GetPyData(each).data
        dataItem.delete(propName)

def onCmp(event):
    if not path.exists(conf.fileCmpCommand):
        alert('GVim installation not found. Please set it up correctly in configuration.py.')
    # TODO multiple cmp
    window = wx.Window.FindFocus()
    if window not in (lTree, rTree):
        return
    selections = window.GetSelections()
    if len(selections) > 1:
        info('Please choose a file item to compare.',
                caption='Operation not supported')
        return
    for each in selections:
        dataItem = window.GetPyData(each).data
        dataItem.compareFiles()

def onRefreshAll(event):
    try:
       cmpSession
       startCmp(cmpSession)
    except NameError:
       alert('Nothing to refresh.')

def onFocus(event):
    window = wx.Window.FindFocus()
    if window not in (lTree, rTree):
        return
    selections = window.GetSelections()
    if len(selections) > 1:
        info('Please choose a valid folder item to focus.',
                caption='Operation not supported')
        return
    for each in selections:
        dataItem = window.GetPyData(each).data
        global cmpSession
        cmpSession = model.CompareSession(dataItem.leftFile, dataItem.rightFile, cmpSession.ignore)
        startCmp(cmpSession)

def onBrowse(event):
    # TODO multiple browse
    window = wx.Window.FindFocus()
    if window not in (lTree, rTree):
        return
    propName = 'leftFile' if window is lTree else 'rightFile'
    for each in window.GetSelections():
        dataItem = window.GetPyData(each).data
        dataItem.browse(propName)

def onNew(event):
    dlg = view.SessionDialog('New')
    if dlg.ShowModal() == wx.ID_OK:
        leftPath, rightPath, ignore = \
                dlg.leftText.GetValue(), dlg.rightText.GetValue(), \
                [ign.strip() for ign in dlg.ignoreText.GetValue().split(',')]
        global cmpSession
        cmpSession = model.CompareSession(leftPath, rightPath, ignore)
        startCmp(cmpSession)
    dlg.Destroy()

def onSave(event):
    import os, cPickle
    try:
        cmpSession
    except NameError:
        alert('No session available')
        return
    cfmdlg = view.SessionDialog('Save', cmpSession)
    if cfmdlg.ShowModal() == wx.ID_OK:
        wildcard = 'DirCompare Session (*.dcs)|*.dcs'
        savefile = wx.FileSelector('Save a session file as', default_path=os.getcwd(),
                wildcard=wildcard, flags=wx.SAVE | wx.OVERWRITE_PROMPT)
        if savefile:
            fp = open(savefile, 'wb')
            # TODO exception handling
            cPickle.dump(cmpSession, fp, 2)
            fp.close()
    cfmdlg.Destroy()

def onLoad(event):
    import os, cPickle
    wildcard = 'DirCompare Session (*.dcs)|*.dcs|' \
               'All files (*.*)|*.*'
    loadfile = wx.FileSelector('Open a session file', default_path=os.getcwd(),
            wildcard=wildcard, flags=wx.OPEN)
    if loadfile:
        try:
            fp = open(loadfile, 'rb')
            session = cPickle.load(fp)
            cfmdlg = view.SessionDialog('Load', session)
            if cfmdlg.ShowModal() == wx.ID_OK:
                global cmpSession
                cmpSession = session
                startCmp(cmpSession)
            cfmdlg.Destroy()
        # TODO see Python Lib Ref 13.1.3, more exceptions can be thrown here
        except (IOError, cPickle.UnpicklingError):
            alert('Invalid session file.')

def onAbout(event):
    aboutinfo = wx.AboutDialogInfo()
    aboutinfo.SetName('DirCompare')
    aboutinfo.SetVersion('0.2')
    aboutinfo.SetLicense('GNU')
#    aboutinfo.SetWebSite('https://sourceforge.net/projects/dircompare')
    aboutinfo.SetWebSite('http://code.google.com/p/dircompare')
    aboutinfo.AddDeveloper('Pan Xingzhi')
    wx.AboutBox(aboutinfo)

def onHelp(event):
    info('Please visit http://code.google.com/p/dircompare \n' +
            '         or send email to vengeance.storm@gmail.com. \n' +
            '                                       Thanks!', 'Help')

def genOnScroll(srcTree, otherTree, ins):
    def onScroll(event):
        event.Skip()
        def syncScroll(srcTree, otherTree):
            srcTreeItem = srcTree.GetFirstVisibleItem()
            otherTreeItem = srcTree.GetPyData(srcTreeItem).getOtherTreeItem(srcTreeItem)
            otherTree.ScrollTo(otherTreeItem)
        wx.CallAfter(syncScroll, srcTree, otherTree)
    return onScroll

##############################
# PyData                     #
##############################

class PyData(object):

    """PyData objects are used to connect left/right wx tree items
    with each other and with the data item (the DataItem object).
    Instances of this class are *attached* to wx tree items.

                tree_items
                    |^
                    ||
                    ||
                    V|     ------> data_item
                 py_data  <------
    """

    def __init__(self, data, lTreeItem, rTreeItem):
        self.data = data
        self.lTreeItem = lTreeItem
        self.rTreeItem = rTreeItem

    def getOtherTreeItem(self, srcTreeItem):
        try:
            self.lTreeItem
            self.rTreeItem
        except AttributeError, e:
            raise AttributeError('lTreeItem or rTreeItem not set!')

        # this '==' cannot be replaced by 'is' since the TreeItemId object
        # returned by event.GetItem() is almost always different from the saved one
        if srcTreeItem == self.lTreeItem:
            otherTreeItem = self.rTreeItem
        elif srcTreeItem == self.rTreeItem:
            otherTreeItem = self.lTreeItem
        else:
            raise ValueError('srcTreeItem is neither lTreeItem nor rTreeItem')
        return otherTreeItem

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        #return ' '.join(('id:', `self.id`, ',', 'data:', `self.data`))
        return ' '.join(('data:', `self.data`))

##############################
# Utilities                  #
##############################
def startCmp(session):
    leftPath, rightPath, ignore = \
            session.leftPath, session.rightPath, session.ignore
    # check path
    if not (path.isdir(leftPath) and path.isdir(rightPath)):
        msg = 'Invalid given path(s).'
        alert(msg)
        return

    # start comparison
    global rootDataItem
    rootDataItem = model.start(leftPath, rightPath, ignore)
    drawNodes(rootDataItem.children, lRoot, rRoot)
    pyData = PyData(rootDataItem, lRoot, rRoot)
    lTree.SetPyData(lRoot, pyData)
    rTree.SetPyData(rRoot, pyData)
    rootDataItem.pyData = pyData

    lTextCtrl.SetValue(path.normpath(leftPath))
    rTextCtrl.SetValue(path.normpath(rightPath))

def refresh():
    pass

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

def drawNodes(dataItems, lParent, rParent):
    """Populates the trees using given dataItems."""
    lTree.DeleteChildren(lParent)
    rTree.DeleteChildren(rParent)

    for dataItem in dataItems:
        lTreeItem = lTree.AppendItem(lParent, '')
        rTreeItem = rTree.AppendItem(rParent, '')

        pyData = PyData(dataItem, lTreeItem, rTreeItem)
        dataItem.pyData = pyData

        lTree.SetPyData(lTreeItem, pyData)
        rTree.SetPyData(rTreeItem, pyData)

        updateTreeItemPairUI(dataItem)

def updateTreeItemPairUI(dataItem):
    lTreeItem, rTreeItem = dataItem.pyData.lTreeItem, dataItem.pyData.rTreeItem

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
        updateTreeItemPairUI(self)
    except AttributeError:
        pass

def alert(msg, caption='Error'):
    wx.MessageBox(msg, caption, style=wx.OK | wx.ICON_EXCLAMATION, parent=frame)

def info(msg, caption):
    wx.MessageBox(msg, caption, style=wx.OK, parent=frame)

##############################
# start                      #
##############################
import configuration as conf

import logging
logging.basicConfig(level=eval(conf.loggingLevel),
                format='%(asctime)s %(levelname)s %(message)s',
                filename=conf.logFile,
                filemode='a')

import model, view
# install shortcuts for performance
DataItem = model.DataItem
Tree = view.Tree
lTree = view.lTree
rTree = view.rTree
lTextCtrl = view.lTextCtrl
rTextCtrl = view.rTextCtrl
lRoot = view.lRoot
rRoot = view.rRoot
TreeItemStyle = view.TreeItemStyle
frame = view.frame

# install listener
DataItem.updateUI = updateUI

# bind handlers
import wx
lTree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, genOnItemActivated(lTree, rTree))
rTree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, genOnItemActivated(rTree, lTree))
lTree.Bind(wx.EVT_TREE_SEL_CHANGED, genOnSelChanged(lTree, rTree))
rTree.Bind(wx.EVT_TREE_SEL_CHANGED, genOnSelChanged(rTree, lTree))

# sync scrolling
lTree.Bind(wx.EVT_SCROLLWIN, genOnScroll(lTree, rTree, 'SCROLLWIN'))
rTree.Bind(wx.EVT_SCROLLWIN, genOnScroll(rTree, lTree, 'SCROLLWIN'))
lTree.Bind(wx.EVT_SCROLLWIN_LINEUP, genOnScroll(lTree, rTree, 'LINEUP'))
rTree.Bind(wx.EVT_SCROLLWIN_LINEUP, genOnScroll(rTree, lTree, 'LINEUP'))
lTree.Bind(wx.EVT_SCROLLWIN_LINEDOWN, genOnScroll(lTree, rTree, 'LINEDOWN'))
rTree.Bind(wx.EVT_SCROLLWIN_LINEDOWN, genOnScroll(rTree, lTree, 'LINEDOWN'))
lTree.Bind(wx.EVT_SCROLLWIN_PAGEUP, genOnScroll(lTree, rTree, 'PAGEUP'))
rTree.Bind(wx.EVT_SCROLLWIN_PAGEUP, genOnScroll(rTree, lTree, 'PAGEUP'))
lTree.Bind(wx.EVT_SCROLLWIN_PAGEDOWN, genOnScroll(lTree, rTree, 'PAGEDOWN'))
rTree.Bind(wx.EVT_SCROLLWIN_PAGEDOWN, genOnScroll(rTree, lTree, 'PAGEDOWN'))
lTree.Bind(wx.EVT_SCROLLWIN_TOP, genOnScroll(lTree, rTree, 'TOP'))
rTree.Bind(wx.EVT_SCROLLWIN_TOP, genOnScroll(rTree, lTree, 'TOP'))
lTree.Bind(wx.EVT_SCROLLWIN_BOTTOM, genOnScroll(lTree, rTree, 'BOTTOM'))
rTree.Bind(wx.EVT_SCROLLWIN_BOTTOM, genOnScroll(rTree, lTree, 'BOTTOM'))
lTree.Bind(wx.EVT_SCROLLWIN_THUMBTRACK, genOnScroll(lTree, rTree, 'THUMBTRACK'))
rTree.Bind(wx.EVT_SCROLLWIN_THUMBTRACK, genOnScroll(rTree, lTree, 'THUMBTRACK'))
lTree.Bind(wx.EVT_SCROLLWIN_THUMBRELEASE, genOnScroll(lTree, rTree, 'THUMBRELEASE'))
rTree.Bind(wx.EVT_SCROLLWIN_THUMBRELEASE, genOnScroll(rTree, lTree, 'THUMBRELEASE'))
lTree.Bind(wx.EVT_SCROLLBAR, genOnScroll(lTree, rTree, 'SCROLLBAR'))
rTree.Bind(wx.EVT_SCROLLBAR, genOnScroll(rTree, lTree, 'SCROLLBAR'))
lTree.Bind(wx.EVT_SCROLL, genOnScroll(lTree, rTree, 'SCROLL'))
rTree.Bind(wx.EVT_SCROLL, genOnScroll(rTree, lTree, 'SCROLL'))
lTree.Bind(wx.EVT_MOUSEWHEEL, genOnScroll(lTree, rTree, 'MOUSEWHEEL'))
rTree.Bind(wx.EVT_MOUSEWHEEL, genOnScroll(rTree, lTree, 'MOUSEWHEEL'))

# toolbar button handlers
map(frame.Bind, (wx.EVT_MENU, ) * 12,
        # handlers
        (genOnCopy(lTree), genOnCopy(rTree), onDel,
         onCmp, onRefreshAll, onFocus, onBrowse,
         onNew, onSave, onLoad,
         onAbout, onHelp),
        # toolbar buttons
        (frame.btn_cplr, frame.btn_cprl, frame.btn_del,
         frame.btn_cmp, frame.btn_rfsh_all, frame.btn_fcs, frame.btn_brws,
         frame.btn_new, frame.btn_save, frame.btn_load,
         frame.btn_abt, frame.btn_hlp))

view.show()

