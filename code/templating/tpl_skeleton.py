"""
tpl_skeleton.py - the single-column resume skeleton, shared by all three template styles.

build_skeleton(doc, theme) lays out every paragraph with its {{PLACEHOLDER}} token; the theme dict
(from build_template.py) supplies fonts, sizes, accent colour, and the header/role treatments.
Because every style is single-column with the same structure, one skeleton + three themes is enough.

Two kinds of token:
  auto-filled by the pipeline   {{TAGLINE}} {{SUMMARY}} {{SKILLS}} (expands to N labelled skill lines)
                                {{ROLEn_TITLE}} {{ROLEn_DATES}} {{ROLEn_Bk}} {{SPEAK_n}} {{ARTICLE_n}}
                                {{FOOTER_TITLE}}
  edited once during setup      {{NAME}} {{CONTACT}} {{ROLEn_COMPANY}} {{EDU_DEGREE/INST/DATES}}

Role bullet capacity (matches fill_template.ROLE_BULLET_CAPACITY): role1=10, role2=9, role3=7, role4=4.
"""
from docx.enum.text import WD_ALIGN_PARAGRAPH
from templating.tpl_common import para, blank, run, bottom_border, right_tab, ensure_header_style, HEADER_STYLE

ROLE_CAPACITY = [("ROLE1", 10), ("ROLE2", 9), ("ROLE3", 7), ("ROLE4", 4)]


def _fixed(t, dotted, token):
    """Value for a template-fixed field from t['identity'] (dotted path), else the {{TOKEN}} literal.
    These fields are constant per person (name, contact, companies, education) - not per-vacancy - so
    profile.py bakes them in via data/identity.json; without it the {{TOKEN}} stays for a manual edit."""
    node = t.get("identity") or {}
    for key in dotted.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    return node or token


def _header_block(doc, t):
    p = para(doc, space_after=4)
    run(p, _fixed(t, "name", "{{NAME}}"), **t["name"])
    p = para(doc, space_after=3)
    run(p, "{{TAGLINE}}", **t["tagline"])
    p = para(doc, space_after=6)
    run(p, _fixed(t, "contact", "{{CONTACT}}"), **t["contact"])
    if t.get("divider"):
        bottom_border(p, **t["divider"])


def _section_header(doc, t, label):
    p = para(doc, style=HEADER_STYLE)
    run(p, label, **t["header"]["run"])
    if t["header"].get("rule"):
        bottom_border(p, **t["header"]["rule"])
    return p


def _body_line(doc, t, token):
    p = para(doc)
    run(p, token, font=t["body_font"], size=t["body_size"])
    return p


def _role_row(doc, t, prefix, first):
    r = t["role"]
    p = para(doc, space_before=(0 if first else 6))
    right_tab(p, t["tab_cm"])
    run(p, "{{%s_TITLE}}" % prefix, font=r["title_font"], size=r["title_size"], bold=True)
    run(p, "  -  ", font=r["title_font"], size=r["title_size"], color=r["company_color"])
    run(p, _fixed(t, "companies.%s" % prefix.lower(), "{{%s_COMPANY}}" % prefix),
        font=r["company_font"], size=r["company_size"],
        color=r["company_color"], italic=r.get("company_italic", False))
    run(p, "\t")
    run(p, "{{%s_DATES}}" % prefix, font=r["date_font"], size=r["date_size"], color=r["date_color"])


def _experience(doc, t):
    _section_header(doc, t, "Experience")
    for i, (prefix, n) in enumerate(ROLE_CAPACITY):
        _role_row(doc, t, prefix, first=(i == 0))
        for k in range(1, n + 1):
            p = para(doc)
            run(p, "{{%s_B%d}}" % (prefix, k), font=t["body_font"], size=t["body_size"])


def _education(doc, t):
    _section_header(doc, t, "Education")
    r = t["role"]
    p = para(doc)
    right_tab(p, t["tab_cm"])
    run(p, _fixed(t, "education.degree", "{{EDU_DEGREE}}"), font=r["title_font"], size=r["title_size"], bold=True)
    run(p, "  -  ", font=r["title_font"], size=r["title_size"], color=r["company_color"])
    run(p, _fixed(t, "education.institution", "{{EDU_INST}}"), font=r["company_font"], size=r["company_size"],
        color=r["company_color"], italic=r.get("company_italic", False))
    run(p, "\t")
    run(p, _fixed(t, "education.dates", "{{EDU_DATES}}"), font=r["date_font"], size=r["date_size"], color=r["date_color"])


def _list_section(doc, t, label, prefix, n):
    _section_header(doc, t, label)
    for i in range(1, n + 1):
        p = para(doc)
        run(p, "{{%s_%d}}" % (prefix, i), font=t["body_font"], size=t["body_size"],
            color=t.get("list_color"))


def _footer(doc, t):
    fp = doc.sections[0].footer.paragraphs[0]
    fp.text = ""
    fp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run(fp, "{{FOOTER_TITLE}}", font=t["body_font"], size=t.get("footer_size", 8), color=t.get("muted"))


def build_skeleton(doc, t):
    ensure_header_style(doc)
    _header_block(doc, t)
    blank(doc); _section_header(doc, t, "Profile"); _body_line(doc, t, "{{SUMMARY}}")
    blank(doc); _section_header(doc, t, "Skills"); _body_line(doc, t, "{{SKILLS}}")
    blank(doc); _experience(doc, t)
    blank(doc); _education(doc, t)
    blank(doc); _list_section(doc, t, "Public speeches", "SPEAK", 4)
    blank(doc); _list_section(doc, t, "Articles", "ARTICLE", 2)
    _footer(doc, t)
