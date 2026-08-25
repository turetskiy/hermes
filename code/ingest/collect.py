"""Walk an inbox directory and extract text from every supported file, in a stable order.
Returns (combined_dump, used, skipped): the dump delimits each file so the model (and you) can
see provenance; used/skipped are relative-path reports so nothing silently disappears."""
import os

from ingest.extract import extract

SKIP_DIRS = {".git", "__pycache__", ".idea", ".vscode", "node_modules"}


def collect(inbox):
    if not os.path.isdir(inbox):
        raise SystemExit(f"inbox folder not found: {inbox}")
    chunks, used, skipped = [], [], []
    for root, dirs, files in os.walk(inbox):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            if name.startswith(".") or name.lower() == "readme.txt":
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, inbox)
            try:
                text = extract(path)
            except Exception as e:  # noqa: BLE001
                skipped.append(f"{rel} (error: {e})")
                continue
            if text is None:
                skipped.append(f"{rel} (unsupported type)")
                continue
            if not text.strip():
                skipped.append(f"{rel} (no extractable text)")
                continue
            used.append(rel)
            chunks.append(f"\n\n===== FILE: {rel} =====\n{text.strip()}")
    return "".join(chunks), used, skipped
