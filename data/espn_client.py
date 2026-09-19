from __future__ import annotations

from typing import Optional
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

class ESPNError(RuntimeError):
    pass


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "LATAMDATA/0.2 (+https://github.com/mellinskdata/latamdata)",
        "Accept": "application/json,text/plain,*/*",
    })
    return session


class ESPNClient:
    """Replaceable adapter for ESPN web JSON endpoints."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.http = _session()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{BASE}/{path.lstrip('/')}"
        try:
            response = self.http.get(url, params=params or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ESPNError(f"Falha ao consultar a fonte online: {exc}") from exc

    def scoreboard(self, league_slug: str, season: int, limit: int = 1000) -> dict:
        return self._get(f"{league_slug}/scoreboard", {"dates": str(season), "limit": limit})

    def teams(self, league_slug: str) -> dict:
        return self._get(f"{league_slug}/teams", {"limit": 100})

    def summary(self, league_slug: str, event_id: str) -> dict:
        return self._get(f"{league_slug}/summary", {"event": str(event_id)})


def _score(comp: dict, side: str):
    competitor = next((c for c in comp.get("competitors", []) if c.get("homeAway") == side), {})
    value = competitor.get("score")
    try:
        return int(float(value)) if value not in (None, "") else None
    except Exception:
        return None


def normalize_scoreboard(payload: dict, league_key: str, league_name: str) -> pd.DataFrame:
    rows = []
    for event in payload.get("events", []) or []:
        competitions = event.get("competitions") or []
        if not competitions:
            continue
        comp = competitions[0]
        competitors = comp.get("competitors") or []
        home = next((x for x in competitors if x.get("homeAway") == "home"), {})
        away = next((x for x in competitors if x.get("homeAway") == "away"), {})
        home_team = home.get("team") or {}
        away_team = away.get("team") or {}
        status = (event.get("status") or {}).get("type") or {}
        venue = comp.get("venue") or {}
        rows.append({
            "event_id": str(event.get("id", "")),
            "league_key": league_key,
            "league": league_name,
            "date": pd.to_datetime(event.get("date"), utc=True, errors="coerce"),
            "home_id": str(home_team.get("id", "")),
            "home": home_team.get("displayName") or home_team.get("name") or "Mandante",
            "home_logo": home_team.get("logo") or "",
            "away_id": str(away_team.get("id", "")),
            "away": away_team.get("displayName") or away_team.get("name") or "Visitante",
            "away_logo": away_team.get("logo") or "",
            "home_score": _score(comp, "home"),
            "away_score": _score(comp, "away"),
            "status": status.get("description") or status.get("detail") or "",
            "completed": bool(status.get("completed", False)),
            "venue": venue.get("fullName") or "",
        })
    return pd.DataFrame(rows)


def normalize_teams(payload: dict, league_key: str, league_name: str) -> pd.DataFrame:
    sports = payload.get("sports") or []
    leagues = sports[0].get("leagues", []) if sports else []
    teams = leagues[0].get("teams", []) if leagues else []
    rows = []
    for wrapper in teams:
        team = wrapper.get("team") or wrapper
        logos = team.get("logos") or []
        rows.append({
            "team_id": str(team.get("id", "")),
            "team": team.get("displayName") or team.get("name") or "",
            "logo": (logos[0].get("href") if logos else None) or team.get("logo") or "",
            "league_key": league_key,
            "league": league_name,
        })
    return pd.DataFrame(rows)


def teams_from_matches(matches: pd.DataFrame) -> pd.DataFrame:
    if matches.empty:
        return pd.DataFrame(columns=["team_id", "team", "logo", "league_key", "league"])
    home = matches[["home_id", "home", "home_logo", "league_key", "league"]].rename(
        columns={"home_id": "team_id", "home": "team", "home_logo": "logo"}
    )
    away = matches[["away_id", "away", "away_logo", "league_key", "league"]].rename(
        columns={"away_id": "team_id", "away": "team", "away_logo": "logo"}
    )
    return pd.concat([home, away], ignore_index=True).drop_duplicates(["league_key", "team_id", "team"])


def match_header(summary: dict) -> dict:
    header = summary.get("header") or {}
    comps = header.get("competitions") or []
    comp = comps[0] if comps else {}
    competitors = comp.get("competitors") or []
    home = next((x for x in competitors if x.get("homeAway") == "home"), {})
    away = next((x for x in competitors if x.get("homeAway") == "away"), {})
    status = (comp.get("status") or {}).get("type") or {}
    return {
        "home": (home.get("team") or {}).get("displayName") or "Mandante",
        "away": (away.get("team") or {}).get("displayName") or "Visitante",
        "home_logo": (home.get("team") or {}).get("logo") or "",
        "away_logo": (away.get("team") or {}).get("logo") or "",
        "home_score": home.get("score"),
        "away_score": away.get("score"),
        "status": status.get("description") or status.get("detail") or "",
        "venue": (comp.get("venue") or {}).get("fullName") or "",
        "date": pd.to_datetime(comp.get("date"), utc=True, errors="coerce"),
    }


def match_team_stats(summary: dict) -> pd.DataFrame:
    rows = []
    for block in (summary.get("boxscore") or {}).get("teams", []) or []:
        team = block.get("team") or {}
        row = {"team": team.get("displayName") or team.get("name") or ""}
        for stat in block.get("statistics", []) or []:
            label = stat.get("label") or stat.get("name") or "stat"
            row[label] = stat.get("displayValue") if stat.get("displayValue") is not None else stat.get("value")
        rows.append(row)
    return pd.DataFrame(rows)


def match_lineups(summary: dict) -> pd.DataFrame:
    rows = []
    for roster in summary.get("rosters", []) or []:
        team = roster.get("team") or {}
        team_name = team.get("displayName") or team.get("name") or ""
        for entry in roster.get("roster", []) or []:
            athlete = entry.get("athlete") or {}
            position = athlete.get("position") or {}
            rows.append({
                "team": team_name,
                "starter": bool(entry.get("starter", False)),
                "jersey": athlete.get("jersey") or "",
                "player": athlete.get("displayName") or athlete.get("fullName") or "",
                "position": position.get("abbreviation") or position.get("name") or "",
            })
    return pd.DataFrame(rows)


def match_events(summary: dict) -> pd.DataFrame:
    events = summary.get("keyEvents") or summary.get("details") or []
    rows = []
    for event in events:
        clock = event.get("clock") or {}
        clock = clock.get("displayValue") if isinstance(clock, dict) else clock
        team = event.get("team") or {}
        athletes = event.get("athletes") or []
        athlete = athletes[0].get("athlete", {}) if athletes and isinstance(athletes[0], dict) else {}
        event_type = event.get("type") or {}
        rows.append({
            "minute": clock or event.get("time", ""),
            "type": event_type.get("text") if isinstance(event_type, dict) else event_type,
            "text": event.get("text") or event.get("shortText") or event.get("headline") or "",
            "team": team.get("displayName") or team.get("name") or "",
            "player": athlete.get("displayName") or "",
        })
    return pd.DataFrame(rows)
