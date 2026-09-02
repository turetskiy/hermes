"""Expanding one anchor paragraph into N lines, one per item - split out of docx_write.py by concern
(that module writes into a single already-existing paragraph; this clones new ones). No pre-allocated
capacity needed in the template: a role/section can hold any number of items, the template just needs
ONE anchor paragraph for fill_template.py to expand from."""
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

from rendering.docx_write import set_segments


def expand_lines(anchor, items, render):
    """Replace one anchor paragraph with N lines, one per item - each a separate paragraph cloning
    the anchor's style. render(paragraph, item) fills one line."""
    if not items:                    # nothing to show (e.g. a from-scratch track) -> blank the anchor
        set_segments(anchor, "")
        return
    style = anchor.style
    render(anchor, items[0])
    prev = anchor._p
    for item in items[1:]:
        new_p = OxmlElement("w:p")
        prev.addnext(new_p)
        para = Paragraph(new_p, anchor._parent)
        para.style = style
        render(para, item)
        prev = new_p


def _cluster_markup(c):
    return f"**{c['label']}:** {c['items']}" if c.get("label") else c["items"]


def expand_labeled_lines(anchor, clusters):
    """Skills clusters as '**Label:** items' lines (bold label; label omitted if empty)."""
    expand_lines(anchor, clusters, lambda p, c: set_segments(p, _cluster_markup(c)))
