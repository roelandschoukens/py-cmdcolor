"""
This is Roeland’s CMD color module, which abstracts away either the ANSI color
codes on VT-style terminals, or the win32 console API. The latter is also called
directly for printing text so you can print any Unicode character up to U+FFFF
on the console.
"""

import functools as _functools
import sys as _sys

# this script requires Python 3

# switch colors on or off
C_COLOR_OFF  = 0
C_COLOR_ON   = 1
C_COLOR_AUTO = 2

_useColorFlag = C_COLOR_AUTO

_ctable = (
    'black'  ,
    'blue'   ,
    'green'  ,
    'cyan'   ,
    'red'    ,
    'magenta',
    'yellow' ,
    'white'   )
    
C_BRIGHT_FLAG = 8
C_RESET = None

def colorname(i):
    """ Returns the name of a color
    
    i shall be a number from 0 to 7 """
    return _ctable[i]


@_functools.total_ordering
class Color:
    """
    Represent a change in color. This can be:
     - a foreground and/or background color;
     - setting the bright flag;
     - resetting the style.
    
    Color is immutable, all operators return new objects.
    
    The add operator is supported, where a + b is equivalent to
    'apply a, then b'
    
    Currently, combining a color with C_BRIGHT_FLAG will result in
    a bright color.
    """
    def make(fg, bg, flag=0):
        """ create color with given foreground and background colors (given as integers) """
        c = Color()
        c.fg = fg
        c.bg = bg
        c.flag = flag
        return c

    def fg(color, intensity=None):
        """ create color with given foreground color (given as integer) """
        return Color.make(Color._val(color, intensity), None)

    def bg(color, intensity=None):
        """ create color with given background color (given as integer) """
        return Color.make(None, Color._val(color, intensity))

    def flag(s):
        """ return the C_BRIGHT_FLAG flag, if set. """
        c = Color()
        c.flag = s
        return c
        
    # forms: Color() -> reset
    # forms: Color(color) -> copy another color object
    def __init__(self, color=None):
        # foreground color, if set
        self.fg = None
        # background color, if set
        self.bg = None
        # flags: now used to create a color object which just switches on
        # the intensity bit (C_BRIGHT)
        self.flag = 0
    
        if color is None:
            return
        else:
            # copy fields
            self.fg = color.fg
            self.bg = color.bg
            self.flag = color.flag
    
    def with_fg(self, color, intensity=None):
        """ return a color with the same background, but a different foreground """
        return Color.make(Color._val(color, intensity), self.bg)
            
    def with_bg(self, color, intensity=None):
        """ return a color with the same foreground, but a different background """
        return Color.make(self.fg, Color._val(color, intensity), self.flag)
    
    def bright(self):
        """
        Returns a version with a bright foreground color
        
        As a special case, C_RESET.bright() returns C_BRIGHT. """
        c = Color(self)
        c.flag = C_BRIGHT_FLAG
        c._apply_flags()
        return c
        
    def dark(self):
        """ returns a version with a dark foreground color """
        c = Color(self)
        c.flag = 0
        if c.fg: c.fg = c.fg % 8
        return c
        
    def bright_bg(self):
        """ returns a version with a bright background color """
        return self.with_bg(self.bg or 0, True)
        
    def dark_bg(self):
        """ returns a version with a dark background color """
        return self.with_bg(self.bg or 0, False)
        
    def _val(color, intensity):
        """ Get a valid color value and optionally set the 'intensity'. """
        a = int(color) % 16
        if intensity:
            a = a | C_BRIGHT_FLAG
        elif intensity is not None:
            a = a % 8
        return a        
        
    def _apply_flags(self):
        """ Normalize this Color instance
        
        a flag plus a color is converted to a high intensity color. """
        if self.fg is not None and self.flag:
            self.fg |= self.flag
            self.flag = 0
        
    # a + b: apply b after a
    def __add__(a, b):
        c = Color(a)
        if b is None: return c
        try:
            if b.fg is not None: c.fg = int(b.fg)
            if b.bg is not None: c.bg = int(b.bg)
            c.flag |= b.flag
            c._apply_flags()
            return c
        except AttributeError:
            raise ValueError("Can't add Color to "+b.__class__.__name__)

    # a + b: apply b after a
    def __radd__(b, a):
        c = Color(b)
        if a is None: return c
        try:
            if b.fg is None: c.fg = int(a.fg)
            if b.bg is None: c.bg = int(a.bg)
            c.flag |= a.flag
            c._apply_flags()
            return c
        except AttributeError:
            raise ValueError("Can't add "+ a.__class__.__name__ + " to Color")
        
    # bool(self)
    def __bool__(self):
        return (self.fg is not None or self.bg is not None or self.flag != 0)

    # repr(self)
    def __repr__(self):
        # bright text: (implies no explicit foreground color)
        if self.flag == C_BRIGHT_FLAG: return  'Color(None, {}, bright)'.format(self.bg)
        # regular color, or None
        return 'Color({}, {})'.format(self.fg, self.bg)

    # str(self)
    def __str__(self):
        # reset:
        if not self:
            return "Reset"
        
        s = ""
        if self.fg:
            s += ("bright " if (self.fg & C_BRIGHT_FLAG) else "") + _ctable[self.fg % 8]
        elif self.flag:
            s += "bright"
        if self.bg:
            if len(s) > 0: s += ", "
            s += ("bright " if (self.bg & C_BRIGHT_FLAG) else "") + _ctable[self.bg % 8] + " background"
        return s

    # hash(self)
    def __hash__(self):
        return self.fg + self.bg * 16 + self.flag * 256

    # a == b
    def __eq__(a, b):
        return (self.fg   == self.fg   and
                self.bg   == self.bg   and
                self.flag == self.flag )

    # a < b
    def __lt__(a, b):
        return a.__hash__() < b.__hash__()


