import wx
#import images
import configuration as conf

class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY, size=conf.frameSize)
        self.splitter = Splitter(self)
        
class Splitter(wx.SplitterWindow):
    def __init__(self, parent, id=wx.ID_ANY):
        wx.SplitterWindow.__init__(self, parent)
        global lTree
        lTree = Tree(self)
        global rTree
        rTree = Tree(self)
        self.SplitVertically(lTree, rTree)

class Tree(wx.TreeCtrl):
    # THINK shall we handle *args and **kwargs?
    def __init__(self, parent):
        wx.TreeCtrl.__init__(self, parent, style=
                                wx.TR_NO_BUTTONS |
                                wx.TR_NO_LINES |
                                wx.TR_EXTENDED |
                                wx.TR_FULL_ROW_HIGHLIGHT |
                                wx.TR_HIDE_ROOT)
                                #^(wx.VSCROLL | wx.HSCROLL
