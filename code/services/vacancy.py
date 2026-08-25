"""Get the job description: fetch a URL, paste it, or skip (returns None)."""
import re
import sys

from services.ui import ask, ask_choice, yes


def fetch_url(url):
    try:
        import requests
        from bs4 import BeautifulSoup
        html = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return re.sub(r"\n{3,}", "\n\n", soup.get_text("\n")).strip()
    except Exception as e:  # noqa: BLE001
        print(f"  ! fetch error: {e}")
        return ""


def _paste():
    print("Paste the job description. End with a line containing only: END")
    lines = []
    while True:
        line = sys.stdin.readline()
        if not line or line.rstrip("\n") == "END":
            break
        lines.append(line)
    return "".join(lines).strip() or None


def get_vacancy():
    """Return the JD text, or None to run without a vacancy (baseline + feedback only)."""
    print("\n== Vacancy ==")
    mode = ask_choice("Vacancy source?", ["fetch a URL", "paste the text", "skip (no vacancy)"])
    if mode == "skip (no vacancy)":
        return None
    if mode == "fetch a URL":
        jd = fetch_url(ask("Vacancy URL"))
        if jd and len(jd) > 200:
            print(f"  fetched {len(jd)} chars.")
            if yes("Use fetched text?"):
                return jd
        else:
            print("  fetch failed or too short - paste it instead.")
    return _paste()
