
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

METRICS = [
    "goals90","assists90","xg90","xa90","prog_pass90","prog_carry90",
    "key_pass90","passes_final_third90","tackles90","interceptions90",
    "recoveries90","duel_win_pct","aerial_win_pct","dribbles90","shots90","pressures90"
]

RADAR_METRICS = {
    "Finalização": "xg90",
    "Criação": "xa90",
    "Progressão passe": "prog_pass90",
    "Progressão condução": "prog_carry90",
    "Defesa": "interceptions90",
    "Pressão": "pressures90",
    "Duelos": "duel_win_pct",
}

LOWER_IS_BETTER = {"turnovers90"}

def add_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for position, group in out.groupby("position"):
        idx = group.index
        for metric in METRICS + ["turnovers90"]:
            ascending = metric not in LOWER_IS_BETTER
            ranks = group[metric].rank(pct=True, ascending=ascending) * 100
            if metric in LOWER_IS_BETTER:
                ranks = 100 - ranks + (100 / max(len(group), 1))
            out.loc[idx, f"pct_{metric}"] = ranks.clip(0, 100)
    return out

def add_value_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Age and league context add modest weighting; performance remains dominant.
    league_factor = {
        "Brasil Série A": 1.00, "Argentina": 0.97, "Brasil Série B": 0.90,
        "Uruguai": 0.88, "Colômbia": 0.89, "Chile": 0.87,
        "Equador": 0.86, "Paraguai": 0.84
    }
    age_bonus = np.where(out["age"] <= 23, 1.12, np.where(out["age"] <= 27, 1.04, 0.94))
    adjusted_perf = out["performance_score"] * out["league"].map(league_factor).fillna(0.85) * age_bonus
    raw = adjusted_perf / np.sqrt(out["market_value_m"].clip(lower=0.15))
    out["value_score"] = ((raw - raw.min()) / (raw.max() - raw.min()) * 100).round(1)
    return out

def similar_players(df: pd.DataFrame, player_id: int, n=8) -> pd.DataFrame:
    target = df[df["player_id"] == player_id].iloc[0]
    pool = df[
        (df["position"] == target["position"]) &
        (df["player_id"] != player_id) &
        (df["minutes"] >= 600)
    ].copy()
    if pool.empty:
        return pool

    features = [
        "goals90","assists90","xg90","xa90","prog_pass90","prog_carry90",
        "key_pass90","passes_final_third90","tackles90","interceptions90",
        "recoveries90","duel_win_pct","aerial_win_pct","dribbles90","pressures90"
    ]
    scaler = StandardScaler()
    combo = pd.concat([df[df["player_id"] == player_id][features], pool[features]], ignore_index=True)
    z = scaler.fit_transform(combo)
    target_z, pool_z = z[0].reshape(1,-1), z[1:]
    model = NearestNeighbors(metric="cosine")
    model.fit(pool_z)
    distances, indices = model.kneighbors(target_z, n_neighbors=min(n, len(pool)))
    result = pool.iloc[indices[0]].copy()
    result["similarity"] = ((1 - distances[0]) * 100).clip(0,100).round(1)
    return result.sort_values("similarity", ascending=False)

def player_strengths_weaknesses(row, top_n=4):
    metric_names = {
        "goals90":"Gols", "assists90":"Assistências", "xg90":"xG",
        "xa90":"xA", "prog_pass90":"Passes progressivos",
        "prog_carry90":"Conduções progressivas", "key_pass90":"Passes-chave",
        "passes_final_third90":"Passes ao terço final", "tackles90":"Desarmes",
        "interceptions90":"Interceptações", "recoveries90":"Recuperações",
        "duel_win_pct":"Duelos vencidos", "aerial_win_pct":"Duelos aéreos",
        "dribbles90":"Dribles", "shots90":"Finalizações", "pressures90":"Pressões",
        "turnovers90":"Proteção da posse"
    }
    pairs = []
    for metric, label in metric_names.items():
        key = f"pct_{metric}"
        if key in row.index:
            pairs.append((label, float(row[key])))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:top_n], list(reversed(pairs[-top_n:]))
