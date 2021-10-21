"""
This is Roeland’s CMD color module, which abstracts away either the ANSI color
codes on VT-style terminals, or the win32 console API. The latter is also called
directly for printing text so you can print any Unicode character up to U+FFFF
on the console.
"""

import functools as _functools
import sys as _sys
import warnings as _warnings

# this script requires Python 3

# switch colors on or off
C_COLOR_OFF  = "off"
C_COLOR_ON   = "on"
C_COLOR_AUTO = "auto"
C_COLOR_ANSI = "ansi"
C_COLOR_OPTION_LIST = (C_COLOR_OFF, C_COLOR_ON, C_COLOR_AUTO, C_COLOR_ANSI)

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


def _color_to_str(n):
    """ integer color number to string """
    if n < 16:
        return ("bright " if (n & C_BRIGHT_FLAG) else "") + _ctable[n % 8]
    return str(n)

@_functools.total_ordering
class Color:
    """
    Represent a change in color. This can be:
     - a foreground and/or background color;
     - setting the bright flag;
     - resetting the style.
    
    Color is immutable, all operators return new objects. The color IDs
    0 to 15 follow Windows convention: 1 is blue and 4 is red. 16 to 255
    follows ANSI convention.
    
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
        
    def __init__(self, color=None):
        """ Make empty object or make a copy

        Color(): create a color which resets to the default
        Color(color): copy a color object
        """
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
        if c.fg and c.fg < 16: c.fg = c.fg % 8
        return c
        
    def bright_bg(self):
        """ returns a version with a bright background color """
        return self.with_bg(self.bg or 0, True)
        
    def dark_bg(self):
        """ returns a version with a dark background color """
        return self.with_bg(self.bg or 0, False)
        
    def _val(color, intensity):
        """ Get a valid color value and optionally set the 'intensity'. """
        a = int(color)
        if a < 16:
            if intensity:
                a = a | C_BRIGHT_FLAG
            elif intensity is not None:
                a = a & ~C_BRIGHT_FLAG
        return a        
        
    def _apply_flags(self):
        """ Normalize this Color instance
        
        a flag plus a color below 16 is converted to a high intensity color. """
        if self.fg is not None and self.fg < 16 and self.flag:
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
        # with flag:
        if self.flag == C_BRIGHT_FLAG: return  'Color({}, {}, C_BRIGHT_FLAG)'.format(self.fg, self.bg)
        # regular color, or None
        return 'Color({}, {})'.format(self.fg, self.bg)

    # str(self)
    def __str__(self):
        # reset:
        if not self:
            return '[reset]'
        
        s = ''
        if self.flag:
            s += 'bright'
        if self.fg:
            if s: s += ' '
            s += _color_to_str(self.fg)
        if self.bg:
            if s: s += ', '
            s += _color_to_str(self.bg) + ' background'
        return '[' + s + ']'

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
C_BRIGHT  = Color.make(None, None, C_BRIGHT_FLAG)

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

       - C_COLOR_OFF: switch off color output
       - C_COLOR_ON: always try to output color if possible on this platform
       - C_COLOR_AUTO (default): only output color if the file handle appears to be a console.
       - C_COLOR_ANSI: always output ANSI sequences (on Windows this switches to outputting ANSI)
    """
    global _useColorFlag
    if flag not in C_COLOR_OPTION_LIST:
        raise ValueError("flag not in "+", ".join(C_COLOR_OPTION_LIST))
    if flag == C_COLOR_ANSI:
        _useColorFlag = C_COLOR_ON
        _use_ansi_fallback()
        _need_flush = False        
    else:
        _useColorFlag = flag


