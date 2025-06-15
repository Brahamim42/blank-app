import requests
import datetime as dt

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.nba.com/",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true"
}
CDN_TEMPLATE = "https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

def get_player_id(name, season="2024-25"):
    """
    Query NBA Stats API's commonallplayers endpoint to find the exact-match player ID.
    Returns : integer player_id if found, else raises.
    """
    url = "https://stats.nba.com/stats/commonallplayers"
    params = {
        "LeagueID": "00",
        "Season": season,
        "IsOnlyCurrentSeason": "1"
    }
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    headers = data["resultSets"][0]["headers"]
    rows    = data["resultSets"][0]["rowSet"]

    idx_id   = headers.index("PERSON_ID")
    idx_name = headers.index("DISPLAY_FIRST_LAST")

    lname = name.strip().lower()
    for row in rows:
        if row[idx_name].lower() == lname:
            return row[idx_id]

    for row in rows:
        if lname in row[idx_name].lower():
            return row[idx_id]

    #raise ValueError(f"Player '{name}' not found on {season} roster.")
    return -1

def build_headshot_url(player_id):
    """
    Given NBA PERSON_ID, return the CDN URL for the 1040×760 PNG headshot.
    """
    if player_id == -1: return r"https://cdn.phenompeople.com/CareerConnectResources/NBANBAUS/social/1024x512-1670500646586.jpg"
    return CDN_TEMPLATE.format(player_id=player_id)

def fetch_nba_headshot(name, season="2024-25", save_dir="headshots"):
    """
    1. Lookup player ID.
    2. Build the CDN URL.
    """
    pid = get_player_id(name, season=season)
    headshot_url = build_headshot_url(pid)
    return headshot_url
