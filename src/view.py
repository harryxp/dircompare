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

import wx
import configuration as conf

##############################
# customized wx windows      #
##############################
class MainFrame(wx.Frame):
    # toolbar buttons
    # every entry is a tuple: (textlabel, attribute name, short description)
    # None means a seperator
    # These buttons are installed on the MainFrame instance using the attribute name
    toolbarData = (
            (' N ', 'btn_new', 'New session', 'Create a new compare session'),
            (' S ', 'btn_save', 'Save session', 'Save current compare session'),
            (' L ', 'btn_load', 'Load session', 'Load a compare session from file system'),
            (None, ) * 4,
            (' > ', 'btn_cplr', 'Copy from left to right', 'Copy from left to right'),
            (' < ', 'btn_cprl', 'Copy from right to left', 'Copy from right to left'),
            (None, ) * 4,
            (' D ', 'btn_del', 'Delete', 'Delete current item'),
            (None, ) * 4,
            (' C ', 'btn_cmp', 'Compare files', 'Compare left/right files (need GVim installed)'),
            (None, ) * 4,
            (' R ', 'btn_rfsh_all', 'Refresh all', 'Refresh all'),
#            (' r ', 'btn_rfsh', 'Refresh selected', 'Refresh selected item'),
            (' F ', 'btn_fcs', 'Focus on current folder', 'Start a new session using selected folders as roots'),
            (None, ) * 4,
            (' B ', 'btn_brws', 'Browse in file manager', 'Use file manager to browse this item'),
            (None, ) * 4,
            (' A ', 'btn_abt', 'About', 'About DirCompare'),
            (' ? ', 'btn_hlp', 'Help', 'Help'))
    def __init__(self):
        super(MainFrame, self).__init__(parent=None, id=wx.ID_ANY, title='DirCompare', size=eval(conf.defaultFrameSize))
        self.splitter = Splitter(self)
        self.__createToolBar()
        self.CreateStatusBar()
        self.CenterOnScreen()

    def __createToolBar(self):
        def createToolBarItem(label, attrName, shortHelp, longHelp):
            if not label:
                toolBar.AddSeparator()
                return
            tool = toolBar.AddLabelTool(wx.ID_ANY, label, wx.NullBitmap, shortHelp=shortHelp, longHelp=longHelp)
            setattr(self, attrName, tool)
        toolBar = self.CreateToolBar(wx.TB_TEXT | wx.TB_NOICONS)
        # practical trick! map looks far better than a loop here!
        map(createToolBarItem, *zip(*self.toolbarData))
        toolBar.Realize()

# TODO we can also get rid of Splitter and directly use 2 panels instead.
# One way to do this is to put a box sizer in MainFrame and keep the two panels
# the same size all the time.
class Splitter(wx.SplitterWindow):
    def __init__(self, parent, id=wx.ID_ANY):
        super(Splitter, self).__init__(parent=parent)
        self.__createPanel('l')
        self.__createPanel('r')
        self.SplitVertically(lPanel, rPanel)

    def __createPanel(self, side):
        panel = wx.Panel(self)
#        setattr(self, side + 'Panel', panel)
        textCtrl = wx.TextCtrl(panel, -1, '', size=(175, -1), style=wx.TE_READONLY)
#        setattr(self, side + 'TextCtrl', textCtrl)
        tree = Tree(panel)
#        setattr(self, side + 'Tree', tree)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        sizer.Add(textCtrl, 0, flag=wx.EXPAND)
        sizer.Add(tree, 1, flag=wx.EXPAND)
        # export the panel, textCtrl & tree
        glbs = globals()
        glbs[side + 'Panel'] = panel
        glbs[side + 'Tree'] = tree
        glbs[side + 'TextCtrl'] = textCtrl

# TODO use wx.gizmos.TreeListCtrl to replace this
class Tree(wx.TreeCtrl):
    style = wx.TR_NO_BUTTONS | wx.TR_NO_LINES | \
            wx.TR_FULL_ROW_HIGHLIGHT | \
            wx.TR_MULTIPLE | \
            wx.TR_HIDE_ROOT

    # TODO shall we handle *args and **kwargs?
    def __init__(self, parent):
        super(Tree, self).__init__(parent=parent, style=Tree.style)