def _set_color_raw_ansi(color, f):
    """ Sets current color using ANSI codes

    Used on Windows 10 in ANSI mode, or as a fallback if neither WIN32 or curses are available. """
    if not color: 
        _print_el(f, '\033[0m')
        return
        
    ansi = []

    if color.flag: 
        # only bright for now.
        ansi.append('1')

    if color.fg is not None:
        if color.fg < 16:
            intensity = (color.fg >= C_BRIGHT_FLAG)
            ansiC = ((color.fg & 1) << 2) + (color.fg & 2) + ((color.fg & 4) >> 2)
            ansi.append('3' + str(ansiC))
            if intensity: ansi.append('1')
        else:
            ansi.append('38;5;' + str(color.fg))

    if color.bg is not None:
        if color.bg < 16:
            intensity = (color.bg >= C_BRIGHT_FLAG)
            ansiC = ((color.bg & 1) << 2) + (color.bg & 2) + ((color.bg & 4) >> 2)
            ansi.append(('10' if intensity else '4') + str(ansiC))
        else:
            ansi.append('48;5;' + str(color.bg))
        

    _print_el(f, '\033[' + ';'.join(ansi) + 'm')


def _reduce_16(n):
    if n < 16:
        return n
    
    if n > 231:
        if n < 235:
            return 0
        if n < 242:
            return 8
        if n < 251:
            return 7
        return 15
    
    n -= 16
    red = n // 36
    n -= 36*red
    green = n // 6
    blue = n - 6*green
    
    col = 0
    if (blue >= max(green, red) - 1): col = col | 1
    if (green >= max(blue, red) - 1): col = col | 2
    if (red >= max(blue, green) - 1): col = col | 4
    
    val = max(blue, green, red)
    if col == 7:
        if val == 0:
            return 0
        if val < 3:
            return 8
    
    if (val > 4):   col = col | 8
    
    
    
    return col


def _use_ansi_fallback():
    """ Switch to ANSI printing. (can't undo this) """
    global _colors, _can_use, _print_el, _set_color

    _colors = lambda file : 256
    _can_use = lambda file: True
    _print_el = lambda file, s: print(file=file, end=s)
    _set_color = _set_color_raw_ansi


if _sys.platform == 'win32':

    # use Windows-specific color stuff

    import ctypes as _ctypes
    import ctypes.wintypes as _wintypes
    from os import environ as _environ
    
    # Win32 API constants
    _ENABLE_PROCESSED_OUTPUT = 0x0001
    _ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winprog/winprog/windows_api_reference.asp
    # for information on Windows APIs.
    _STD_OUTPUT_HANDLE= -11
    _STD_ERROR_HANDLE = -12

    # Win32 types
    _WORD = _wintypes.WORD
    _DWORD = _wintypes.DWORD
    _SMALL_RECT = _wintypes.SMALL_RECT
    _COORD = _wintypes._COORD

    class _CONSOLE_SCREEN_BUFFER_INFO(_ctypes.Structure):
      """struct in wincon.h."""
      _fields_ = [
        ("dwSize", _COORD),
        ("dwCursorPosition", _COORD),
        ("wAttributes", _WORD),
        ("srWindow", _SMALL_RECT),
        ("dwMaximumWindowSize", _COORD)]

    # cache function handles
    _getConsoleMode = _ctypes.windll.kernel32.GetConsoleMode
    _setConsoleMode = _ctypes.windll.kernel32.SetConsoleMode
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
            self.use_ansi = False
            self.istty = (self.default is not None)
            if self.istty and _environ.get('CMDCOLOR_ANSI', '1') == '1':
                # enable ANSI sequences
                mode = _DWORD(0)
                ok = _getConsoleMode(self.h, _ctypes.byref(mode))
                if not ok:
                    _warnings.warn("cmdcolor initialization: call to GetConsoleMode failed", stacklevel=4)
                    self.istty = False

                if ok:
                    ok = _setConsoleMode(self.h, mode.value | _ENABLE_PROCESSED_OUTPUT | _ENABLE_VIRTUAL_TERMINAL_PROCESSING)
                    if ok:
                        self.use_ansi = True
            else:
                self.default = C_WHITE + C_BG_BLACK
            self.color   = Color(self.default) # copy

    _std_h = ((_sys.stdout, _STD_OUTPUT_HANDLE),
              (_sys.stderr, _STD_ERROR_HANDLE))
    _con = { f[0] : _Con(f[1]) for f in _std_h }
    
    def _istty(file):
        c = _con.get(file)
        return c is not None and c.istty

    def _colors(file):
        c = _con.get(file)
        return 1 if c is None else (256 if c.use_ansi else 16)

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
        if con.use_ansi:
            _set_color_raw_ansi(color, f)
            return
            
        if not color:
            color = con.default
        else:
            color = con.color + color
        
        con.color = color
        fg, bg = _reduce_16(color.fg), _reduce_16(color.bg)
        attr = fg + bg * 16
        bool = _setConsoleTextAttribute(con.h, attr)
    
    _need_flush = any(c.istty for _, c in _con.items())
    
