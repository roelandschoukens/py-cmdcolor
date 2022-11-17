# CmdColor

This is Roeland’s CMD color module, which abstracts away either the ANSI color
codes on VT-style terminals, or the win32 console API. The latter is also called
directly for printing text so you can print any Unicode character up to U+FFFF
on the console.

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

## Output modes

Color modes used by this package:

 - `Win32`: Console API: old versions of Windows. You may define an environment variable
   `%CMDCOLOR_ANSI%` and set it to `0` if you want this mode on current Windows versions.
 - `ANSI`: ANSI escape codes: Windows versions that support the ENABLE_VIRTUAL_TERMINAL_PROCESSING flag.
 - `Curses`: where available we obtain valid escape codes from terminfo. However terminfo
   does not provide codes for reset bold, background and foreground separately, for that we send
   the standard ANSI escape codes.
 - `None`: For output handles which aren’t terminals.

## Caveats

Curses thinks GNU screen only supports 8 colors. It actually supports both 16 foreground
colors and 16 background colors.
