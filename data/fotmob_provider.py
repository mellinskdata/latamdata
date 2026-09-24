from __future__ import annotations

import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://www.fotmob.com/api/data"
IMAGE_BASE = "https://images.fotmob.com/image_resources/playerimages"

LEAGUES = {
    "bra_a": {"id": 268, "name": "Brasileirão Série A"},
    "bra_b": {"id": 8814, "name": "Brasileirão Série B"},
    "arg_a": {"id": 112, "name": "Liga Profesional Argentina"},
}

RAW_STATS = [
    "mins_played",
    "rating",
    "goals",
    "goal_assist",
    "goals_per_90",
    "expected_goals",
    "expected_goals_per_90",
    "expected_goalsontarget",
    "ontarget_scoring_att",
    "total_scoring_att",
    "accurate_pass",
    "big_chance_created",
    "total_att_assist",
    "accurate_long_balls",
    "expected_assists",
    "expected_assists_per_90",
    "won_contest",
    "big_chance_missed",
    "defensive_contributions",
    "total_tackle",
    "interception",
    "effective_clearance",
    "outfielder_block",
    "ball_recovery",
    "poss_won_att_3rd",
    "clean_sheet",
    "_save_percentage",
    "saves",
    "_goals_prevented",
    "goals_conceded",
    "fouls",
    "yellow_card",
    "red_card",
]

POSITION_ID_GROUP = {
    11: "GK",
    32: "FB", 38: "FB", 62: "FB", 68: "FB",
    33: "CB", 34: "CB", 35: "CB", 36: "CB", 37: "CB",
    63: "DM", 64: "DM", 65: "DM", 66: "DM", 67: "DM",
    71: "W", 72: "W", 78: "W", 79: "W",
    73: "CM", 74: "CM", 75: "CM", 76: "CM", 77: "CM",
    82: "W", 83: "W", 87: "W", 88: "W", 102: "W", 103: "W", 107: "W", 108: "W",
    84: "AM", 85: "AM", 86: "AM",
    104: "ST", 105: "ST", 106: "ST", 114: "ST", 115: "ST", 116: "ST",
}

DETAILED_KEYS = {
    "goals": "goals",
    "expected_goals": "xG",
    "expected_goals_on_target": "xGOT",
    "non_penalty_xg": "npxG",
    "shots": "Finalizações",
    "ShotsOnTarget": "No alvo",
    "assists": "Assistências",
    "expected_assists": "xA",
    "successful_passes": "Passes certos",
    "successful_passes_accuracy": "Precisão de passe",
    "long_balls_accurate": "Bolas longas certas",
    "chances_created": "Chances criadas",
    "big_chance_created_team_title": "Grandes chances criadas",
    "crosses_succeeeded": "Cruzamentos certos",
    "dribbles_succeeded": "Dribles certos",
    "duel_won": "Duelos vencidos",
    "duel_won_percent": "Duelos vencidos %",
    "aerials_won": "Duelos aéreos vencidos",
    "aerials_won_percent": "Duelos aéreos %",
    "touches_opp_box": "Toques na área adversária",
    "dispossessed": "Perdas por desarme",
    "defensive_actions": "Ações defensivas",
    "matchstats.headers.tackles": "Desarmes",
    "interceptions": "Interceptações",
    "blocked_shots": "Bloqueios",
    "recoveries": "Recuperações",
    "poss_won_att_3rd_team_title": "Recuperações no terço final",
    "clearances": "Cortes",
    "saves": "Defesas",
    "save_percentage": "Defesas %",
    "goals_prevented": "Gols evitados",
    "goals_conceded": "Gols sofridos",
    "clean_sheet_team_title": "Clean sheets",
}


class FotMobError(RuntimeError):
    pass


def _num(value: Any) -> float:
    try:
        if value is None or pd.isna(value):
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _per90(total: Any, minutes: Any) -> float:
    total_value = _num(total)
    minute_value = _num(minutes)
    if math.isnan(total_value) or math.isnan(minute_value) or minute_value <= 0:
        return math.nan
    return total_value * 90.0 / minute_value


def _market_millions(value: Any) -> float:
    raw = _num(value)
    if math.isnan(raw) or raw <= 0:
        return math.nan
    return raw / 1_000_000.0


