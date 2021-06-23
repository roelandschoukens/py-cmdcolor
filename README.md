# CmdColor

*Note: both main issues addressed by this packages have since been resolved:*

 - Unicode output: Python 3.6 can print Unicode to the Windows console out of the box;
 - Colors: Windows 10 introduced support for ANSI control sequences. (you still have to
   explicitly enable it).

------

Print text in the 16 colors supported on the Windows console. In most terminals you can print
ANSI colors 17 to 255 as well.

Use the `printc()` function and the various `C_...` constants defined in this package:

```
printc("Print", C_RED, "red", C_RESET, "and", C_BLUE.bright(), "blue", C_RESET, "text.")
```

If the output is not a terminal the color constants are ignored.

You may still encounter 8 color terminals (eg. vanilla GNU screen), you can't use
bright background colors on such terminals. Windows 7 and 8 support 16 colors.
