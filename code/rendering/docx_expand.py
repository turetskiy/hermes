"""Expanding one anchor paragraph into N lines, one per item - split out of docx_write.py by concern
(that module writes into a single already-existing paragraph; this clones new ones). No pre-allocated
capacity needed in the template: a role/section can hold any number of items, the template just needs
ONE anchor paragraph for fill_template.py to expand from."""
import copy

from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

from rendering.docx_write import set_segments


def expand_lines(anchor, items, render):
    """Replace one anchor paragraph with N lines, one per item - each a separate paragraph cloning
    the anchor's FULL pPr (paragraph style/spacing/etc AND any direct formatting on top of it, e.g. a
    real Word bullet-list numPr, which a hand-marked-up custom template's bullet anchor typically has
    as direct formatting rather than something its style alone carries - copying only `.style` silently
    dropped that, so every line but the first came out with no bullet marker at all). render(paragraph,
    item) fills one line."""
    if not items:                    # nothing to show (e.g. a from-scratch track) -> blank the anchor
        set_segments(anchor, "")
        return
    anchor_pPr = anchor._p.pPr
    render(anchor, items[0])
    prev = anchor._p
    for item in items[1:]:
        new_p = OxmlElement("w:p")
        if anchor_pPr is not None:
            new_p.append(copy.deepcopy(anchor_pPr))
        prev.addnext(new_p)
        para = Paragraph(new_p, anchor._parent)
        render(para, item)
        prev = new_p


def _cluster_markup(c):
    return f"**{c['label']}:** {c['items']}" if c.get("label") else c["items"]


def expand_labeled_lines(anchor, clusters):
    """Skills clusters as '**Label:** items' lines (bold label; label omitted if empty)."""
    expand_lines(anchor, clusters, lambda p, c: set_segments(p, _cluster_markup(c)))
