"""Central palette for the Convox dark theme.

All widgets should reference these constants instead of hard-coding hex
strings. Keeps the look consistent and makes future re-theming trivial.
"""

# Surfaces (darkest to lightest)
BG_DEEPEST = "#16181d"     # window background
BG_BASE = "#1f2127"        # main panels
BG_RAISED = "#262932"      # raised cards / inputs
BG_ELEVATED = "#2f3340"    # hover surface
BG_HIGHLIGHT = "#3a3f4d"   # selected / active

# Borders
BORDER_SOFT = "#2a2d36"
BORDER_STRONG = "#3a3f4d"

# Text
TEXT_PRIMARY = "#f2f3f5"
TEXT_SECONDARY = "#b9bbbe"
TEXT_MUTED = "#72767d"
TEXT_DISABLED = "#4f535c"

# Brand / accents
ACCENT = "#5865f2"          # primary brand (Discord blurple)
ACCENT_HOVER = "#6b75f5"
ACCENT_PRESSED = "#4752c4"

SUCCESS = "#3ba55d"
SUCCESS_HOVER = "#43b663"
WARNING = "#faa61a"
DANGER = "#ed4245"
DANGER_HOVER = "#f04347"

# Status indicators (presence)
STATUS_ONLINE = "#3ba55d"
STATUS_IDLE = "#faa61a"
STATUS_DND = "#ed4245"
STATUS_OFFLINE = "#747f8d"
STATUS_VOICE = "#5865f2"
STATUS_IN_MATCH = "#eb6cff"

# Self / mention highlight tints
SELF_BUBBLE = "#3a4c8c"
OTHER_BUBBLE = "#2f3340"
SYSTEM_BUBBLE = "#26333d"
PRIVATE_BUBBLE = "#54356b"


def status_color(status: str) -> str:
    """Map a presence-status string to a hex color."""
    status = (status or "").upper()
    return {
        "ONLINE": STATUS_ONLINE,
        "IN_ROOM": STATUS_ONLINE,
        "VOICE_ACTIVE": STATUS_VOICE,
        "IN_MATCH": STATUS_IN_MATCH,
        "DO_NOT_DISTURB": STATUS_DND,
        "IDLE": STATUS_IDLE,
        "OFFLINE": STATUS_OFFLINE,
    }.get(status, STATUS_OFFLINE)