# color numbers
C_RESET   = Color()

C_BLACK   = Color.fg(0)
C_BLUE    = Color.fg(1)
C_GREEN   = Color.fg(2)
C_CYAN    = Color.fg(3)
C_RED     = Color.fg(4)
C_MAGENTA = Color.fg(5)
C_YELLOW  = Color.fg(6)
C_WHITE   = Color.fg(7)

""" special value which turns on "bright" (also called "bold") """
C_BRIGHT  = Color.flag(C_BRIGHT_FLAG)

C_BG_BLACK   = Color.bg(0)
C_BG_BLUE    = Color.bg(1)
C_BG_GREEN   = Color.bg(2)
C_BG_CYAN    = Color.bg(3)
C_BG_RED     = Color.bg(4)
C_BG_MAGENTA = Color.bg(5)
C_BG_YELLOW  = Color.bg(6)
C_BG_WHITE   = Color.bg(7)

        
def enableColorPrinting(flag):
    """Enables or disables color output.
    
    flag may be:
        C_COLOR_OFF: Unconditionally switch off color output
        C_COLOR_ON: Always try to output color if possible on this platform
        C_COLOR_AUTO (default): only output color if the file handle appears to be a console.
    """
    global _useColorFlag
    if flag not in [C_COLOR_OFF, C_COLOR_ON, C_COLOR_AUTO]:
        raise ArgumentError("flag should be C_COLOR_OFF, C_COLOR_ON or C_COLOR_AUTO")
    _useColorFlag = flag