class SessionDialog(wx.Dialog):
    """Used to create a compare session or display the content of a session."""
    def __init__(self, mode, session=None):
        # if mode is 'New', create a session
        # if it's 'Save' or 'Load', display a session
        if mode == 'New':
            title = 'New Compare Session'
            textStyle = 0
            values = ('', '', '.svn, .cvs')
        elif mode == 'Save':
            title = 'Confirm Compare Session to Save'
            textStyle = wx.TE_READONLY
            values = (session.leftPath, session.rightPath, '%s, ' * len(session.ignore) % tuple(session.ignore))
        elif mode == 'Load':
            title = 'Confirm Compare Session to Load'
            textStyle = wx.TE_READONLY
            values = (session.leftPath, session.rightPath, '%s, ' * len(session.ignore) % tuple(session.ignore))
        else:
            raise ValueError('argument mode must be one of ("New", "Save", "Load")')
        super(SessionDialog, self).__init__(frame, wx.ID_ANY, title, size=(300, 200))
        # static text
        map(wx.StaticText,
            # parent
            (self, ) * 2,
            # ID
            (wx.ID_ANY, ) * 2,
            # text
            ('Ignore :', 'Full name match. E.g, .svn, .cvs'),
            # positon
            ((27, 100), (90, 120)))
        # text ctrl
        self.leftText, self.rightText, self.ignoreText = \
            map(wx.TextCtrl,
                # parent
                (self, ) * 3,
                # ID
                (wx.ID_ANY, ) * 3,
                # text
                values,
                # positon
                ((90, 20), (90, 60), (90, 100)),
                # size
                ((170, 20), (170, 20), (170, 20)),
                # style
                (textStyle, ) * 3)
        # button
        leftButton, rightButton, okButton, cancelButton = \
            map(wx.Button,
                # parent
                (self, ) * 4,
                # ID
                (wx.ID_ANY, wx.ID_ANY, wx.ID_OK, wx.ID_CANCEL),
                # text
                ('Left   : ', 'Right  :', 'OK', 'Cancel'),
                # positon
                ((25, 18), (25, 58), (60, 140), (160, 140)),
                # size
                ((50, 25), (50, 25), wx.Button.GetDefaultSize(), wx.Button.GetDefaultSize()))
                # style
        if mode == 'New':
            leftButton.Bind(wx.EVT_BUTTON, self.__genOpenDir(self.leftText, 'Choose a directory on left'))
            rightButton.Bind(wx.EVT_BUTTON, self.__genOpenDir(self.rightText, 'Choose a directory on right'))

    def __genOpenDir(self, textCtrl, msg):
        def openDir(event):
            # focus on the path the user might have given
            def findLongestLegalPath(pth):
                """Finds the longest legal path according to the user input in the textctrl, if any.
                   If failed, it returns current user's home directory as fallback."""
                import os.path as path
                if not pth:
                    # pth being empty or None
                    return path.expanduser('~')
                elif path.isdir(pth):
                    return pth
                else:
                    return findLongestLegalPath(path.dirname(pth))
            existingPath = findLongestLegalPath(textCtrl.GetValue())
            d = wx.DirSelector(message=msg, defaultPath=existingPath, style=0, parent=self)
            if d:
                textCtrl.SetValue(d)
        return openDir

class TreeItemStyle(object):
    def __init__(self, color, bgColor, icons):
        self.color = color
        self.bgColor = bgColor
        self.icons = icons

##############################
# start                      #
##############################
app = wx.App(redirect=False)
frame = MainFrame()

lRoot = lTree.AddRoot('lRoot')
rRoot = rTree.AddRoot('rRoot')

# setup tree artworks
imgSz = (16, 16)
imgLst = wx.ImageList(*imgSz)
Tree.fldImg, Tree.fldOpnImg, Tree.fileImg = \
    map(imgLst.Add,
            map(wx.ArtProvider_GetBitmap,
                (wx.ART_FOLDER, wx.ART_FILE_OPEN, wx.ART_NORMAL_FILE),
                (wx.ART_OTHER, ) * 3,
                (imgSz, ) * 3))
#Tree.naImg  = imgLst.Add(wx.ArtProvider_GetBitmap(wx.ART_MISSING_IMAGE, wx.ART_OTHER, imgSz))
#Tree.naImg  = imgLst.Add(wx.EmptyBitmap(*imgSz))
lTree.SetImageList(imgLst)
rTree.SetImageList(imgLst)

# setup wx tree item styles
TreeItemStyle.FILE_SAME, TreeItemStyle.FILE_DIFF, \
TreeItemStyle.FILE_ONESIDEONLY, TreeItemStyle.FILE_ABSENT, \
TreeItemStyle.DIR_SAME, TreeItemStyle.DIR_DIFF, \
TreeItemStyle.DIR_ONESIDEONLY, TreeItemStyle.DIR_ABSENT = \
    map(TreeItemStyle,
        # foregroud text color
        (conf.normalTextColor, conf.diffTextColor,
         conf.oneSideTextColor, conf.oneSideTextColor,
         conf.normalTextColor, conf.diffTextColor,
         conf.oneSideTextColor, conf.oneSideTextColor),
        # backgroud color
        (conf.normalBgColor, conf.diffBgColor,
         conf.oneSideBgColor, conf.oneSideBgColor,
         conf.normalBgColor, conf.diffBgColor,
         conf.oneSideBgColor, conf.oneSideBgColor),
        # icons
        (((Tree.fileImg, wx.TreeItemIcon_Normal), (Tree.fileImg, wx.TreeItemIcon_Selected)),
         ((Tree.fileImg, wx.TreeItemIcon_Normal), (Tree.fileImg, wx.TreeItemIcon_Selected)),
         ((Tree.fileImg, wx.TreeItemIcon_Normal), (Tree.fileImg, wx.TreeItemIcon_Selected)),
         (),
         ((Tree.fldImg, wx.TreeItemIcon_Normal), (Tree.fldOpnImg, wx.TreeItemIcon_Expanded)),
         ((Tree.fldImg, wx.TreeItemIcon_Normal), (Tree.fldOpnImg, wx.TreeItemIcon_Expanded)),
         ((Tree.fldImg, wx.TreeItemIcon_Normal), (Tree.fldOpnImg, wx.TreeItemIcon_Expanded)),
         ()))

def show():
    """Brings up the GUI."""
    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    show()

