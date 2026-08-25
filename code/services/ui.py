"""Console IO helpers (EOF-safe). Single place for user prompts (DRY).

Arrow-key selection (select / ask_choice) uses ONLY the standard library (termios raw mode) - a new
user needs nothing installed for the menus to work. It degrades to a numbered prompt when stdin/stdout
is not a TTY (piped input) or termios is missing (non-Unix). Likewise `edit` uses prompt_toolkit only
if it happens to be installed, otherwise a plain keep-or-retype prompt."""
import sys


def _input(prompt):
    try:
        return input(prompt)
    except EOFError:  # end of piped input -> treat as blank
        return ""


def ask(prompt, default=None):
    suffix = f" [{default}]" if default not in (None, "") else ""
    val = _input(f"{prompt}{suffix}: ").strip()
    return val if val else (default if default is not None else "")


def yes(prompt):
    return _input(f"{prompt} [y/N]: ").strip().lower() in ("y", "yes")


def ask_choice(prompt, options):
    return select(prompt, options)


def select(title, options, descriptions=None):
    """Move the cursor over `options` with up/down (or j/k), Enter to choose. Returns the option."""
    if not options:
        raise ValueError("select(): no options to choose from")
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            import termios  # noqa: F401  Unix-only, stdlib
            return _raw_select(title, options, descriptions)
        except Exception:  # noqa: BLE001  any terminal issue -> numbered fallback
            pass
    return _numbered(title, options, descriptions)


def _render(title, options, descriptions, sel):
    lines = []
    if title:
        lines.append("\x1b[1m" + title + "\x1b[0m")
    for idx, opt in enumerate(options):
        on = idx == sel
        row = (" > " if on else "   ") + opt
        lines.append("\x1b[7m" + row + " \x1b[0m" if on else row)
        if descriptions and descriptions.get(opt):
            lines.append("\x1b[90m       " + descriptions[opt] + "\x1b[0m")
    lines.append("\x1b[90m  [up/down] move   [Enter] select\x1b[0m")
    return lines


def _raw_select(title, options, descriptions):
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    n, i = len(options), 0
    lines = _render(title, options, descriptions, i)
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = ch + sys.stdin.read(2)
                if seq == "\x1b[A":
                    i = (i - 1) % n
                elif seq == "\x1b[B":
                    i = (i + 1) % n
                else:
                    continue
            elif ch in ("k", "K"):
                i = (i - 1) % n
            elif ch in ("j", "J"):
                i = (i + 1) % n
            elif ch in ("\r", "\n"):
                break
            elif ch == "\x03":
                raise KeyboardInterrupt
            else:
                continue
            lines = _render(title, options, descriptions, i)
            sys.stdout.write(f"\x1b[{len(lines)}A" + "\n".join("\x1b[2K" + ln for ln in lines) + "\n")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return options[i]


def _numbered(prompt, options, descriptions=None):
    print(prompt)
    for idx, o in enumerate(options, 1):
        print(f"  {idx}) {o}")
        if descriptions and descriptions.get(o):
            print(f"       {descriptions[o]}")
    while True:
        raw = _input("choose #: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  invalid choice")


def edit(prompt, prefill):
    """Prompt with `prefill` already in the line, editable with the cursor - IF prompt_toolkit is
    installed. Otherwise (nothing installed / no TTY) a plain keep-or-retype prompt."""
    prefill = str(prefill)
    if sys.stdin.isatty():
        try:
            from prompt_toolkit import prompt as _pt
            return _pt(f"{prompt}: ", default=prefill)
        except Exception:  # noqa: BLE001
            pass
    got = _input(f"{prompt} [Enter=keep]: ").strip()
    return got or prefill
