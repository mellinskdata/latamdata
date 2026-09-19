from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import math
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://www.sofascore.com/api/v1"

PLAYER_FIELDS = [
    "goals", "assists", "expectedGoals", "expectedAssists", "rating",
    "minutesPlayed", "appearances", "started", "keyPasses",
    "accurateFinalThirdPasses", "accuratePassesPercentage", "accuratePasses",
    "accurateLongBalls", "accurateLongBallsPercentage", "bigChancesCreated",
    "bigChancesMissed", "totalShots", "shotsOnTarget", "blockedShots",
    "successfulDribbles", "successfulDribblesPercentage", "tackles",
    "interceptions", "clearances", "ballRecovery", "groundDuelsWon",
    "groundDuelsWonPercentage", "aerialDuelsWon", "aerialDuelsWonPercentage",
    "totalDuelsWon", "totalDuelsWonPercentage", "wasFouled", "fouls",
    "dispossessed", "possesionLost", "saves", "cleanSheets",
    "highClaims", "errorLeadToGoal", "errorLeadToShot", "passToAssist",
]

class SofaScoreError(RuntimeError):
    pass


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3, connect=3, read=3, backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.sofascore.com/",
    })
    return s


class SofaScoreClient:
    """Replaceable adapter for public web endpoints used by SofaScore.

    These are not a contracted/open-data API. They are used only as a pragmatic
    prototype source and every call is isolated here so the provider can be
    swapped without rewriting the Streamlit UI or analytics layer.
    """

    def __init__(self, timeout: int = 18):
        self.timeout = timeout
        self.http = _session()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{BASE}/{path.lstrip('/')}"
        try:
            r = self.http.get(url, params=params or {}, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and data.get("error"):
                raise SofaScoreError(str(data.get("error")))
            return data
        except SofaScoreError:
            raise
        except Exception as exc:
            raise SofaScoreError(f"Falha ao consultar SofaScore ({url}): {exc}") from exc

    def seasons(self, tournament_id: int) -> list[dict]:
        return self._get(f"unique-tournament/{tournament_id}/seasons").get("seasons", []) or []

    def season_id(self, tournament_id: int, year: int) -> int:
        seasons = self.seasons(tournament_id)
        candidates = []
        for season in seasons:
            label = str(season.get("year") or season.get("name") or "")
            if label == str(year) or label.startswith(str(year)) or str(year) in label:
                candidates.append(season)
        if not candidates:
            available = ", ".join(str(x.get("year") or x.get("name")) for x in seasons[:8])
            raise SofaScoreError(f"Temporada {year} não encontrada. Disponíveis: {available or 'nenhuma'}")
        return int(candidates[0]["id"])

    def league_statistics_raw(
        self,
        tournament_id: int,
        season_id: int,
        accumulation: str = "per90",
        page_limit: int = 100,
        max_pages: int = 20,
    ) -> list[dict]:
        fields = ",".join(PLAYER_FIELDS)
        rows: list[dict] = []
        offset = 0
        for _ in range(max_pages):
            payload = self._get(
                f"unique-tournament/{tournament_id}/season/{season_id}/statistics",
                {
                    "limit": page_limit,
                    "order": "-rating",
                    "offset": offset,
                    "accumulation": accumulation,
                    "fields": fields,
                    "filters": "position.in.G~D~M~F",
                },
            )
            batch = payload.get("results", []) or []
            rows.extend(batch)
            if not batch:
                break
            if payload.get("page") is not None and payload.get("pages") is not None:
                if int(payload.get("page")) >= int(payload.get("pages")):
                    break
            if len(batch) < page_limit:
                break
            offset += page_limit
        return rows

    def league_players(self, tournament_id: int, season_id: int, league_key: str, league_name: str) -> pd.DataFrame:
        per90 = self.league_statistics_raw(tournament_id, season_id, "per90")
        total = self.league_statistics_raw(tournament_id, season_id, "total")
        return normalize_league_players(per90, total, league_key, league_name, tournament_id, season_id)

    def player_profile(self, player_id: int) -> dict:
        return self._get(f"player/{int(player_id)}")

    def player_characteristics(self, player_id: int) -> dict:
        return self._get(f"player/{int(player_id)}/characteristics")

    def player_season_heatmap(self, player_id: int, tournament_id: int, season_id: int) -> pd.DataFrame:
        payload = self._get(
            f"player/{int(player_id)}/unique-tournament/{int(tournament_id)}/season/{int(season_id)}/heatmap/overall"
        )
        points = payload.get("points") or payload.get("heatmap") or []
        if not points:
            return pd.DataFrame(columns=["x", "y"])
        out = pd.DataFrame(points)
        if not {"x", "y"}.issubset(out.columns):
            return pd.DataFrame(columns=["x", "y"])
        return out[["x", "y"]].apply(pd.to_numeric, errors="coerce").dropna()


def _first_numeric(*values):
    for value in values:
        if isinstance(value, dict):
            value = value.get("value")
        try:
            if value is not None and value != "":
                return float(value)
        except (TypeError, ValueError):
            continue
    return math.nan


def _age_from_timestamp(ts) -> float:
    try:
        born = datetime.fromtimestamp(float(ts), tz=timezone.utc).date()
        today = datetime.now(tz=timezone.utc).date()
        return float(today.year - born.year - ((today.month, today.day) < (born.month, born.day)))
    except Exception:
        return math.nan


def _market_value_eur(player: dict) -> float:
    raw = player.get("proposedMarketValueRaw") or {}
    currency = raw.get("currency") or player.get("marketValueCurrency") or "EUR"
    value = _first_numeric(raw, player.get("proposedMarketValue"), player.get("marketValue"))
    if math.isnan(value):
        return value
    return value if str(currency).upper() == "EUR" else math.nan


def normalize_profile(payload: dict) -> dict:
    p = payload.get("player") or payload
    team = p.get("team") or payload.get("team") or {}
    country = p.get("country") or {}
    mv = _market_value_eur(p)
    return {
        "player_id": int(p.get("id")) if p.get("id") is not None else None,
        "player": p.get("name") or p.get("shortName") or "",
        "position": p.get("position") or "",
        "height_cm": _first_numeric(p.get("height")),
        "preferred_foot": p.get("preferredFoot") or "",
        "nationality": country.get("name") or country.get("alpha3") or "",
        "age": _age_from_timestamp(p.get("dateOfBirthTimestamp")),
        "club": team.get("name") or "",
        "team_id": str(team.get("id") or ""),
        "market_value_m": (mv / 1_000_000) if not math.isnan(mv) else math.nan,
    }


def _player_base(item: dict) -> dict:
    p = item.get("player") or {}
    t = item.get("team") or {}
    country = p.get("country") or {}
    mv = _market_value_eur(p)
    return {
        "player_id": int(p.get("id")) if p.get("id") is not None else None,
        "player": p.get("name") or p.get("shortName") or "",
        "club": t.get("name") or (p.get("team") or {}).get("name") or "",
        "team_id": str(t.get("id") or (p.get("team") or {}).get("id") or ""),
        "position": p.get("position") or item.get("position") or "",
        "nationality": country.get("name") or country.get("alpha3") or "",
        "age": _age_from_timestamp(p.get("dateOfBirthTimestamp")),
        "height_cm": _first_numeric(p.get("height")),
        "preferred_foot": p.get("preferredFoot") or "",
        "market_value_m": (mv / 1_000_000) if not math.isnan(mv) else math.nan,
    }


def normalize_league_players(
    per90_rows: list[dict],
    total_rows: list[dict],
    league_key: str,
    league_name: str,
    tournament_id: int,
    season_id: int,
) -> pd.DataFrame:
    total_by_id = {}
    for item in total_rows:
        pid = (item.get("player") or {}).get("id")
        if pid is not None:
            total_by_id[int(pid)] = item

    rows = []
    for item in per90_rows:
        base = _player_base(item)
        pid = base.get("player_id")
        if pid is None:
            continue
        total = total_by_id.get(int(pid), {})
        merged = dict(base)
        merged.update({
            "league_key": league_key,
            "league": league_name,
            "tournament_id": int(tournament_id),
            "season_id": int(season_id),
            "minutes": _first_numeric(total.get("minutesPlayed"), item.get("minutesPlayed")),
            "appearances": _first_numeric(total.get("appearances"), item.get("appearances")),
            "started": _first_numeric(total.get("started"), item.get("started")),
            "rating": _first_numeric(item.get("rating"), total.get("rating")),
            "goals90": _first_numeric(item.get("goals")),
            "assists90": _first_numeric(item.get("assists")),
            "xg90": _first_numeric(item.get("expectedGoals")),
            "xa90": _first_numeric(item.get("expectedAssists")),
            "key_pass90": _first_numeric(item.get("keyPasses")),
            "passes_final_third90": _first_numeric(item.get("accurateFinalThirdPasses")),
            "pass_accuracy_pct": _first_numeric(item.get("accuratePassesPercentage")),
            "long_balls90": _first_numeric(item.get("accurateLongBalls")),
            "big_chances_created90": _first_numeric(item.get("bigChancesCreated")),
            "tackles90": _first_numeric(item.get("tackles")),
            "interceptions90": _first_numeric(item.get("interceptions")),
            "recoveries90": _first_numeric(item.get("ballRecovery")),
            "clearances90": _first_numeric(item.get("clearances")),
            "duel_win_pct": _first_numeric(item.get("totalDuelsWonPercentage"), item.get("groundDuelsWonPercentage")),
            "aerial_win_pct": _first_numeric(item.get("aerialDuelsWonPercentage")),
            "dribbles90": _first_numeric(item.get("successfulDribbles")),
            "shots90": _first_numeric(item.get("totalShots")),
            "shots_on_target90": _first_numeric(item.get("shotsOnTarget")),
            "turnovers90": _first_numeric(item.get("possesionLost"), item.get("dispossessed")),
            "saves90": _first_numeric(item.get("saves")),
            "clean_sheets": _first_numeric(total.get("cleanSheets")),
        })
        rows.append(merged)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    numeric = [c for c in df.columns if c not in {"player","club","team_id","position","nationality","preferred_foot","league_key","league"}]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.drop_duplicates(["league_key", "player_id"]).reset_index(drop=True)
