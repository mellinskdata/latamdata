from __future__ import annotations

import math
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


SCOUT_METRICS = [
    "rating",
    "goals90", "assists90", "xg90", "xa90", "xgot90",
    "shots90", "shots_on_target90",
    "passes90", "key_pass90", "chances_created90",
    "big_chances_created90", "long_balls90", "dribbles90",
    "defensive_actions90", "tackles90", "interceptions90",
    "recoveries90", "clearances90", "blocks90", "high_press_wins90",
    "save_pct", "saves90", "goals_prevented90", "goals_conceded90",
    "fouls90",
]

LOWER_IS_BETTER = {"goals_conceded90", "fouls90"}

LABELS = {
    "rating": "Nota média",
    "goals90": "Gols / 90",
    "assists90": "Assistências / 90",
    "xg90": "xG / 90",
    "xa90": "xA / 90",
    "xgot90": "xGOT / 90",
    "shots90": "Finalizações / 90",
    "shots_on_target90": "Finalizações no alvo / 90",
    "passes90": "Passes certos / 90",
    "key_pass90": "Chances criadas / 90",
    "chances_created90": "Chances criadas / 90",
    "big_chances_created90": "Grandes chances criadas / 90",
    "long_balls90": "Bolas longas certas / 90",
    "dribbles90": "Dribles certos / 90",
    "defensive_actions90": "Ações defensivas / 90",
    "tackles90": "Desarmes / 90",
    "interceptions90": "Interceptações / 90",
    "recoveries90": "Recuperações / 90",
    "clearances90": "Cortes / 90",
    "blocks90": "Bloqueios / 90",
    "high_press_wins90": "Posse recuperada no terço final / 90",
    "save_pct": "Defesas %",
    "saves90": "Defesas / 90",
    "goals_prevented90": "Gols evitados / 90",
    "goals_conceded90": "Gols sofridos / 90",
    "fouls90": "Disciplina",
}

DIMENSIONS = {
    "Finalização": ["xg90", "goals90", "xgot90", "shots_on_target90"],
    "Criação": ["xa90", "key_pass90", "big_chances_created90"],
    "Posse": ["passes90", "long_balls90", "dribbles90"],
    "Defesa": [
        "defensive_actions90", "tackles90", "interceptions90",
        "recoveries90", "clearances90", "blocks90", "high_press_wins90",
    ],
    "Goleiro": ["save_pct", "saves90", "goals_prevented90", "goals_conceded90"],
}

RADAR_METRICS = {
    "Finalização": "dimension_finishing",
    "Criação": "dimension_creation",
    "Posse": "dimension_possession",
    "Defesa": "dimension_defense",
    "Impacto": "performance_score",
    "Confiabilidade": "reliability_score",
}

ROLE_WEIGHTS = {
    "GK": {
        "save_pct": 1.5, "goals_prevented90": 1.5, "goals_conceded90": 1.2,
        "saves90": .8, "passes90": .5, "long_balls90": .5, "rating": .8,
    },
    "CB": {
        "interceptions90": 1.25, "clearances90": 1.0, "blocks90": 1.0,
        "tackles90": .9, "recoveries90": .8, "defensive_actions90": 1.1,
        "passes90": .8, "long_balls90": .7, "rating": .6,
    },
    "FB": {
        "tackles90": 1.0, "interceptions90": .9, "recoveries90": .7,
        "xa90": .9, "key_pass90": .8, "dribbles90": .8,
        "passes90": .6, "long_balls90": .5, "rating": .6,
    },
    "DM": {
        "tackles90": 1.1, "interceptions90": 1.2, "recoveries90": 1.15,
        "defensive_actions90": 1.0, "passes90": .9, "long_balls90": .7,
        "high_press_wins90": .6, "xa90": .35, "rating": .6,
    },
    "CM": {
        "passes90": 1.0, "xa90": .9, "key_pass90": .8, "long_balls90": .65,
        "recoveries90": .8, "tackles90": .55, "interceptions90": .55,
        "dribbles90": .55, "xg90": .35, "rating": .6,
    },
    "AM": {
        "xa90": 1.25, "key_pass90": 1.1, "big_chances_created90": 1.0,
        "xg90": .85, "goals90": .65, "dribbles90": .7,
        "passes90": .55, "rating": .6,
    },
    "W": {
        "xa90": 1.0, "key_pass90": .9, "dribbles90": 1.15,
        "xg90": 1.0, "goals90": .85, "shots_on_target90": .65,
        "big_chances_created90": .8, "high_press_wins90": .4, "rating": .6,
    },
    "ST": {
        "xg90": 1.35, "goals90": 1.2, "xgot90": 1.0,
        "shots_on_target90": .9, "shots90": .55, "xa90": .55,
        "key_pass90": .45, "high_press_wins90": .35, "rating": .6,
    },
}


