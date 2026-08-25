"""
build_template.py - generate data/template.docx (+ data/template.meta.json) in one of three styles.

Every style is single-column and ATS-safe; they differ only in typography, rules, accent colour, and
header/role treatment. All three emit the SAME {{PLACEHOLDER}} tokens, so fill_template.py fills any of
them the same way. The meta sidecar tells fill_template which fonts/accent to use when it writes the
tailored content in (so e.g. the serif Gazette body stays serif after filling).

  ledger   - sans body + mono labels/dates, slate-blue accent
  column   - serif name + sans body, forest-green accent
  gazette  - serif body, editorial caps kickers, oxblood accent

CLI:  python -m templating.build_template <ledger|column|gazette>      (run from code/)
API:  build_template.build("ledger")  ->  writes data/template.docx, returns its path
      build_template.list_styles()    ->  ["ledger", "column", "gazette"]
"""
import json
import os
import sys

if __package__ in (None, ""):  # allow `python code/templating/build_template.py ...` direct runs
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import docx

import paths
from templating import tpl_common as C
from templating.tpl_skeleton import build_skeleton

TEMPLATE_PATH = os.path.join(paths.DATA, "template.docx")
META_PATH = os.path.join(paths.DATA, "template.meta.json")


def _identity():
    """name/contact/companies/education baked into the fixed tokens, from data/identity.json (profile.py)."""
    try:
        with open(os.path.join(paths.DATA, "identity.json")) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}

SLATE, FOREST, OXBLOOD = "3C5A74", "34594A", "7C3B46"
INK, MUTED = C.INK, C.MUTED
CALIBRI, LIGHT, CONSOLAS, CAMBRIA = "Calibri", "Calibri Light", "Consolas", "Cambria"


def _theme(style, margins, accent, name, tagline, contact, divider, header, role,
           body_font, bold_font, list_color):
    left, right = margins[2], margins[3]
    return {
        "style": style, "margins": margins, "muted": MUTED, "accent": accent,
        "name": name, "tagline": tagline, "contact": contact, "divider": divider,
        "header": header, "role": role,
        "body_font": body_font, "bold_font": bold_font, "link_font": CALIBRI,
        "body_size": 10.5 if style != "gazette" else 11, "footer_size": 8,
        "list_color": list_color, "tab_cm": round(C.A4_W - left - right, 2),
    }


LEDGER = _theme(
    "ledger", (1.4, 1.4, 1.7, 1.7), SLATE,
    name={"font": CALIBRI, "size": 22, "bold": True},
    tagline={"font": CONSOLAS, "size": 8.5, "color": SLATE, "caps": True, "spacing": 24},
    contact={"font": CONSOLAS, "size": 8.5, "color": MUTED},
    divider={"color": SLATE, "sz": 8},
    header={"run": {"font": CONSOLAS, "size": 8.5, "color": MUTED, "caps": True, "spacing": 22},
            "rule": None},
    role={"title_font": CALIBRI, "title_size": 11, "company_font": CALIBRI, "company_size": 10.5,
          "company_color": MUTED, "date_font": CONSOLAS, "date_size": 8.5, "date_color": MUTED},
    body_font=LIGHT, bold_font=CALIBRI, list_color=SLATE,
)

COLUMN = _theme(
    "column", (1.4, 1.4, 1.5, 1.5), FOREST,
    name={"font": CAMBRIA, "size": 24, "bold": True},
    tagline={"font": CALIBRI, "size": 10.5, "color": MUTED},
    contact={"font": CALIBRI, "size": 9, "color": MUTED},
    divider={"color": FOREST, "sz": 18},
    header={"run": {"font": CALIBRI, "size": 8.5, "color": FOREST, "caps": True, "spacing": 26,
                    "bold": True}, "rule": None},
    role={"title_font": CALIBRI, "title_size": 11, "company_font": CALIBRI, "company_size": 10,
          "company_color": FOREST, "date_font": CALIBRI, "date_size": 9, "date_color": MUTED},
    body_font=LIGHT, bold_font=CALIBRI, list_color=FOREST,
)

GAZETTE = _theme(
    "gazette", (1.4, 1.4, 1.7, 1.7), OXBLOOD,
    name={"font": CAMBRIA, "size": 26, "bold": True},
    tagline={"font": CALIBRI, "size": 8.5, "color": MUTED, "caps": True, "spacing": 32},
    contact={"font": CALIBRI, "size": 9, "color": MUTED},
    divider={"color": INK, "sz": 16},
    header={"run": {"font": CALIBRI, "size": 8.5, "color": MUTED, "caps": True, "spacing": 30,
                    "bold": True}, "rule": {"color": OXBLOOD, "sz": 10, "space": 3}},
    role={"title_font": CAMBRIA, "title_size": 11.5, "company_font": CAMBRIA, "company_size": 11,
          "company_color": MUTED, "company_italic": True, "date_font": CALIBRI, "date_size": 9,
          "date_color": MUTED},
    body_font=CAMBRIA, bold_font=CAMBRIA, list_color=OXBLOOD,
)

THEMES = {"ledger": LEDGER, "column": COLUMN, "gazette": GAZETTE}


def list_styles():
    return list(THEMES)


def _write_meta(t):
    meta = {
        "style": t["style"], "body_font": t["body_font"], "bold_font": t["bold_font"],
        "link_font": t["link_font"], "speak_header": "Public speeches", "articles_header": "Articles",
        "tagline": t["tagline"], "list_color": t["list_color"], "footer_size": t["footer_size"],
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)


def build(style):
    if style not in THEMES:
        raise SystemExit(f"unknown style '{style}'. Known: {list_styles()}")
    t = {**THEMES[style], "identity": _identity()}
    doc = docx.Document()
    C.setup_page(doc, t["margins"])
    C.normal_style(doc, t["body_font"], t["body_size"])
    build_skeleton(doc, t)
    doc.save(TEMPLATE_PATH)
    _write_meta(t)
    return TEMPLATE_PATH


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in THEMES:
        raise SystemExit(f"usage: python -m templating.build_template <{'|'.join(list_styles())}>")
    print("wrote", build(sys.argv[1]))
    print("wrote", META_PATH)
