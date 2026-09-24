from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from fotmob_analytics import DatasetBuilder, FotMobClient
from fotmob_analytics.client import player_image_url
from fotmob_analytics.details import fetch_detailed_stats


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
            "position": raw["position_group"].fillna(""),
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
            "assists90": [
                _per90(v, m) for v, m in zip(raw["goal_assist"], minutes)
            ],
            "xg_total": pd.to_numeric(raw["expected_goals"], errors="coerce"),
            "xg90": pd.to_numeric(raw["expected_goals_per_90"], errors="coerce"),
            "xa_total": pd.to_numeric(raw["expected_assists"], errors="coerce"),
            "xa90": pd.to_numeric(raw["expected_assists_per_90"], errors="coerce"),
            "xgot90": [
                _per90(v, m) for v, m in zip(raw["expected_goalsontarget"], minutes)
            ],
            "shots90": pd.to_numeric(raw["total_scoring_att"], errors="coerce"),
            "shots_on_target90": pd.to_numeric(raw["ontarget_scoring_att"], errors="coerce"),
            "passes90": pd.to_numeric(raw["accurate_pass"], errors="coerce"),
            "key_pass90": [
                _per90(v, m) for v, m in zip(raw["total_att_assist"], minutes)
            ],
            "chances_created90": [
                _per90(v, m) for v, m in zip(raw["total_att_assist"], minutes)
            ],
            "big_chances_created90": [
                _per90(v, m) for v, m in zip(raw["big_chance_created"], minutes)
            ],
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
            "goals_prevented90": [
                _per90(v, m) for v, m in zip(raw["_goals_prevented"], minutes)
            ],
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
    def __init__(self) -> None:
        self.client = FotMobClient(
            cache_ttl=6 * 3600,
            min_request_interval=0.22,
            timeout=20.0,
        )
        self.builder = DatasetBuilder(self.client, max_workers=4)

    def league_players(self, league_key: str, season: int) -> pd.DataFrame:
        meta = LEAGUES[league_key]
        raw = self.builder.league_player_table(
            meta["id"],
            season=str(season),
            stats=RAW_STATS,
        )
        return normalize_player_table(raw, league_key, meta["name"], meta["id"])

    def player_details(
        self,
        player_id: int,
        league_key: str,
        season_name: str | None = None,
    ) -> dict:
        meta = LEAGUES[league_key]
        player_data = self.client.player(int(player_id))
        detailed = fetch_detailed_stats(
            self.client,
            int(player_id),
            meta["id"],
            season_name=season_name,
            player_data=player_data,
        )

        result: dict[str, Any] = {
            "player_id": int(player_id),
            "image_url": player_image_url(int(player_id)),
            "stats": pd.DataFrame(),
            "shotmap": pd.DataFrame(),
        }
        if detailed is not None:
            result["stats"] = detailed.table.copy()
            if detailed.shotmap is not None:
                result["shotmap"] = detailed.shotmap.copy()
            result["resolved_season"] = detailed.season
        return result