def _mean_percentiles(row: pd.Series, metrics: list[str]) -> float:
    values = []
    for metric in metrics:
        value = row.get(f"pct_{metric}")
        if pd.notna(value):
            values.append(float(value))
    return round(float(np.mean(values)), 1) if values else np.nan


def add_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out

    for _, group in out.groupby("position", dropna=False):
        idx = group.index
        for metric in SCOUT_METRICS:
            if metric not in group.columns:
                continue
            series = pd.to_numeric(group[metric], errors="coerce")
            if series.notna().sum() < 3:
                continue
            pct = series.rank(pct=True, method="average") * 100
            if metric in LOWER_IS_BETTER:
                pct = 100 - pct + 100 / max(series.notna().sum(), 1)
            out.loc[idx, f"pct_{metric}"] = pct.clip(0, 100)

    if "market_value_m" in out:
        market = pd.to_numeric(out["market_value_m"], errors="coerce")
        if market.notna().sum() >= 3:
            out["pct_market_value_m"] = market.rank(pct=True) * 100

    return out


def add_dimension_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out

    mapping = {
        "dimension_finishing": DIMENSIONS["Finalização"],
        "dimension_creation": DIMENSIONS["Criação"],
        "dimension_possession": DIMENSIONS["Posse"],
        "dimension_defense": DIMENSIONS["Defesa"],
        "dimension_goalkeeping": DIMENSIONS["Goleiro"],
    }
    for column, metrics in mapping.items():
        out[column] = out.apply(lambda row: _mean_percentiles(row, metrics), axis=1)
    return out


def add_performance_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    scores = []

    for _, row in out.iterrows():
        weights = ROLE_WEIGHTS.get(str(row.get("position", "")), {})
        weighted = []
        total_weight = 0.0
        for metric, weight in weights.items():
            pct = row.get(f"pct_{metric}")
            if pd.notna(pct):
                weighted.append(float(pct) * float(weight))
                total_weight += float(weight)
        score = sum(weighted) / total_weight if total_weight else np.nan
        scores.append(round(float(score), 1) if pd.notna(score) else np.nan)

    out["performance_score"] = scores
    out["impact_score"] = out["performance_score"]
    return out


