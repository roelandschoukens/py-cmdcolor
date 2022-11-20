"""
This is Roeland’s CMD color module, which abstracts away either the ANSI color
codes on VT-style terminals, or the win32 console API. The latter is also called
directly for printing text so you can print any Unicode character up to U+FFFF
on the console.

The + operator allows creating colors 8 to 15 by adding the bright flag to colors 0 to 7.
This is because originally we represented RGBI bits on Windows (which inherited
these from CGA all the way back. This is also how we ended up with blue being color 4).
Many scripts using ANSI sequences do this as well, they print `'\033[1;31m'`
for bright blue. In particular, they may assume `'\033[1;30m'` yields visible dark gray.
They may also ignore the bold attribute on colors 8 to 15.

Terminals therefore often use bright colors if you request bold for colors 0 to 7. Hence
we still create bright blue with `C_BLUE + C_BRIGHT`, and using `printc(C_BLUE, C_BRIGHT, ...)`
is discouraged.

For output using curses, we assume that colors 8 to 15 are output as proper colors 8 to
15 instead of "bold" colors 0 to 7. If this is not the case, C_RESET_BRIGHT and C_RESET_FG
will behave in a funny way. This happens hopefully only when only 8 colors are supported.

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

# flag values. Internal. Use the C_** Color objects in your code instead.
C_BRIGHT_FLAG = 8
_C_RESET_BRIGHT_FLAG = 0x100
_C_RESET_FG_FLAG = 0x400
_C_RESET_BG_FLAG = 0x800
_C_RESET_ALL_FLAG = 0x1000 # separate, since ANSI has a reset all function

_all_flags = C_BRIGHT_FLAG, _C_RESET_BRIGHT_FLAG, _C_RESET_FG_FLAG, _C_RESET_BG_FLAG, _C_RESET_ALL_FLAG
_all_flags_str = 'C_BRIGHT_FLAG', '_C_RESET_BRIGHT_FLAG', '_C_RESET_FG_FLAG', '_C_RESET_BG_FLAG', '_C_RESET_ALL_FLAG'

def colorname(i):
    """ Returns the name of a color

    i shall be a number from 0 to 7 """
    return _ctable[i]


def _color_to_str(n):
    """ integer color number to string """
    if n < 16:
        return ("bright " if (n & 8) else "") + _ctable[n % 8]
    return str(n)

@_functools.total_ordering
class Color:
    """
    Represent a change in color. This can be:
     - a foreground and/or background color;
     - setting the bold flag;
     - resetting the style.

    Color is immutable, all operators return new objects. The color IDs
    0 to 15 follow Windows convention: 1 is blue and 4 is red. 16 to 255
    follows ANSI convention.

    The operator a + b is mapped to ‘apply color a, then color b’. This
    operation is neither associative, nor commutative. Green after
    blue is obviously different from blue after green.

    C_BRIGHT also behaves in a peculiar way for colors 0 to 16, due to originally
    supporting only the 8 standard ANSI colors, and only 16 non-bold colors on Windows:

        - `C_BLUE` is color 1
        - `C_BLUE + C_BRIGHT` is color 9
        - `C_BLUE + C_BRIGHT + C_BRIGHT` is color 9 with the bold attribute set
        - `C_BLUE + (C_BRIGHT + C_BRIGHT)` is color 9 without the bold attribute set because a Color only has one bright flag.

    Adding C_RESET_BRIGHT to color 9 with bold will remove the bold attribute. Adding C_RESET_BRIGHT again will bring it back to color 1.

    `printc(C_BLUE, C_BRIGHT, "text")` in ANSI or curses mode still represents 2 separate color operations: set the color to 1, and then set the bold attribute.
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

    def fg6(r, g, b):
        """ create color with given 6-level RGB values (0−5) """
        r, g, b = int(r), int(g), int(b)
        if (max(r, g, b) > 5 or min(r, g, b) < 0):
            raise ValueError("RGB value out of range")
        color = 16 + b + 6*(g + 6*r)
        return Color.make(color, None)

    def bg6(r, g, b):
        """ create color with given 6-level RGB values (0−5) as background color """
        r, g, b = int(r), int(g), int(b)
        if (max(r, g, b) > 5 or min(r, g, b) < 0):
            raise ValueError("RGB value out of range")
        color = 16 + b + 6*(g + 6*r)
        return Color.make(None, color)

    def fg24(r, g, b, intensity=None):
        """ create color as 24-bit RGB (0−255) """
        r, g, b = int(r), int(g), int(b)
        if (max(r, g, b) > 255 or min(r, g, b) < 0):
            raise ValueError("RGB value out of range")
        color = 0xff000000 + b + 256*(g + 256*r)
        return Color.make(color, None)

    def bg24(r, g, b, intensity=None):
        """ create color with 24-bit RGB (0−255) as background color """
        r, g, b = int(r), int(g), int(b)
        if (max(r, g, b) > 255 or min(r, g, b) < 0):
            raise ValueError("RGB value out of range")
        color = 0xff000000 + b + 256*(g + 256*r)
        return Color.make(None, color)

    def __init__(self, color=None):
        """ Make empty object or make a copy

        Color(): create a color object which does not change the printed color
        Color(color): copy a color object

        For constructing a color using an int, see fg() and bg() and their variants.
        """
        # foreground color, if set
        # values 0 to 256 refer to some 256 color palette
        # values 0xff000000 and above are 32-bit ARGB values (with A set to
        # 255 to distinguish it from the 256-color palette).
        self.fg = None
        # background color, if set
        # values 0 to 256 refer to some 256 color palette
        # values 0xff000000 and above are 32-bit ARGB values (with A set to
        # 255 to distinguish it from the 256-color palette).
        self.bg = None
        # flags: now used to create a color object which just switches on
        # the intensity bit (C_BRIGHT, or 'bold' on ANSI)
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
        Returns a version with a bright foreground color (for colors 0 to 7), or with bold text.

        As a special case, C_RESET.bright() returns C_BRIGHT. """
        c = Color(self)
        c._apply_flags(C_BRIGHT_FLAG)
        return c

    def dark(self):
        """ returns a version with a dark foreground color for colors 8 to 15. """
        c = Color(self)
        c.flag = 0
        if c.fg and c.fg < 16: c.fg = c.fg % 8
        return c

    def bright_bg(self):
        """ returns a version with a bright background color for colors 0 to 7 """
        return self.with_bg(self.bg or 0, True)

    def dark_bg(self):
        """ returns a version with a dark background color for colors 8 to 15"""
        return self.with_bg(self.bg or 0, False)

    def _val(color, intensity):
        """ Get a valid color value and optionally set the 'intensity'. """
        a = int(color)
        if a < 16:
            if intensity:
                a = a | 8
            elif intensity is not None:
                a = a & 7
        return a

    def _apply_flags(self, new_flags):
        """ Apply new flags to this Color instance

        a flag plus a color below 16 is converted to a high intensity color. """

        # reset color flags: eat foreground or background
        if new_flags & _C_RESET_FG_FLAG:
            self.fg = None
        if new_flags & _C_RESET_BG_FLAG:
            self.bg = None

        # mutually exclusive brightness flags, and fold into colors 0 to 15
        if new_flags & C_BRIGHT_FLAG:
            self.flag &= ~_C_RESET_BRIGHT_FLAG

            # emboldening colors 0 to 7 creates colors 8 to 15 instead of bold
            if self.fg is not None and self.fg < 8:
                new_flags &= ~C_BRIGHT_FLAG
                self.fg += 8

        if new_flags & _C_RESET_BRIGHT_FLAG:
            if self.flag & C_BRIGHT_FLAG:
                self.flag &= ~C_BRIGHT_FLAG
            elif 8 <= self.fg < 16:
                new_flags &= ~_C_RESET_BRIGHT_FLAG
                self.fg -= 8

        self.flag |= new_flags

    def _add(self, b):
        c = Color(self)
        if b.flag & _C_RESET_ALL_FLAG:
            return Color.make(None, None, _C_RESET_ALL_FLAG)

        c.flag &= ~_C_RESET_ALL_FLAG
        if b.fg is not None:
            c.fg = int(b.fg)
            c.flag &= ~_C_RESET_FG_FLAG
        if b.bg is not None:
            c.flag &= ~_C_RESET_BG_FLAG
            c.bg = int(b.bg)
        c._apply_flags(b.flag)
        return c

    # a + b: apply b after a
    def __add__(a, b):
        if not b: Color(a)
        try:
            return a._add(b)
        except AttributeError:
            raise ValueError("Can't add Color to "+b.__class__.__name__)

    # a + b: apply b after a
    def __radd__(b, a):
        if not a: return Color(b)
        try:
            return a._add(b)
        except AttributeError:
            raise ValueError("Can't add Color to "+a.__class__.__name__)

    # bool(self)
    def __bool__(self):
        return (self.fg is not None or self.bg is not None or self.flag != 0)

    # repr(self)
    def __repr__(self):
        # with flag:
        if self.flag:
            s = [y for x, y in zip(_all_flags, _all_flags_str) if self.flag & x]
            return  'Color({}, {}, {})'.format(self.fg, self.bg, ' | '.join(s))
        # regular color, or None
        return 'Color({}, {})'.format(self.fg, self.bg)

    # str(self)
    def __str__(self):
        # reset:
        if not self:
            return []
        if self.flag & _C_RESET_ALL_FLAG:
            return '[reset]'

        s = []
        if self.flag & C_BRIGHT_FLAG:
            s.append('bold')
        if self.flag & _C_RESET_BRIGHT_FLAG:
            s.append('non-bold')
        if self.flag & _C_RESET_FG_FLAG:
            s.append('non-colored')
        if self.fg:
            s.append(_color_to_str(self.fg))
        s = ' '.join(s)
        if self.bg:
            if s: s += ', '
            s += _color_to_str(self.bg) + ' background'
        if self.flag & _C_RESET_BG_FLAG:
            if s: s += ', '
            s.append('no background')
        return '[' + s + ']'

    # hash(self)
    def __hash__(self):
        return hash(self.fg, self.bg, self.flag)

    # a == b
    def __eq__(a, b):
        return (self.fg   == self.fg   and
                self.bg   == self.bg   and
                self.flag == self.flag )

    # a < b
    def __lt__(a, b):
        return a.__hash__() < b.__hash__()


# color numbers

#: Color object that represents no action to change color
C_NO_COLOR = Color()
#: reset all attributes
C_RESET   = Color.make(None, None, _C_RESET_ALL_FLAG)

# basic 8 foreground colors
# bright_bg() can be used for high-intensity background colors.
C_BLACK   = Color.fg(0)
C_BLUE    = Color.fg(1)
C_GREEN   = Color.fg(2)
C_CYAN    = Color.fg(3)
C_RED     = Color.fg(4)
C_MAGENTA = Color.fg(5)
C_YELLOW  = Color.fg(6)
C_WHITE   = Color.fg(7)

#: Enable high intensity bit, and bold
C_BRIGHT  = Color.make(None, None, C_BRIGHT_FLAG)
#: Disable bold, and high intensity bit
C_RESET_BRIGHT  = Color.make(None, None, _C_RESET_BRIGHT_FLAG)
#: Reset foreground color to default
C_RESET_FG  = Color.make(None, None, _C_RESET_FG_FLAG)
#: Reset background color to default
C_RESET_BG  = Color.make(None, None, _C_RESET_BG_FLAG)

# basic 8 background colors
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

    These values are stored in the tuple `C_COLOR_OPTION_LIST` so you can easily present them as
    choises for eg. argparse options.
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
    if color.flag & _C_RESET_ALL_FLAG:
        _print_el(f, '\033[0m')
        return

    ansi = []

    if color.flag & C_BRIGHT_FLAG:
        ansi.append('1')
    elif color.flag & _C_RESET_BRIGHT_FLAG:
        ansi.append('22')

    if color.flag & _C_RESET_FG_FLAG:
        ansi.append('39')
    elif color.fg is not None:
        if color.fg < 16:
            intensity = (color.fg >= 8)
            ansiC = ((color.fg & 1) << 2) + (color.fg & 2) + ((color.fg & 4) >> 2)
            ansi.append(('9' if intensity else '3') + str(ansiC))
        elif color.fg < 256:
            ansi.append('38;5')
            ansi.append(str(color.fg))
        else:
            ansi.append('38;2')
            ansi.append(str((color.fg >> 16) & 0xff))
            ansi.append(str((color.fg >>  8) & 0xff))
            ansi.append(str((color.fg      ) & 0xff))

    if color.flag & _C_RESET_BG_FLAG:
        ansi.append('49')
    elif color.bg is not None:
        if color.bg < 16:
            intensity = (color.bg >= 8)
            ansiC = ((color.bg & 1) << 2) + (color.bg & 2) + ((color.bg & 4) >> 2)
            ansi.append(('10' if intensity else '4') + str(ansiC))
        elif color.bg < 256:
            ansi.append('48;5')
            ansi.append(str(color.bg))
        else:
            ansi.append('48;2')
            ansi.append(str((color.bg >> 16) & 0xff))
            ansi.append(str((color.bg >>  8) & 0xff))
            ansi.append(str((color.bg      ) & 0xff))

    _print_el(f, '\033[' + ';'.join(ansi) + 'm')


def _reduce_256(n):
    """ return a color value from our 256-color palette."""
    if n < 256:
        return n

    r = ((n >> 16) & 0xff)
    g = ((n >> 8) & 0xff)
    b = (n & 0xff)

    a1 = min(r, g, b)
    a2 = max(r, g, b)
    if abs(a1 - a2) < 20:
        return min(255, 232 + (a1 + a2) // 16)

    r = (r + 20) // 51
    g = (g + 20) // 51
    b = (b + 20) // 51

    return 16 + b + 6*(g + 6*r)

def _reduce_16(n):
    """ return a color value between 0 and 15 that approximates the given value."""
    if n < 16:
        return n

    if n > 231 and n < 256:
        if n < 235:
            return 0
        if n < 242:
            return 8
        if n < 251:
            return 7
        return 15

    if n > 256:
        red   = ((n & 0xff) + 20) // 51
        green = (((n >> 8) & 0xff) + 20) // 51
        blue  = (((n >> 16) & 0xff) + 20) // 51
    else:
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
    global _colorMode, _colors, _can_use, _print_el, _set_color

    _colorMode = lambda file : "ANSI"
    _colors = lambda file : 0x1000000
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
            global _colorMode
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
        return 1 if c is None else (0x1000000 if c.use_ansi else 16)

    def _colorMode(file):
        c = _con.get(file)
        return "None" if c is None else ("ANSI" if c.use_ansi else "win32")

    def _can_use(file):
        # if the Console API is not available, our custom printing doesn't work at all
        return _istty(file)

    # using WriteConsoleW also solves this stupid UnicodeEncodeError on printing fancy characters. It
    # is however slower than print().
    def _print_el(file, s):
        con = _con[file]
        if con.use_ansi:
            print(end=s)
        else:
            n = _ctypes.c_int(0)
            utf16 = s.encode('utf-16-le') # we need to count 2 'code' units for characters beyond U+FFFF
            _writeConsole(con.h, s, len(utf16) // 2, _ctypes.byref(n), None)


    def _set_color(color, f):
        con = _con[f]
        if con.use_ansi:
            _set_color_raw_ansi(color, f)
            return

        if color.flag & _C_RESET_ALL_FLAG:
            color = con.default
        else:
            color = con.color + color
            # handle reset color flags
            if color.fg is None: color.fg = con.default.fg
            if color.bg is None: color.bg = con.default.bg
            color.flag &= ~_C_RESET_FG_FLAG
            color.flag &= ~_C_RESET_BG_FLAG

        con.color = color
        fg, bg = _reduce_16(color.fg), _reduce_16(color.bg)
        attr = fg + bg * 16
        bool = _setConsoleTextAttribute(con.h, attr)

    _need_flush = any(c.istty and not c.use_ansi for _, c in _con.items())

# Unix and Windows/msys
else:

    def _istty(file):
        return file.isatty()

    def _print_el(file, s):
        print(file=file, end=s)

    try:
        import curses as _cu
        from os import environ as _environ
        _cu.setupterm()
        _cols = _cu.tigetnum("colors")
        use_curses = _cols <= 16 or _environ.get('CMDCOLOR_CURSES', '0') == '1'

    except ImportError:
        use_curses = False

    if use_curses:
        _afstr = _cu.tigetstr("setaf")
        _abstr = _cu.tigetstr("setab")
        _colbold = _cu.tigetstr("bold").decode('ascii')
        _colreset =  _cu.tigetstr("sgr0").decode('ascii')

        def _can_use(file):
            return _cols and _cols >= 8

        def _colors(file):
            return _cols

        def _colorMode(file):
            return "Curses" if _cols >= 8 else "None"

        def _set_color(color, f):
            if color.flag & _C_RESET_ALL_FLAG:
                _print_el(f, _colreset)
                return

            if color.flag & C_BRIGHT_FLAG:
                _print_el(f, _colbold)
            elif color.flag & _C_RESET_BRIGHT_FLAG:
                _print_el(f, '\033[22m')

            if color.flag & _C_RESET_FG_FLAG:
                _print_el(f, '\033[39m')
            elif color.fg is not None:
                fg = color.fg
                if _cols <= 256:
                    fg = _reduce_256(fg)
                elif _cols <= 16:
                    fg = _reduce_16(fg)

                if fg < 16:
                    ansiC = ((fg & 1) << 2) + (fg & 2) + ((fg & 4) >> 2)
                    if fg >= 8:
                        if _cols >= 16:
                            ansiC += 8
                        else:
                            _print_el(f, _colbold)
                else:
                    ansiC = fg
                _print_el(f, _cu.tparm(_afstr, ansiC).decode('ascii'))

            if color.flag & _C_RESET_BG_FLAG:
                _print_el(f, '\033[49m')
            elif color.bg is not None:
                bg = color.bg
                if _cols <= 256:
                    bg = _reduce_256(bg)
                elif _cols <= 16:
                    bg = _reduce_16(bg)

                if bg < 16:
                    ansiC = ((bg & 1) << 2) + (bg & 2) + ((bg & 4) >> 2);
                    if _cols >= 16 and (bg & 8):
                        ansiC += 8
                else:
                    ansiC = bg
                _print_el(f, _cu.tparm(_abstr, ansiC).decode('ascii'))

    else:
        # Assume the usual ANSI codes will work
        _use_ansi_fallback()

    _need_flush = False


def canPrintColor(file=_sys.stdout):
    """ Return True if printc is able to attempt to print colored text. """
    return _can_use(file)


def numColors(file=_sys.stdout):
    """ Number of colors we can print on this file.

    this may return 1, 8, 16 or 256 """
    if not _can_use(file):
        return 1
    return _colors(file)


def colorMode(file=_sys.stdout):
    """ Color mode used """
    return _colorMode(file)


def willPrintColor(file=_sys.stdout):
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
                if s:
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

    do_info = "--help" in _sys.argv or "--info" in _sys.argv or "-h" in _sys.argv

    def ramp(x):
        x = x % 30
        if x < 5:
            return 5
        elif x < 10:
            return 10 - x
        elif x < 20:
            return 0
        elif x < 25:
            return x - 20
        else:
            return 5

    def rainbow(i):
        if numColors() >= 256:
            r = ramp(i // 2)
            g = ramp(i // 2 - 10)
            b = ramp(i // 2 - 20)
            return Color.fg6(r, g, b)
        return C_RESET

    rowI = 0
    printc(rainbow(0), "╔", end='')
    for i in range(1, 77):
        printc(rainbow(i), "═", end='')
    printc(rainbow(78), "╗")

    rowI += 2
    printc(rainbow(rowI),  "║", C_RESET,"  This is the ", end="")
    s = "«cmdcolor»"
    cl = [4, 12, 12, 14, 14, 10, 10, 11, 9, 1]
    for ch, c in zip(s, cl): printc(Color.fg(c), ch, end="")
    printc(" module. Import it into your favorite script to   ", rainbow(78+rowI), "║")
    rowI += 2
    printc(rainbow(rowI), "║", C_RESET, "  print colors.", " "*58, rainbow(78+rowI), "║")

    if do_info:
        rowI += 2
        printc(rainbow(rowI), "║", C_RESET, "  {:72s}".format("") , rainbow(78+rowI), "║")
        rowI += 2
        printc(rainbow(rowI), "║", C_RESET, "  {:72s}".format("Status:") , rainbow(78+rowI), "║")
        rowI += 2
        s = " - stdout: " + (str(numColors(_sys.stdout)) + " colors ("+ colorMode(_sys.stdout) +")" if willPrintColor(_sys.stdout) else "no colors")
        printc(rainbow(rowI), "║", C_RESET, "  {:72s}".format(s) , rainbow(78+rowI), "║")
        rowI += 2
        s = " - stderr: " + (str(numColors(_sys.stderr)) + " colors ("+ colorMode(_sys.stderr) +")" if willPrintColor(_sys.stderr) else "no colors")
        printc(rainbow(rowI), "║", C_RESET, "  {:72s}".format(s) , rainbow(78+rowI), "║")

    rowI += 2
    printc(rainbow(rowI), "╚", end='')
    for i in range(1, 77):
        printc(rainbow(i+rowI), "═", end='')
    printc(rainbow(78+rowI), "╝")

    if not canPrintColor(_sys.stdout):
        print("Current stdout cannot print colors")
    elif not willPrintColor(_sys.stdout):
        print("Current stdout will not print colors")

    if do_info:
        print()
        printc("You can display a color chart by using the", C_BRIGHT, "--chart", C_RESET, "option.")
        printc("In 256 color mode use", C_BRIGHT, "--chart256", C_RESET, "or", C_BRIGHT, "--chart256bg", C_RESET, end=".\n")
        printc("Use", C_BRIGHT, "--force", C_RESET, "to always try to print color.")
        printc(C_BRIGHT, "--info", C_RESET, "and", C_BRIGHT, "--test", C_RESET, "print extra information.")

    if "--test" in _sys.argv:
        print()
        printc("Gray fg ramp: ", end='')
        for i in range(232, 256):
            printc(Color.fg(i), "██", end='')
        printc()
        printc("Gray bg ramp: ", end='')
        for i in range(232, 256):
            printc(Color.bg(i), "  ", end='')
        printc()
        printc()

        for j in range(0, 6, 2):
            printc("256-color cube: " if j == 2 else "                ", end='')
            for i in range(16, 232, 6):
                printc(Color.bg(i + j), Color.fg(i+j+1), "▄", end='')
            printc()
        printc()

        for i, (rgb_bg, rgb_fg) in enumerate((
            ((255, 0, 60), (255, 128, 0) ),
            ((255, 220, 0), (0, 255, 100)),
            ((0, 150, 255), (80, 0, 255)),
            ((180, 0, 255), (128, 128, 128))
            )):
            printc("True-color ramps: " if i == 1 else "                  ", end='')
            for i in range(0, 256, 9):
                printc(
                    Color.fg24(i * rgb_fg[0] // 255, i * rgb_fg[1] // 255, i * rgb_fg[2] // 255),
                    Color.bg24(i * rgb_bg[0] // 255, i * rgb_bg[1] // 255, i * rgb_bg[2] // 255),
                    "▄", end='')
            for i in range(0, 256, 9):
                t = 255 - i
                printc(
                    Color.fg24(i + t * rgb_fg[0] // 255, i + t * rgb_fg[1] // 255, i + t * rgb_fg[2] // 255),
                    Color.bg24(i + t * rgb_bg[0] // 255, i + t * rgb_bg[1] // 255, i + t * rgb_bg[2] // 255),
                    "▄", end='')
            printc()
        printc()

        printc("Color 0 to 15 behavior:")
        printc('  - Black:', C_BLACK, C_BRIGHT, "bold text")
        printc('  - Green:', C_GREEN, "regular text")
        printc('  - Green:', C_GREEN, C_BRIGHT, "bold text")
        printc('  - Green:', C_GREEN + C_BRIGHT, "bright text")
        printc('  - Green:', C_GREEN + C_BRIGHT + C_BRIGHT, "bright bold text")
        printc('  - Bright vs. bold:', C_YELLOW + C_BRIGHT, "Bright yellow,", C_RESET_FG, "default color")
        printc()
        if numColors() > 16:
            printc("Color 16 to 255 behavior:")
            printc('  - Black:', Color.fg6(0, 0, 0), C_BRIGHT, "bold text")
            printc('  - Green:', Color.fg6(0, 4, 1), "regular text")
            printc('  - Green:', Color.fg6(0, 4, 1) + C_BRIGHT, "bold text")

    if "--chart" in _sys.argv:
        print()
        printc("standard text, ", C_BRIGHT, "bold text", C_RESET_BRIGHT, ".", sep="")
        print()
        print(" {:<26}  {:<26}".format("foreground colors", "background colors"))
        for i in range(8):
            printc("  {:2}:".format(i)  , Color.fg(i)      , "{:<7}".format(colorname(i)), C_RESET_FG,
                   "  {:2}:".format(i+8), Color.fg(i, True), "{:<7}".format(colorname(i)), C_RESET_FG,
                   "  {:2}:".format(i)  , Color.bg(i)      , "{:<7}".format(colorname(i)), C_RESET_BG,
                   "  {:2}:".format(i+8), Color.bg(i, True), "{:<7}".format(colorname(i)), C_RESET_BG)


    if "--chart256" in _sys.argv or "--chart256bg" in _sys.argv:
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
