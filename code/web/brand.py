"""The page header: an inline SVG caduceus (Hermes's winged staff with two entwined serpents) plus
the "Hermes" wordmark. Drawn by hand as a symmetric vector icon - no external image, nothing fetched -
one wing/snake path is mirrored via <use> for perfect left-right symmetry. Uses currentColor so it
follows the surrounding text color (light/dark) automatically."""

CADUCEUS_SVG = """
<svg viewBox="0 0 64 72" width="40" height="45" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <path id="wing" d="M32 23 C 40 17, 50 14, 58 8 C 52 18, 44 22, 35 26 Z"/>
    <path id="snake" d="M32 67 C 46 61, 46 51, 32 46 C 18 41, 18 32, 32 27 C 43 23, 44 18, 35 14"/>
  </defs>
  <line x1="32" y1="69" x2="32" y2="13" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
  <circle cx="32" cy="10" r="3.5" fill="currentColor"/>
  <use href="#wing" fill="currentColor" opacity="0.85"/>
  <use href="#wing" fill="currentColor" opacity="0.85" transform="scale(-1,1) translate(-64,0)"/>
  <use href="#snake" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
  <use href="#snake" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"
       transform="scale(-1,1) translate(-64,0)"/>
  <circle cx="35" cy="14" r="2" fill="currentColor"/>
  <circle cx="29" cy="14" r="2" fill="currentColor"/>
</svg>
"""


def header():
    from nicegui import ui
    with ui.row().classes("items-center gap-2"):
        ui.html(CADUCEUS_SVG, sanitize=False)
        ui.label("Hermes").classes("text-4xl font-bold tracking-tight")