def add_reliability(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    minutes = pd.to_numeric(out.get("minutes"), errors="coerce").fillna(0).clip(lower=0)
    out["reliability_score"] = np.minimum(100, np.sqrt(minutes / 1800.0) * 100).round(1)
    return out


def add_value_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["value_score"] = np.nan

    valid = (
        out["market_value_m"].notna()
        & (out["market_value_m"] > 0)
        & out["performance_score"].notna()
    )
    if valid.sum() >= 2:
        age = pd.to_numeric(out.loc[valid, "age"], errors="coerce").fillna(27)
        youth = np.where(age <= 21, 1.18, np.where(age <= 24, 1.10, np.where(age <= 28, 1.0, .90)))
        raw = (
            out.loc[valid, "performance_score"].to_numpy()
            * youth
            / np.sqrt(out.loc[valid, "market_value_m"].clip(lower=.15).to_numpy())
        )
        lo, hi = float(np.nanmin(raw)), float(np.nanmax(raw))
        score = np.full(len(raw), 50.0) if hi - lo < 1e-9 else (raw - lo) / (hi - lo) * 100
        out.loc[valid, "value_score"] = np.round(score, 1)

    return out


def add_opportunity_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ages = pd.to_numeric(out.get("age"), errors="coerce")

    def age_score(age):
        if pd.isna(age):
            return 50.0
        if age <= 20:
            return 100.0
        if age <= 22:
            return 90.0
        if age <= 24:
            return 78.0
        if age <= 27:
            return 58.0
        if age <= 30:
            return 38.0
        return 22.0

    youth = ages.map(age_score)
    cheap = 100 - out.get("pct_market_value_m", pd.Series(np.nan, index=out.index))
    opportunity = (
        out["performance_score"].fillna(50) * .50
        + youth.fillna(50) * .25
        + cheap.fillna(50) * .15
        + out["reliability_score"].fillna(50) * .10
    )
    out["opportunity_score"] = opportunity.clip(0, 100).round(1)
    return out


def archetype(row: pd.Series) -> str:
    position = str(row.get("position", ""))
    pct = lambda metric: float(row.get(f"pct_{metric}", 0) or 0)

    if position == "GK":
        if max(pct("save_pct"), pct("goals_prevented90")) >= 75:
            return "Shot stopper"
        if max(pct("passes90"), pct("long_balls90")) >= 75:
            return "Goleiro construtor"
        return "Goleiro equilibrado"

    if position == "CB":
        if max(pct("passes90"), pct("long_balls90")) >= 75:
            return "Zagueiro construtor"
        if max(pct("clearances90"), pct("blocks90"), pct("interceptions90")) >= 75:
            return "Stopper"
        return "Zagueiro equilibrado"

    if position == "FB":
        if max(pct("xa90"), pct("key_pass90"), pct("dribbles90")) >= 75:
            return "Lateral ofensivo"
        if max(pct("tackles90"), pct("interceptions90")) >= 75:
            return "Lateral defensivo"
        return "Lateral equilibrado"

    if position == "DM":
        if max(pct("passes90"), pct("long_balls90")) >= 75 and max(pct("interceptions90"), pct("recoveries90")) >= 60:
            return "Volante construtor"
        if max(pct("tackles90"), pct("interceptions90"), pct("recoveries90")) >= 75:
            return "Volante recuperador"
        return "Volante equilibrado"

    if position == "CM":
        if max(pct("xa90"), pct("key_pass90"), pct("passes90")) >= 75:
            return "Organizador"
        if max(pct("recoveries90"), pct("tackles90")) >= 70 and max(pct("xg90"), pct("xa90")) >= 55:
            return "Box-to-box"
        return "Meio-campista equilibrado"

    if position == "AM":
        if max(pct("xa90"), pct("key_pass90"), pct("big_chances_created90")) >= 75:
            return "Criador entrelinhas"
        if max(pct("xg90"), pct("goals90")) >= 75:
            return "Meia finalizador"
        return "Meia ofensivo híbrido"

    if position == "W":
        if pct("dribbles90") >= 75:
            return "Extremo driblador"
        if max(pct("xa90"), pct("key_pass90")) >= 75:
            return "Criador de lado"
        if max(pct("xg90"), pct("goals90")) >= 75:
            return "Inside forward"
        return "Extremo equilibrado"

    if position == "ST":
        if max(pct("xg90"), pct("goals90"), pct("xgot90")) >= 75:
            return "Finalizador"
        if max(pct("xa90"), pct("key_pass90")) >= 70:
            return "9 associativo"
        if pct("high_press_wins90") >= 75:
            return "Pressing forward"
        return "Atacante móvel"

    return "Perfil híbrido"


def add_archetypes(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["archetype"] = out.apply(archetype, axis=1)
    return out


def prepare_players(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = add_percentiles(df)
    out = add_dimension_scores(out)
    out = add_performance_score(out)
    out = add_reliability(out)
    out = add_value_score(out)
    out = add_opportunity_score(out)
    out = add_archetypes(out)
    return out


def similar_players(
    df: pd.DataFrame,
    player_id: int,
    league_key: str | None = None,
    n: int = 8,
) -> pd.DataFrame:
    target_mask = df["player_id"].astype(str) == str(player_id)
    if league_key is not None:
        target_mask &= df["league_key"].eq(league_key)
    target_rows = df[target_mask]
    if target_rows.empty:
        return pd.DataFrame()

    target = target_rows.iloc[0]
    pool = df[
        (df["position"] == target["position"])
        & ~(
            (df["player_id"].astype(str) == str(player_id))
            & (df["league_key"] == target["league_key"])
        )
        & (df["minutes"].fillna(0) >= 450)
    ].copy()
    if pool.empty:
        return pool

    metrics = list(ROLE_WEIGHTS.get(str(target["position"]), {}).keys())
    features = [
        metric for metric in metrics
        if metric in df.columns and df[metric].notna().sum() >= 8
    ]
    if len(features) < 3:
        features = [
            metric for metric in SCOUT_METRICS
            if metric in df.columns and df[metric].notna().sum() >= 8
        ]
    if not features:
        return pd.DataFrame()

    combo = pd.concat(
        [target_rows.iloc[[0]][features], pool[features]],
        ignore_index=True,
    )
    combo = combo.apply(pd.to_numeric, errors="coerce")
    combo = combo.fillna(combo.median(numeric_only=True)).fillna(0)

    z = StandardScaler().fit_transform(combo)
    model = NearestNeighbors(metric="cosine")
    model.fit(z[1:])
    distances, indices = model.kneighbors(
        z[0].reshape(1, -1),
        n_neighbors=min(n, len(pool)),
    )

    result = pool.iloc[indices[0]].copy()
    result["similarity"] = ((1 - distances[0]) * 100).clip(0, 100).round(1)
    return result.sort_values("similarity", ascending=False)


def strengths_weaknesses(row: pd.Series, top_n: int = 4):
    pairs = []
    for metric, label in LABELS.items():
        key = f"pct_{metric}"
        if key in row.index and pd.notna(row.get(key)):
            pairs.append((label, float(row[key])))
    pairs.sort(key=lambda item: item[1], reverse=True)
    if not pairs:
        return [], []
    return pairs[:top_n], list(reversed(pairs[-top_n:]))


def player_signals(row: pd.Series) -> list[str]:
    signals = []

    goals90 = row.get("goals90")
    xg90 = row.get("xg90")
    if pd.notna(goals90) and pd.notna(xg90):
        diff = float(goals90) - float(xg90)
        if diff >= .10:
            signals.append(f"Finalização acima do xG (+{diff:.2f} gol/90).")
        elif diff <= -.10:
            signals.append(f"Produção de gols abaixo do xG ({diff:.2f} gol/90).")

    assists90 = row.get("assists90")
    xa90 = row.get("xa90")
    if pd.notna(assists90) and pd.notna(xa90):
        diff = float(assists90) - float(xa90)
        if diff >= .10:
            signals.append(f"Assistências acima do xA (+{diff:.2f}/90).")
        elif diff <= -.10:
            signals.append(f"Assistências abaixo do xA ({diff:.2f}/90).")

    if float(row.get("reliability_score", 0) or 0) >= 80:
        signals.append("Amostra de minutos robusta para comparação.")
    elif float(row.get("reliability_score", 0) or 0) < 55:
        signals.append("Amostra de minutos pequena: interpretar percentis com cautela.")

    if float(row.get("pct_high_press_wins90", 0) or 0) >= 80:
        signals.append("Destaque na recuperação de posse no terço final.")
    if float(row.get("pct_big_chances_created90", 0) or 0) >= 80:
        signals.append("Elite da posição em criação de grandes chances.")

    return signals[:5]


def team_form(matches: pd.DataFrame, team_id: str, last_n: int = 10) -> pd.DataFrame:
    if matches.empty:
        return matches
    m = matches[
        (matches.home_id.astype(str) == str(team_id))
        | (matches.away_id.astype(str) == str(team_id))
    ].copy()
    m = m[m["completed"]].sort_values("date", ascending=False).head(last_n).sort_values("date")
    if m.empty:
        return m

    def outcome(row):
        home = str(row.home_id) == str(team_id)
        gf = row.home_score if home else row.away_score
        ga = row.away_score if home else row.home_score
        if pd.isna(gf) or pd.isna(ga):
            return "-"
        return "V" if gf > ga else "E" if gf == ga else "D"

    m["result"] = m.apply(outcome, axis=1)
    return m


def team_summary(matches: pd.DataFrame, team_id: str) -> dict:
    m = matches[
        (matches.home_id.astype(str) == str(team_id))
        | (matches.away_id.astype(str) == str(team_id))
    ]
    m = m[m["completed"]].copy()
    if m.empty:
        return {"games": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "ppg": 0.0}

    wins = draws = losses = gf = ga = 0
    for row in m.itertuples():
        home = str(row.home_id) == str(team_id)
        scored = row.home_score if home else row.away_score
        conceded = row.away_score if home else row.home_score
        if scored is None or conceded is None:
            continue
        gf += int(scored)
        ga += int(conceded)
        if scored > conceded:
            wins += 1
        elif scored == conceded:
            draws += 1
        else:
            losses += 1

    games = wins + draws + losses
    return {
        "games": games,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "gf": gf,
        "ga": ga,
        "ppg": round((wins * 3 + draws) / games, 2) if games else 0.0,
    }
