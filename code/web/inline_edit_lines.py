"""attach_inline_edit_lines(field) - the line-targeted variant of web/inline_edit.py's popover, for a
big multi-line document (the factbook's raw-markdown textarea) where "the field" is too coarse a target:
clicking a bullet line should edit just that line. Split out of inline_edit.py by concern - reuses its
shared popover core and single-popover/busy-lock registry.

The highlight is a painted overlay `<div>`, not native text selection - a textarea's selection only
renders while IT is focused, and typing into the popover's own instruction box necessarily moves focus
there, which would silently erase a selection-based highlight. The overlay is computed via the classic
"mirror div" trick (an offscreen div reproducing the textarea's exact font/padding/line-wrapping, used
to measure where the target substring would land) and painted at those coordinates with `position:
fixed`, independent of DOM focus.

Scope trade-off: the popover itself still anchors to the whole field (Quasar's default anchor-to-
parent), not to the exact pixel position of the clicked line - only the highlight is pixel-precise."""
from web.inline_edit import _build_core, _request_open

_GET_TEXTAREA = '''
const root = getHtmlElement({id});
const ta = root.tagName === "TEXTAREA" ? root : root.querySelector("textarea");
'''

_LOCATE_JS = _GET_TEXTAREA + '''
const pos = ta.selectionStart;
const text = ta.value;
const start = text.lastIndexOf("\\n", pos - 1) + 1;
let end = text.indexOf("\\n", pos);
if (end === -1) end = text.length;
return {{start: start, end: end, text: text.slice(start, end)}};
'''

_HIGHLIGHT_ID = "inline-edit-hl-{id}"

_PAINT_JS = _GET_TEXTAREA + '''
const prev = document.getElementById("''' + _HIGHLIGHT_ID + '''");
if (prev) prev.remove();
const style = getComputedStyle(ta);
const mirror = document.createElement("div");
["boxSizing", "width", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
 "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth",
 "fontFamily", "fontSize", "fontWeight", "fontStyle", "letterSpacing", "lineHeight",
 "wordSpacing", "tabSize"].forEach(p => mirror.style[p] = style[p]);
Object.assign(mirror.style, {{position: "fixed", visibility: "hidden", whiteSpace: "pre-wrap",
    wordWrap: "break-word", top: "-9999px", left: "-9999px", height: "auto"}});
document.body.appendChild(mirror);
const text = ta.value;
mirror.appendChild(document.createTextNode(text.substring(0, {start})));
const span = document.createElement("span");
span.textContent = text.substring({start}, {end}) || " ";
mirror.appendChild(span);
mirror.appendChild(document.createTextNode(text.substring({end})));
const spanRect = span.getBoundingClientRect();
const mirrorRect = mirror.getBoundingClientRect();
const taRect = ta.getBoundingClientRect();
const hl = document.createElement("div");
hl.id = "''' + _HIGHLIGHT_ID + '''";
Object.assign(hl.style, {{
    position: "fixed", pointerEvents: "none", background: "rgba(251, 191, 36, 0.45)",
    top: (taRect.top + (spanRect.top - mirrorRect.top) - ta.scrollTop) + "px",
    left: (taRect.left + (spanRect.left - mirrorRect.left) - ta.scrollLeft) + "px",
    width: spanRect.width + "px", height: spanRect.height + "px", zIndex: 9999,
}});
document.body.appendChild(hl);
mirror.remove();
'''

_CLEAR_JS = '''
const el = document.getElementById("''' + _HIGHLIGHT_ID + '''");
if (el) el.remove();
'''


def attach_inline_edit_lines(field):
    from nicegui import ui

    line = {"start": 0, "end": 0}

    def set_highlight(on):
        js = _PAINT_JS.format(id=field.id, start=line["start"], end=line["end"]) if on \
            else _CLEAR_JS.format(id=field.id)
        ui.run_javascript(js)

    def get_text():
        return field.value[line["start"]:line["end"]]

    def set_text(new_text):
        full = field.value
        field.value = full[:line["start"]] + new_text + full[line["end"]:]
        line["end"] = line["start"] + len(new_text)
        set_highlight(True)  # the highlighted range's length (and so its pixel box) just changed

    open_popover, close = _build_core(get_text, set_text, set_highlight)

    async def _on_click():
        loc = await ui.run_javascript(_LOCATE_JS.format(id=field.id))
        if not loc["text"].strip().startswith(("-", "*")):
            return  # not a bullet line - leave normal editing alone
        line["start"], line["end"] = loc["start"], loc["end"]
        _request_open(open_popover, close)

    # "click" never reaches the server for a Quasar textarea (something in QField's own click
    # handling swallows it before it bubbles to nicegui's listener) - "mouseup" fires reliably and
    # happens at the same point in the interaction (after the browser has already placed the caret).
    field.on("mouseup", _on_click)