def _stat_value(entry: dict) -> float:
    value = entry.get("statValue")
    if isinstance(value, dict):
        value = value.get("value")
    return _num(value)


def _position_from_label(label: Any) -> str | None:
    if not isinstance(label, str) or not label.strip():
        return None
    primary = label.split(",")[0].strip().upper()
    return {
        "GK": "GK",
        "CB": "CB",
        "RB": "FB", "LB": "FB", "RWB": "FB", "LWB": "FB",
        "CDM": "DM", "DM": "DM",
        "CM": "CM",
        "CAM": "AM", "AM": "AM",
        "RW": "W", "LW": "W", "RM": "W", "LM": "W",
        "ST": "ST", "CF": "ST",
    }.get(primary)


def _position_from_id(value: Any) -> str | None:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    if pid in POSITION_ID_GROUP:
        return POSITION_ID_GROUP[pid]
    if pid in (0, 1, 11):
        return "GK"
    if 30 <= pid <= 39:
        return "CB" if 33 <= pid <= 37 else "FB"
    if 60 <= pid <= 69:
        return "DM"
    if 70 <= pid <= 79:
        return "W" if pid in (71, 72, 78, 79) else "CM"
    if 80 <= pid <= 89:
        return "AM"
    if 100 <= pid <= 119:
        return "ST"
    return None


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out:
            out[col] = np.nan
    return out


def normalize_player_table(
    raw: pd.DataFrame,
    league_key: str,
    league_name: str,
    league_id: int,
) -> pd.DataFrame:
    if raw.empty:
        return raw

    raw = _ensure_columns(
        raw,
        [
            "player_id", "name", "team", "team_id", "position_group",
            "position_label", "season_id", "season", "age", "country",
            "height", "market_value",
        ] + RAW_STATS,
    )
    minutes = pd.to_numeric(raw["mins_played"], errors="coerce")

    out = pd.DataFrame(
        {
            "player_id": pd.to_numeric(raw["player_id"], errors="coerce"),
            "player": raw["name"].fillna(""),
            "club": raw["team"].fillna(""),
            "team_id": raw["team_id"].astype("string"),
            "position": raw["position_group"].fillna("UNK"),
            "position_label": raw["position_label"].fillna(""),
            "league_key": league_key,
            "league": league_name,
            "fotmob_league_id": int(league_id),
            "season_id": pd.to_numeric(raw["season_id"], errors="coerce"),
            "season": raw["season"].astype("string"),
            "age": pd.to_numeric(raw["age"], errors="coerce"),
            "nationality": raw["country"].fillna(""),
            "height_cm": pd.to_numeric(raw["height"], errors="coerce"),
            "market_value_m": raw["market_value"].map(_market_millions),
            "minutes": minutes,
            "rating": pd.to_numeric(raw["rating"], errors="coerce"),
            "goals_total": pd.to_numeric(raw["goals"], errors="coerce"),
            "assists_total": pd.to_numeric(raw["goal_assist"], errors="coerce"),
            "goals90": pd.to_numeric(raw["goals_per_90"], errors="coerce"),
            "assists90": [_per90(v, m) for v, m in zip(raw["goal_assist"], minutes)],
            "xg_total": pd.to_numeric(raw["expected_goals"], errors="coerce"),
            "xg90": pd.to_numeric(raw["expected_goals_per_90"], errors="coerce"),
            "xa_total": pd.to_numeric(raw["expected_assists"], errors="coerce"),
            "xa90": pd.to_numeric(raw["expected_assists_per_90"], errors="coerce"),
            "xgot90": [_per90(v, m) for v, m in zip(raw["expected_goalsontarget"], minutes)],
            "shots90": pd.to_numeric(raw["total_scoring_att"], errors="coerce"),
            "shots_on_target90": pd.to_numeric(raw["ontarget_scoring_att"], errors="coerce"),
            "passes90": pd.to_numeric(raw["accurate_pass"], errors="coerce"),
            "key_pass90": [_per90(v, m) for v, m in zip(raw["total_att_assist"], minutes)],
            "chances_created90": [_per90(v, m) for v, m in zip(raw["total_att_assist"], minutes)],
            "big_chances_created90": [_per90(v, m) for v, m in zip(raw["big_chance_created"], minutes)],
            "big_chances_missed": pd.to_numeric(raw["big_chance_missed"], errors="coerce"),
            "long_balls90": pd.to_numeric(raw["accurate_long_balls"], errors="coerce"),
            "dribbles90": pd.to_numeric(raw["won_contest"], errors="coerce"),
            "defensive_actions90": pd.to_numeric(raw["defensive_contributions"], errors="coerce"),
            "tackles90": pd.to_numeric(raw["total_tackle"], errors="coerce"),
            "interceptions90": pd.to_numeric(raw["interception"], errors="coerce"),
            "clearances90": pd.to_numeric(raw["effective_clearance"], errors="coerce"),
            "blocks90": pd.to_numeric(raw["outfielder_block"], errors="coerce"),
            "recoveries90": pd.to_numeric(raw["ball_recovery"], errors="coerce"),
            "high_press_wins90": pd.to_numeric(raw["poss_won_att_3rd"], errors="coerce"),
            "clean_sheets": pd.to_numeric(raw["clean_sheet"], errors="coerce"),
            "save_pct": pd.to_numeric(raw["_save_percentage"], errors="coerce"),
            "saves90": pd.to_numeric(raw["saves"], errors="coerce"),
            "goals_prevented90": [_per90(v, m) for v, m in zip(raw["_goals_prevented"], minutes)],
            "goals_conceded90": pd.to_numeric(raw["goals_conceded"], errors="coerce"),
            "fouls90": pd.to_numeric(raw["fouls"], errors="coerce"),
            "yellow_cards": pd.to_numeric(raw["yellow_card"], errors="coerce"),
            "red_cards": pd.to_numeric(raw["red_card"], errors="coerce"),
        }
    )

    out = out.dropna(subset=["player_id"]).copy()
    out["player_id"] = out["player_id"].astype(int)
    out["position"] = out["position"].replace("", "UNK")
    return out.drop_duplicates(["league_key", "player_id"]).reset_index(drop=True)


