# CmdColor

This is Roeland’s CMD color module, originally intended to abstract away either the ANSI
color codes on VT-style terminals, or the win32 console API. The latter is also called
directly for printing text so you can print any Unicode character up to U+FFFF
on the console.

_You may notice that both of those problems no longer exist (they are solved in respectively
Windows 10, and Python 3.6), so the main remaining functions are to have some more convenient
interface to define RGB colors, and to have it enable VT processing on Windows._

Use the `printc()` function and the various `C_...` constants defined in this package:

```
printc("Print", C_RED, "red", C_RESET, "and", C_BLUE.bright(), "blue", C_RESET, "text.")
```

If the output is not a terminal the color constants are ignored.

## Colors 0 to 15

Windows and ANSI disagree on whether color 1 is blue or red. As the name of this package
suggests, Windows prevailed for this one.

The + operator allows creating colors 8 to 15 by adding the bright flag to colors 0 to 7.
This is because originally we represented RGBI bits on Windows (which inherited
these from CGA all the way back. This is also how we ended up with blue being color 1).
Many scripts using ANSI sequences also use bold to create the other 8 colors, eg. `'\033[1;34m'`
for bright blue. In particular, they may assume `'\033[1;30m'` yields visible dark gray.

Terminals therefore often use bright colors if you request bold for colors 0 to 7. So,
we still create bright blue with `C_BLUE + C_BRIGHT`, and using `printc(C_BLUE, C_BRIGHT, ...)`
is discouraged.

For output using curses, we assume that colors 8 to 15 are output as proper colors 8 to
15 instead of "bold" colors 0 to 7. If this is not the case, C_RESET_BRIGHT and C_RESET_FG
will behave in some funny way. This happens hopefully only when only 8 colors are supported.

If you output 256 or truecolor to a terminal that only supports 256 colors (or poor old
16-color on Windows 7), some level of fallback is provided. But obviously, manage your
expectations.

## Output modes

Color modes used by this package:

 - `Win32`: Console API: old versions of Windows. As the name of this module implies, this was the
   original way this module operated, but it is now largely obsolete. It solved 2 problems back in the
   day, one is how to print colors at all, and the second is how to print Unicode on the terminal (Python
   used the ANSI functions with the local 8-bit character set until version 3.5).
 - `ANSI`: ANSI escape codes: Windows versions that support the ENABLE_VIRTUAL_TERMINAL_PROCESSING flag. If the `%CMDCOLOR_ANSI%`
   environment variable is set to 0, cmdcolor will not attempt to enable VT processing and use the old Console API mode.
 - `Curses`: if the `curses` module is available we obtain valid codes from terminfo. Only used when `$CMDCOLOR_CURSES` is set.
 - `None`: For output handles which aren’t terminals.

### Curses

Curses is by default not used, except for detecting situations where only 16 colors are supported.
Assuming that the standard ANSI codes work seems to be more reliable than assuming Curses returns
the right info.

 - Terminfo does not provide codes for reset bold, background and foreground separately, for that we send
   the standard ANSI escape codes.

 - Curses thinks GNU screen only supports 8 colors. It actually supports both 16 foreground
   colors and 16 background colors.

 - True color support is relatively recent, and kind of weird — are colors 0 to 255 now shades
   of blue, or do they still produce the same palette as 256-color mode? When generating ANSI
   sequences directly this point is moot, since these two cases just use different sequences.
