"""The inbox file manager on the Material screen: the file list, the upload control (hidden once
there's something in the inbox already), and its show/hide toggle. Split out of web/material.py by
concern - purely local file I/O, no model calls, so it has nothing to do with the factbook build/save
flow beyond needing to be frozen (see screen_lock()) while a Build reads the same inbox directory."""
import os

from services.osutil import open_path
from web.notify import notify


def build_file_manager(inbox):
    from nicegui import ui

    def listed_files():
        return [f for f in sorted(os.listdir(inbox)) if f.lower() != "readme.txt" and not f.startswith(".")]

    starts_empty = not listed_files()  # nudge the upload control open only when the inbox is empty

    files_table = ui.table(
        rows=[], row_key="name",
        columns=[
            {"name": "name", "label": "Name", "field": "name", "align": "left"},
            {"name": "type", "label": "Type", "field": "type", "align": "left"},
        ],
    ).classes("w-full").props("dense flat bordered").style("height: 12rem")

    def refresh_files():
        rows = []
        for f in listed_files():
            if os.path.isdir(os.path.join(inbox, f)):
                rows.append({"name": f, "type": "Folder"})
            else:
                ext = os.path.splitext(f)[1].lstrip(".").upper()
                rows.append({"name": f, "type": ext or "File"})
        files_table.rows = rows

    def on_upload(e):
        with open(os.path.join(inbox, e.name), "wb") as f:
            f.write(e.content.read())
        refresh_files()
        notify(f"Added {e.name}")

    def toggle_upload():
        upload_ctl.set_visibility(not upload_ctl.visible)
        add_files_btn.set_text("Hide upload" if upload_ctl.visible else "Add files")

    with ui.row():
        add_files_btn = ui.button("Hide upload" if starts_empty else "Add files",
                                   on_click=toggle_upload).props("outline")
        ui.button("Open inbox folder", on_click=lambda: open_path(inbox)).props("outline")

    upload_ctl = ui.upload(on_upload=on_upload, auto_upload=True, multiple=True)
    upload_ctl.props("flat bordered").classes("w-full")
    upload_ctl.set_visibility(starts_empty)

    refresh_files()
    return add_files_btn, upload_ctl
