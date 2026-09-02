"""Fetch a job description from a URL. Used by web/tailor.py."""
import re


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
