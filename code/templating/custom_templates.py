"""Custom templates: any OTHER .docx sitting directly in data/ (besides template.docx itself) is a
ready-made, hand-marked-up template - discovered just by being there, no registration step. It must
carry the same {{PLACEHOLDER}} tokens tpl_skeleton.py's generated templates do (see that file's own
docstring for the full token list) for fill_template.py to be able to fill it. Its meta sidecar (same
stem + .meta.json - style/body_font/bold_font/link_font/speak_header/articles_header/tagline/
list_color/footer_size, see build_template.py's _write_meta() for the shape) carries its fonts/colors;
falls back to docx_write.py's own defaults (Calibri Light/Calibri) if there's no sidecar, which suit
most résumés reasonably well."""
import os
import shutil

import docx

import paths

_REQUIRED_TOKENS = ("{{TAGLINE}}", "{{SUMMARY}}", "{{SKILLS}}")


def _is_marked_up(path):
    """Cheap sanity check: does this .docx actually carry Hermes's placeholder tokens? Filters out a
    plain, non-tokenized .docx that happens to sit in the same folder (e.g. the original resume a
    custom template was hand-marked-up from) - offering it as a "style" would fail immediately with a
    confusing placeholder-not-found error the moment someone picked it."""
    try:
        text = "\n".join(p.text for p in docx.Document(path).paragraphs)
    except Exception:  # noqa: BLE001 - not a valid/readable .docx at all
        return False
    return all(token in text for token in _REQUIRED_TOKENS)


def list_custom():
    """[stem, ...] for every actually-marked-up custom .docx in data/, sorted."""
    if not os.path.isdir(paths.DATA):
        return []
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(paths.DATA)
        if f.lower().endswith(".docx") and f != "template.docx"
        and _is_marked_up(os.path.join(paths.DATA, f))
    )


def build(stem, template_path, meta_path):
    """Copy data/<stem>.docx (+ its .meta.json sidecar, if present) into place as the active
    template/meta, mirroring what build_template.build() does for a generated style."""
    src = os.path.join(paths.DATA, f"{stem}.docx")
    if not os.path.exists(src):
        raise SystemExit(f"custom template '{stem}' not found at {src}")
    shutil.copy(src, template_path)
    meta_src = os.path.join(paths.DATA, f"{stem}.meta.json")
    if os.path.exists(meta_src):
        shutil.copy(meta_src, meta_path)
    elif os.path.exists(meta_path):
        os.remove(meta_path)  # no sidecar for this one - don't leave a stale one from a prior style
    return template_path
