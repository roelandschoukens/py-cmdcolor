# CmdColor

Print text in the 16 colors supported on the Windows console.

 - On Windows, use the win32 Console API. Also use this API for printing, so older Python versions can print Unicode.
 - If `curses` is available, use that. Use colors 0 to 15 if available. On 8 color terminals (some GNU screen builds, winpty), use the bold bold attribute. Note that you can't use bright background colors on such terminals.

Use the `printc()` function and the various `C_...` constants defined in this package.

```
printc("Print ", C_RED, "red", C_RESET, " and ", C_BLUE.bright(), " text.")
```