class FotMobProvider:
    def __init__(self, timeout: float = 20.0, min_request_interval: float = .16) -> None:
        self.timeout = timeout
        self.min_request_interval = min_request_interval
        self._local = threading.local()
        self._rate_lock = threading.Lock()
        self._next_request_at = 0.0
        self._season_cache: dict[int, list[dict]] = {}
        self._team_cache: dict[int, dict] = {}

    @property
    def session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            retry = Retry(
                total=3,
                connect=3,
                read=3,
                backoff_factor=.8,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=("GET",),
                respect_retry_after_header=True,
            )
            session.mount("https://", HTTPAdapter(max_retries=retry))
            session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                    "Accept": "application/json,text/plain,*/*",
                    "Referer": "https://www.fotmob.com/",
                }
            )
            self._local.session = session
        return session

    def _throttle(self) -> None:
        with self._rate_lock:
            now = time.monotonic()
            wait = self._next_request_at - now
            self._next_request_at = max(now, self._next_request_at) + self.min_request_interval
        if wait > 0:
            time.sleep(wait)

    def _get(self, path: str, **params: Any) -> dict:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        url = f"{BASE_URL}/{path}"
        if query:
            url = f"{url}?{query}"

        last_error = None
        for attempt in range(3):
            self._throttle()
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 429:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise FotMobError(f"Resposta inválida do FotMob: {url}")
                return data
            except Exception as exc:
                last_error = exc
                time.sleep(.5 * (attempt + 1))
        raise FotMobError(f"Falha ao consultar FotMob ({url}): {last_error}")

    def league(self, league_id: int) -> dict:
        return self._get("leagues", id=int(league_id))

    def team(self, team_id: int) -> dict:
        team_id = int(team_id)
        if team_id not in self._team_cache:
            self._team_cache[team_id] = self._get("teams", id=team_id)
        return self._team_cache[team_id]

    def player(self, player_id: int) -> dict:
        return self._get("playerData", id=int(player_id))

    def league_seasons(self, league_id: int) -> list[dict]:
        league_id = int(league_id)
        if league_id in self._season_cache:
            return self._season_cache[league_id]

        payload = self.league(league_id)
        links = (payload.get("stats") or {}).get("seasonStatLinks") or []
        seasons = [
            {"id": item.get("TournamentId"), "name": str(item.get("Name") or "")}
            for item in links
            if item.get("TournamentId") is not None
        ]

        if not seasons:
            probe = self._get(
                "leagueseasondeepstats",
                id=league_id,
                season=0,
                type="players",
                stat="rating",
            )
            seasons = [
                {"id": item.get("id"), "name": str(item.get("name") or "")}
                for item in probe.get("seasons", [])
                if item.get("leagueId") in (None, league_id) and item.get("id")
            ]

        self._season_cache[league_id] = seasons
        return seasons

    def resolve_season(self, league_id: int, season: int | str) -> tuple[int, str]:
        target = str(season).strip()
        seasons = self.league_seasons(league_id)
        for item in seasons:
            name = str(item.get("name") or "").strip()
            if name == target or name.startswith(target) or target in name:
                return int(item["id"]), name

        try:
            sid = int(season)
            for item in seasons:
                if int(item["id"]) == sid:
                    return sid, str(item.get("name") or sid)
        except (TypeError, ValueError):
            pass

        available = ", ".join(str(item.get("name")) for item in seasons[:8])
        raise FotMobError(
            f"Temporada {season} não encontrada para a liga {league_id}. "
            f"Disponíveis: {available or 'nenhuma'}"
        )

    def deep_stat(self, league_id: int, season_id: int, stat: str) -> list[dict]:
        payload = self._get(
            "leagueseasondeepstats",
            id=int(league_id),
            season=int(season_id),
            type="players",
            stat=stat,
        )
        return payload.get("statsData", []) or []

    def _squad_records(self, team_id: int) -> list[dict]:
        try:
            payload = self.team(team_id)
        except Exception:
            return []

        details = payload.get("details") or {}
        team_name = details.get("shortName") or details.get("name") or ""
        records = []

        for group in (payload.get("squad") or {}).get("squad") or []:
            if str(group.get("title") or "").lower() == "coach":
                continue
            for member in group.get("members") or []:
                player_id = member.get("id")
                if player_id is None:
                    continue
                label = member.get("positionIdsDesc") or ""
                records.append(
                    {
                        "player_id": int(player_id),
                        "team": team_name,
                        "age": member.get("age"),
                        "height": member.get("height"),
                        "country": member.get("cname") or member.get("ccode") or "",
                        "market_value": member.get("transferValue"),
                        "position_label": label,
                        "position_group": (
                            _position_from_label(label)
                            or _position_from_id(member.get("positionIds"))
                            or _position_from_id(member.get("positionId"))
                        ),
                    }
                )
        return records

    def _raw_league_table(self, league_id: int, season: int) -> pd.DataFrame:
        season_id, season_name = self.resolve_season(league_id, season)

        def fetch(stat: str):
            try:
                return stat, self.deep_stat(league_id, season_id, stat)
            except Exception:
                return stat, []

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(fetch, RAW_STATS))

        rows: dict[int, dict] = {}
        for stat, entries in results:
            for entry in entries:
                player_id = entry.get("id")
                if player_id is None:
                    continue
                player_id = int(player_id)
                row = rows.setdefault(
                    player_id,
                    {
                        "player_id": player_id,
                        "name": entry.get("name") or "",
                        "team_id": entry.get("teamId"),
                        "position_id": entry.get("position"),
                        "season_id": season_id,
                        "season": season_name,
                    },
                )
                row[stat] = _stat_value(entry)
                if row.get("team_id") is None and entry.get("teamId") is not None:
                    row["team_id"] = entry.get("teamId")
                if row.get("position_id") is None and entry.get("position") is not None:
                    row["position_id"] = entry.get("position")

        frame = pd.DataFrame(list(rows.values()))
        if frame.empty:
            return frame

        for stat in RAW_STATS:
            if stat not in frame:
                frame[stat] = np.nan

        team_ids = sorted(
            {
                int(team_id)
                for team_id in frame["team_id"].dropna().tolist()
                if str(team_id).strip()
            }
        )
        with ThreadPoolExecutor(max_workers=4) as pool:
            batches = list(pool.map(self._squad_records, team_ids))
        squad = pd.DataFrame([record for batch in batches for record in batch])

        if not squad.empty:
            squad = squad.drop_duplicates("player_id", keep="first")
            frame = frame.merge(squad, on="player_id", how="left")
        else:
            for col in [
                "team", "age", "height", "country", "market_value",
                "position_label", "position_group",
            ]:
                frame[col] = np.nan

        fallback = frame["position_id"].map(_position_from_id)
        frame["position_group"] = frame["position_group"].fillna(fallback)
        return frame

    def league_players(self, league_key: str, season: int) -> pd.DataFrame:
        meta = LEAGUES[league_key]
        raw = self._raw_league_table(meta["id"], season)
        return normalize_player_table(
            raw,
            league_key,
            meta["name"],
            meta["id"],
        )

    def _resolve_player_entry(
        self,
        player_data: dict,
        league_id: int,
        season_name: str | None,
    ) -> tuple[str, str] | None:
        candidates = player_data.get("statSeasons") or []

        if season_name:
            normalized = str(season_name).strip()
            ordered = sorted(
                candidates,
                key=lambda item: str(item.get("seasonName") or "") != normalized,
            )
        else:
            ordered = candidates

        for season in ordered:
            name = str(season.get("seasonName") or "")
            if season_name and normalized not in name and name not in normalized:
                continue
            for tournament in season.get("tournaments") or []:
                if int(tournament.get("tournamentId") or -1) == int(league_id):
                    entry_id = tournament.get("entryId")
                    if entry_id:
                        return str(entry_id), name

        if season_name:
            for season in candidates:
                for tournament in season.get("tournaments") or []:
                    if int(tournament.get("tournamentId") or -1) == int(league_id):
                        entry_id = tournament.get("entryId")
                        if entry_id:
                            return str(entry_id), str(season.get("seasonName") or "")
        return None

    def _parse_player_stats(self, payload: dict) -> pd.DataFrame:
        records = []
        section = payload.get("statsSection") or {}
        for group in section.get("items") or []:
            group_title = group.get("title") or ""
            for item in group.get("items") or []:
                raw_key = item.get("localizedTitleId")
                title = item.get("title") or DETAILED_KEYS.get(raw_key) or raw_key or ""
                percentile = item.get("percentileRankPer90")
                if percentile is None:
                    percentile = item.get("percentileRank")
                records.append(
                    {
                        "group": group_title,
                        "title": title,
                        "key": raw_key,
                        "value": _num(item.get("statValue")),
                        "per90": _num(item.get("per90")),
                        "percentile": _num(percentile),
                    }
                )
        return pd.DataFrame(records)

    def _parse_shotmap(self, payload: dict) -> pd.DataFrame:
        records = []
        for shot in payload.get("shotmap") or []:
            if shot.get("isOwnGoal"):
                continue
            records.append(
                {
                    "x": shot.get("x"),
                    "y": shot.get("y"),
                    "xg": shot.get("expectedGoals") or 0,
                    "event": shot.get("eventType"),
                    "shot_type": shot.get("shotType"),
                    "situation": shot.get("situation"),
                    "minute": shot.get("min"),
                    "on_target": bool(shot.get("isOnTarget")),
                }
            )
        return pd.DataFrame(records)

    def player_details(
        self,
        player_id: int,
        league_key: str,
        season_name: str | None = None,
    ) -> dict:
        meta = LEAGUES[league_key]
        player_data = self.player(int(player_id))
        entry = self._resolve_player_entry(
            player_data,
            meta["id"],
            season_name,
        )

        result = {
            "player_id": int(player_id),
            "image_url": f"{IMAGE_BASE}/{int(player_id)}.png",
            "stats": pd.DataFrame(),
            "shotmap": pd.DataFrame(),
        }
        if entry is None:
            return result

        entry_id, resolved_season = entry
        payload = self._get(
            "playerStats",
            playerId=int(player_id),
            seasonId=entry_id,
        )
        result["stats"] = self._parse_player_stats(payload)
        result["shotmap"] = self._parse_shotmap(payload)
        result["resolved_season"] = resolved_season
        return result
