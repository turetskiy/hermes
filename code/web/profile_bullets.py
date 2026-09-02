"""Per-role bullet-count controls for the Profile screen - roles.roleN.max_bullets exposed as explicit
number inputs (previously only reachable by hand-editing result_box's raw JSON), synced both ways.
Defaults match profile_write.py's DEFAULT_MAX_BULLETS - the one place Hermes, not any template,
decides how many bullets a role starts with. 0 is a valid value and also this screen's answer to
"how do I exclude a role" - content/assemble.py already drops a role with no bullets from the resume
entirely (roles[role_slot] = None), same as a role with nothing tagged to it in block_tracks.json."""
import json

DEFAULTS = {"role1": 6, "role2": 4, "role3": 3, "role4": 2}


def build_bullet_controls(result_box):
    """Returns (row, pull_from_json) - call pull_from_json() any time result_box.value is replaced
    wholesale (a track loaded, or a fresh profile built) so the inputs pick up its current values."""
    from nicegui import ui

    inputs = {}

    def push_to_json():
        try:
            data = json.loads(result_box.value)
        except ValueError:
            return  # mid hand-edit / not valid JSON right now - leave result_box alone
        roles = data.get("roles", {})
        for r, inp in inputs.items():
            if isinstance(roles.get(r), dict):
                roles[r]["max_bullets"] = int(inp.value)
        result_box.value = json.dumps(data, ensure_ascii=False, indent=2)

    def pull_from_json():
        """Also shows the row - called whenever result_box gets fresh content to reflect, so callers
        don't need a separate set_visibility(True) of their own."""
        try:
            data = json.loads(result_box.value)
        except ValueError:
            return
        roles = data.get("roles", {})
        for r, inp in inputs.items():
            role = roles.get(r)
            mb = role.get("max_bullets") if isinstance(role, dict) else None
            inp.value = mb if isinstance(mb, int) else DEFAULTS[r]
        row.set_visibility(True)

    with ui.row().classes("w-full gap-3") as row:
        for r, default in DEFAULTS.items():
            inp = ui.number(f"Bullets - {r}", value=default, min=0, max=30, precision=0) \
                .classes("flex-1 min-w-0").tooltip(f"0 excludes {r} from the resume entirely")
            inp.on_value_change(push_to_json)
            inputs[r] = inp
    row.set_visibility(False)

    return row, pull_from_json
