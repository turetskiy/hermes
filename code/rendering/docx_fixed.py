"""NAME/CONTACT/ROLEn_COMPANY/EDU_* - constant per person, not per-vacancy, but still filled by
fill_template.py in the same pass as everything else rather than baked into template.docx ahead of
time (split out of docx_write.py by concern - that module writes into ONE paragraph at a time, this
scans the whole document). No template file - generated or custom, source or working copy - ever
carries real personal data this way; only the final per-run output does."""
from docx.oxml.ns import qn

FIXED_TOKENS = {
    "{{NAME}}": "name",
    "{{CONTACT}}": "contact",
    "{{ROLE1_COMPANY}}": "companies.role1",
    "{{ROLE2_COMPANY}}": "companies.role2",
    "{{ROLE3_COMPANY}}": "companies.role3",
    "{{ROLE4_COMPANY}}": "companies.role4",
    "{{EDU_DEGREE}}": "education.degree",
    "{{EDU_INST}}": "education.institution",
    "{{EDU_DATES}}": "education.dates",
}


def _lookup(identity, dotted):
    node = identity
    for key in dotted.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    return node


def fill_fixed_tokens(doc, identity):
    """A token with no matching identity.json data is left as-is rather than blanked - same fallback
    the old per-run baking used."""
    for t in doc.element.body.iter(qn("w:t")):
        dotted = FIXED_TOKENS.get(t.text or "")
        if dotted:
            resolved = _lookup(identity, dotted)
            if resolved:
                t.text = resolved
