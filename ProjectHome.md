**Update 2009 June 29: I'm currently looking forward to wxPython to get compatible with Python 3.0 to do bugfixes and probably code refactoring (saves much effort due to better string/unicode support in Python itself).  But the last release should be pretty stable per feedback from users.  Please note that `DirCompare.rc` file under the installation path is the configuration file! I'm following the Linux convention here!**

It's more useful than I thought after I invented this.
> - the Author of DirCompare

它比我当初设想的更为有用。
> - 作者

To Windows users: Just use the latest release in zip format.  There are user reports that msvcp71.dll is needed to run this software.  Due to license concerns it's not included in the distribution.  However it should be fairly easy for you to locate it and place it to the WINDOWS directory.

To Unix users: Install Python 2.6 and wxPython 2.8, grab the code and do a
```
python DirCompare.py
```

Or use the #! trick. whatever you want :-)

Comments are highly welcomed!

_DirCompare on Linux. Click for a larger image._

<a href='http://personal.panxingzhi.net/wp-content/uploads/2009/09/dircompare-screenshot.png'><img width='432' alt='' height='264' src='http://personal.panxingzhi.net/wp-content/uploads/2009/09/dircompare-screenshot.png' /></a>

Alternative software: You may want to try <a href='http://meld.sourceforge.net/'>Meld</a>, which is more rich feature-wise.  It's interesting to see that it's also written in Python.  However I feel my little gadget suffice for most my daily needs and is significantly faster.