# Unix and Windows/msys
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

        def _colors(file):
            return min(256, _cols)

        def _set_color(color, f):
            if not color: 
                _print_el(f, _colreset)
                return
                
            if color.flag: 
                # map "bright" to the bold attribute
                _print_el(f, _colbold)
            
            if color.fg is not None:
                fg = color.fg
                if _cols <= 16:
                    fg = _reduce_16(fg)
                
                if fg < 16:
                    ansiC = ((fg & 1) << 2) + (fg & 2) + ((fg & 4) >> 2)
                    if fg >= C_BRIGHT_FLAG:
                        _print_el(f, _colbold)
                else:
                    ansiC = fg
                _print_el(f, _cu.tparm(_afstr, ansiC).decode('ascii'))

            if color.bg is not None:
                bg = color.bg
                if _cols <= 16:
                    bg = _reduce_16(bg)
            
                if bg < 16:
                    ansiC = ((bg & 1) << 2) + (bg & 2) + ((bg & 4) >> 2);
                    if _cols >= 16 and (bg & C_BRIGHT_FLAG):
                        ansiC += C_BRIGHT_FLAG
                else:
                    ansiC = bg
                _print_el(f, _cu.tparm(_abstr, ansiC).decode('ascii'))

    except ImportError:
        # no curses available. Assume the usual ANSI codes will work
        _use_ansi_fallback()
        
    _need_flush = False

        
def canPrintColor(file):
    """ Return True if printc is able to attempt to print colored text. """
    return _can_use(file)
    
        
def numColors(file):
    """ Number of colors we can print on this file.

    this may return 1, 8, 16 or 256 """
    if not _can_use(file):
        return 1
    return _colors(file)
    
        
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
    
    if "--ansi" in _sys.argv:
        enableColorPrinting(C_COLOR_ANSI)
    
    print("This is the ", end="")
    s = "«cmdcolor»"
    cl = [4, 12, 12, 14, 14, 10, 10, 11, 9, 1]
    for ch, c in zip(s, cl): printc(Color.fg(c), ch, end="")
    print(" module. Import it into your favorite script to print\ncolors.")
    
    if not canPrintColor(_sys.stdout):  
        print("Current stdout cannot print colors")
    elif not willPrintColor(_sys.stdout):  
        print("Current stdout will not print colors")
    
    if "--help" in _sys.argv or "--info" in _sys.argv or "-h" in _sys.argv:
        print()
        printc("You can display a color chart by using the", C_BRIGHT, "--chart", C_RESET, "option.")
        printc("In 256 color mode use", C_BRIGHT, "--chart256", C_RESET, "or", C_BRIGHT, "--chart256bg", C_RESET, end=".\n")
        printc("Use", C_BRIGHT, "--force", C_RESET, "to always try to print color.")
        printc()
        printc("Status:")
        printc("   stdout:", str(numColors(_sys.stdout)) + " colors" if willPrintColor(_sys.stdout) else "no colors")
        printc("   stderr:", str(numColors(_sys.stderr)) + " colors" if willPrintColor(_sys.stderr) else "no colors")
    
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

    
    elif "--chart256" in _sys.argv or "--chart256bg" in _sys.argv:
        C = (lambda x : Color.make(0, x)) if "--chart256bg" in _sys.argv else Color.fg
    
        print()
        for i in range(16):
            printc(C(i), "{:03}".format(i), end=' ')
        printc()
        printc()
        
        for a in range(6):
            for b in range(6):
                for c in range(6):
                    i = 16 + c + 6*(b + 6*a)
                    printc(C(i), "{:03}".format(i), end=' ')
                printc()
            printc()
        printc()
        
        for i in range(232, 244):
            printc(C(i), "{:03}".format(i), end=' ')
        printc()
        for i in range(244, 256):
            printc(C(i), "{:03}".format(i), end=' ')
        printc()