if _sys.platform == 'win32':

    # use Windows-specific color stuff

    import ctypes as _ctypes
    
    # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winprog/winprog/windows_api_reference.asp
    # for information on Windows APIs.
    _STD_OUTPUT_HANDLE= -11
    _STD_ERROR_HANDLE = -12

    _SHORT = _ctypes.c_short
    _WORD = _ctypes.c_ushort

    class _COORD(_ctypes.Structure):
      """struct in wincon.h."""
      _fields_ = [
        ("X", _SHORT),
        ("Y", _SHORT)]

    class _SMALL_RECT(_ctypes.Structure):
      """struct in wincon.h."""
      _fields_ = [
        ("Left", _SHORT),
        ("Top", _SHORT),
        ("Right", _SHORT),
        ("Bottom", _SHORT)]

    class _CONSOLE_SCREEN_BUFFER_INFO(_ctypes.Structure):
      """struct in wincon.h."""
      _fields_ = [
        ("dwSize", _COORD),
        ("dwCursorPosition", _COORD),
        ("wAttributes", _WORD),
        ("srWindow", _SMALL_RECT),
        ("dwMaximumWindowSize", _COORD)]

    # cache function handles
    _writeConsole = _ctypes.windll.kernel32.WriteConsoleW
    _getConsoleScreenBufferInfo = _ctypes.windll.kernel32.GetConsoleScreenBufferInfo
    _setConsoleTextAttribute = _ctypes.windll.kernel32.SetConsoleTextAttribute
    
    def _get_color(h):
        csbi = _CONSOLE_SCREEN_BUFFER_INFO()
        success = _getConsoleScreenBufferInfo(h, _ctypes.byref(csbi))
        if not success: return None
        return Color.make(csbi.wAttributes & 15, (csbi.wAttributes >> 4) & 15)

    # get our data for any handle which is a console
    class _Con:
        def __init__(self, std_h):
            self.h = _ctypes.windll.kernel32.GetStdHandle(std_h)
            self.default = _get_color(self.h)
            self.istty = (self.default is not None)
            if not self.istty:
                self.default = C_WHITE + C_BG_BLACK
            self.color   = Color(self.default) # copy

    _std_h = ((_sys.stdout, _STD_OUTPUT_HANDLE),
              (_sys.stderr, _STD_ERROR_HANDLE))
    _con = { f[0] : _Con(f[1]) for f in _std_h }
    
    def _istty(file):
        c = _con.get(file)
        return c is not None and c.istty

    def _can_use(file):
        # if the Console API is not available, our custom printing doesn't work at all
        return _istty(file)

    # using WriteConsoleW also solves this stupid UnicodeEncodeError on printing fancy characters:
    def _print_el(file, s):
        n = _ctypes.c_int(0)
        utf16 = s.encode('utf-16-le') # we need to count 2 'code' units for characters beyond U+FFFF
        _writeConsole(_con[file].h, s, len(utf16) // 2, _ctypes.byref(n), None)
        
        
    def _set_color(color, f):
        con = _con[f]
        if not color:
            color = con.default
        else:
            color = con.color + color
        
        con.color = color
        attr = color.fg + color.bg * 16
        bool = _setConsoleTextAttribute(con.h, attr)
    
    _need_flush = any(c.istty for _, c in _con.items())
    
else:

    def _istty(file):
        return file.isatty()

    def _print_el(file, s):
        print(file=file, end=s)

    try:
        import curses as _cu
        
        _cu.setupterm()
        _cols = _cu.tigetnum("colors")
        _afstr = _cu.tigetstr("setaf")
        _abstr = _cu.tigetstr("setab")
        _colbold = _cu.tigetstr("bold").decode('ascii')
        _colreset =  _cu.tigetstr("sgr0").decode('ascii')


        def _can_use(file):
            return _cols and _cols >= 8


        def _set_color(color, f):
            if not color: 
                _print_el(f, _colreset)
                return
                
            if color.flag: 
                # only bright for now.
                _print_el(f, _colbold)
            
            if color.fg is not None:
                fg = color.fg
                ansiC = ((fg & 1) << 2) + (fg & 2) + ((fg & 4) >> 2)
                if fg >= C_BRIGHT_FLAG:
                    if _cols < 16:
                        _print_el(f, _colbold)
                    else:
                        ansiC += C_BRIGHT_FLAG
                
                _print_el(f, _cu.tparm(_afstr, ansiC).decode('ascii'))
                

            if color.bg is not None:
                ansiC = ((color.bg & 1) << 2) + (color.bg & 2) + ((color.bg & 4) >> 2);
                if _cols >= 16 and (color.bg & C_BRIGHT_FLAG):
                    ansiC += C_BRIGHT_FLAG
                _print_el(f, _cu.tparm(_abstr, ansiC).decode('ascii'))


    except ImportError:
        
        def _can_use(file):
            return True

        
        #use ANSI escape codes
        def _set_color(color, f):
            if not color: 
                _print_el(f, '\033[0m')
                return
                
            ansi = []

            if color.flag: 
                # only bright for now.
                ansi.append('1')

            if color.fg is not None:
                intensity = (color.fg >= C_BRIGHT_FLAG)
                ansiC = ((color.fg & 1) << 2) + (color.fg & 2) + ((color.fg & 4) >> 2)
                
                ansi.append('3' + str(ansiC))
                if intensity: ansi.append('1')

            if color.bg is not None:
                intensity = (color.bg >= C_BRIGHT_FLAG)
                ansiC = ((color.bg & 1) << 2) + (color.bg & 2) + ((color.bg & 4) >> 2)
                
                ansi.append(('10' if intensity else '4') + str(ansiC))

            _print_el(f, '\033[' + ';'.join(ansi) + 'm')
        
    _need_flush = False

        
def canPrintColor(file):
    """ Return True if printc is able to attempt to print colored text. """
    return _can_use(file)
    
        
def willPrintColor(file):
    """ Return True if printc will attempt to print colored text to this file.
    
    This depends on the setting supplied with enableColorPrinting() """
    global _useColorFlag
    if not _can_use(file):
        return False
    if _useColorFlag == C_COLOR_OFF: return False
    if _useColorFlag == C_COLOR_ON: return True
    if file is None: return False
    # COLOR_AUTO
    return _istty(file)
    

def printc(*args, **kwargs):
    """ Analog to the print() function, but accepts Color objects to change colors
    
    Any Color objects will cause the output color to change for subsequent text.
    Other objects will be printed as usual.
    
    end is always printed without color, this avoids common problems if the trailing
    return is printed with color attributes.
    
    If color is off, the call is equivalent to
        
        print(*[s for s in args if type(s) is not Color], **kwargs)
    """
    file = kwargs.get('file', _sys.stdout)
    use = willPrintColor(file)
    if not use:
        # strip all color objects and print
        ss = [s for s in args if type(s) is not Color]
        print(*ss, **kwargs)
        return

    sep0 = str(kwargs.get('sep', ' '))
    end = str(kwargs.get('end', '\n'))
    
    try:
        if _need_flush: file.flush()


        sep = None
        for s in args:

            if type(s) is Color:
                _set_color(s, file)
            else:
                # handle separators. Colors do not trigger
                # separators
                if sep is not None:
                    _print_el(file, sep)
                    sep = None
                    
                _print_el(file, str(s))
                
                sep = sep0

    finally:
        _set_color(C_RESET, file)
    
    _print_el(file, end)

    
if __name__ == "__main__":

    if "--force" in _sys.argv:
        enableColorPrinting(C_COLOR_ON)
    
    print("This is the ", end="")
    s = "«cmdcolor»"
    c = [4, 12, 12, 14, 14, 10, 10, 11, 9, 1]
    for z in zip(s, c): printc(Color.fg(z[1]), z[0], end="")
    print(" module. Import it into your favorite script to print\ncolors.")
    
    if not willPrintColor(_sys.stdout):  
        print("Current stdout cannot print colors")
    elif not willPrintColor(_sys.stdout):  
        print("Current stdout will not print colors")
    
    if "--help" in _sys.argv or "-h" in _sys.argv:
        print()
        printc("You can display a color chart by using the", C_BRIGHT, "--chart", C_RESET, "option.")
        printc("Use ", C_BRIGHT, "--force", C_RESET, " to always try to print color.")
    
    elif "--chart" in _sys.argv:
        print()
        printc("standard text, ", C_BRIGHT, "bold text", C_RESET, ".", sep="")
        print()
        print(" {:<26}  {:<26}".format("foreground colors", "background colors"))
        for i in range(8):
            printc("{:2}:"  .format(i),               Color.fg(i)             , "{:<7}".format(colorname(i)), C_RESET,
                   "  {:2}:".format(i+C_BRIGHT_FLAG), Color.fg(i, True)       , "{:<7}".format(colorname(i)), C_RESET,
                   "  {:2}:".format(i)              , Color.bg(i)             , "{:<7}".format(colorname(i)), C_RESET,
                   "  {:2}:".format(i+C_BRIGHT_FLAG), C_BLACK.with_bg(i, True), "{:<7}".format(colorname(i)), C_RESET)
