"""Identity panel for the Profile screen: name/contact/education/companies (identity.json, global -
the same person across every track) plus this track's label/headline/summary/footer_title (small text
fields, positioning.json). One form, one "Save identity" button. Role title/dates/bullets live in
web/profile_roles.py instead, alongside each role's own Build/Save. Split out of web/profile.py by
concern."""
from web.inline_edit import attach_inline_edit
from web.notify import notify
from web.progress import busy

ROLE_SLOTS = ("role1", "role2", "role3", "role4")


def build_identity_panel(get_track_id, push_line, register, others, on_saved=None):
    from nicegui import ui
    import profile
    import profile_store
    from content import profile_drafts

    with ui.expansion("Identity").classes("w-full") as panel:
        with ui.row().classes("w-full gap-3"):
            label_in = ui.input("Track label (e.g. the target role)").classes("flex-1")
            name_in = ui.input("Name").classes("flex-1")
        contact_in = ui.input("Contact (city, country - email - phone - linkedin)").classes("w-full")
        with ui.row().classes("w-full gap-3"):
            degree_in = ui.input("Degree").classes("flex-1")
            institution_in = ui.input("Institution").classes("flex-1")
            edu_dates_in = ui.input("Education dates").classes("flex-1")
        with ui.row().classes("w-full gap-3"):
            company_ins = {r: ui.input(f"{r} company").classes("flex-1") for r in ROLE_SLOTS}
        headline_in = ui.input("Headline").classes("w-full")
        summary_in = ui.textarea("Summary").props("rows=3").classes("w-full")
        footer_in = ui.input("Footer title").classes("w-full")
        for f in (headline_in, summary_in, footer_in):
            attach_inline_edit(f)

        async def save():
            tid = get_track_id()
            if not tid:
                notify("Track id can't be empty", type="warning")
                return
            async with busy(save_btn, *others(save_btn)):
                identity = {
                    "name": name_in.value, "contact": contact_in.value,
                    "education": {"degree": degree_in.value, "institution": institution_in.value,
                                  "dates": edu_dates_in.value},
                    "companies": {r: inp.value for r, inp in company_ins.items()},
                }
                profile.write_identity(identity, tid, label_in.value.strip() or tid,
                                        headline_in.value, summary_in.value, footer_in.value)
                push_line(f"Saved identity + track metadata for '{tid}'")
                notify("Identity saved", type="positive")
                if on_saved:
                    on_saved()

        save_btn = register(ui.button("Save identity", on_click=save))

    def load(track_id):
        identity = profile_store.load_identity()
        meta = profile_store.load_track_meta(track_id) if track_id else {}
        draft = profile_drafts.get(track_id) if track_id else None
        d_identity = (draft or {}).get("identity", {})

        name_in.value = identity.get("name") or d_identity.get("name", "")
        contact_in.value = identity.get("contact") or d_identity.get("contact", "")
        edu = identity.get("education") or d_identity.get("education") or {}
        degree_in.value = edu.get("degree", "")
        institution_in.value = edu.get("institution", "")
        edu_dates_in.value = edu.get("dates", "")
        companies = identity.get("companies") or d_identity.get("companies") or {}
        for r, inp in company_ins.items():
            inp.value = companies.get(r, "")
        label_in.value = meta.get("label") or (track_id or "")
        headline_in.value = meta.get("headline") or (draft or {}).get("headline", "")
        summary_in.value = meta.get("summary") or (draft or {}).get("summary", "")
        footer_in.value = meta.get("footer_title") or (draft or {}).get("footer_title", "")

        # collapsed by default once there's something to show - expanded (needs attention) otherwise
        panel.value = not bool(name_in.value)
        panel._props["caption"] = name_in.value
        panel.update()

    return panel, load
