from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

SCOUT_METRICS = [
    "rating", "goals90", "assists90", "xg90", "xa90", "key_pass90",
    "passes_final_third90", "pass_accuracy_pct", "long_balls90",
    "big_chances_created90", "tackles90", "interceptions90", "recoveries90",
    "clearances90", "duel_win_pct", "aerial_win_pct", "dribbles90",
    "shots90", "shots_on_target90", "turnovers90", "saves90",
]

LOWER_IS_BETTER = {"turnovers90"}

RADAR_METRICS = {
    "Finalização": "xg90",
    "Criação": "xa90",
    "Passes-chave": "key_pass90",
    "Drible": "dribbles90",
    "Desarme": "tackles90",
    "Interceptação": "interceptions90",
    "Duelos": "duel_win_pct",
}

ROLE_METRICS = {
    "G": ["rating", "saves90", "pass_accuracy_pct", "aerial_win_pct"],
    "D": ["rating", "interceptions90", "tackles90", "clearances90", "duel_win_pct", "aerial_win_pct", "pass_accuracy_pct"],
    "M": ["rating", "xa90", "key_pass90", "passes_final_third90", "dribbles90", "interceptions90", "duel_win_pct"],
    "F": ["rating", "xg90", "goals90", "xa90", "shots90", "dribbles90", "key_pass90"],
}

LABELS = {
    "rating": "Nota média", "goals90": "Gols/90", "assists90": "Assistências/90",
    "xg90": "xG/90", "xa90": "xA/90", "key_pass90": "Passes-chave/90",
    "passes_final_third90": "Passes ao terço final/90", "pass_accuracy_pct": "Precisão de passe",
    "long_balls90": "Bolas longas certas/90", "big_chances_created90": "Grandes chances criadas/90",
    "tackles90": "Desarmes/90", "interceptions90": "Interceptações/90", "recoveries90": "Recuperações/90",
    "clearances90": "Cortes/90", "duel_win_pct": "Duelos vencidos %", "aerial_win_pct": "Duelos aéreos %",
    "dribbles90": "Dribles certos/90", "shots90": "Finalizações/90", "shots_on_target90": "No alvo/90",
    "turnovers90": "Proteção da posse", "saves90": "Defesas/90",
}


def add_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out
    for _, group in out.groupby("position", dropna=False):
        idx = group.index
        for metric in SCOUT_METRICS:
            if metric not in group.columns or group[metric].notna().sum() < 2:
                continue
            pct = group[metric].rank(pct=True, method="average") * 100
            if metric in LOWER_IS_BETTER:
                pct = 100 - pct + (100 / max(group[metric].notna().sum(), 1))
            out.loc[idx, f"pct_{metric}"] = pct.clip(0, 100)
    return out


def add_performance_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out
    scores = []
    for _, row in out.iterrows():
        metrics = ROLE_METRICS.get(str(row.get("position", "")), SCOUT_METRICS[:10])
        vals = [row.get(f"pct_{m}") for m in metrics]
        vals = [float(v) for v in vals if pd.notna(v)]
        scores.append(round(float(np.mean(vals)), 1) if vals else np.nan)
    out["performance_score"] = scores
    return out


def add_value_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["value_score"] = np.nan
    if out.empty or "market_value_m" not in out:
        return out
    valid = out["market_value_m"].notna() & (out["market_value_m"] > 0) & out["performance_score"].notna()
    if valid.sum() < 2:
        return out
    age = out.loc[valid, "age"] if "age" in out else pd.Series(np.nan, index=out.index[valid])
    youth = np.where(age.fillna(27) <= 21, 1.15, np.where(age.fillna(27) <= 24, 1.08, np.where(age.fillna(27) <= 28, 1.0, .92)))
    raw = out.loc[valid, "performance_score"].to_numpy() * youth / np.sqrt(out.loc[valid, "market_value_m"].clip(lower=.15).to_numpy())
    lo, hi = float(np.nanmin(raw)), float(np.nanmax(raw))
    score = np.full(len(raw), 50.0) if hi - lo < 1e-9 else (raw - lo) / (hi - lo) * 100
    out.loc[valid, "value_score"] = np.round(score, 1)
    return out


def prepare_players(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return add_value_score(add_performance_score(add_percentiles(df)))


def similar_players(df: pd.DataFrame, player_id: int, league_key: str | None = None, n: int = 8) -> pd.DataFrame:
    target_mask = df["player_id"].astype(str) == str(player_id)
    if league_key is not None:
        target_mask &= df["league_key"].eq(league_key)
    target_rows = df[target_mask]
    if target_rows.empty:
        return pd.DataFrame()
    target = target_rows.iloc[0]
    pool = df[
        (df["position"] == target["position"]) &
        ~((df["player_id"].astype(str) == str(player_id)) & (df["league_key"] == target["league_key"])) &
        (df["minutes"].fillna(0) >= 450)
    ].copy()
    if pool.empty:
        return pool
    features = [m for m in SCOUT_METRICS if m in df.columns and df[m].notna().sum() >= 8]
    if not features:
        return pd.DataFrame()
    combo = pd.concat([target_rows.iloc[[0]][features], pool[features]], ignore_index=True)
    combo = combo.apply(pd.to_numeric, errors="coerce")
    combo = combo.fillna(combo.median(numeric_only=True)).fillna(0)
    z = StandardScaler().fit_transform(combo)
    model = NearestNeighbors(metric="cosine")
    model.fit(z[1:])
    distances, indices = model.kneighbors(z[0].reshape(1,-1), n_neighbors=min(n, len(pool)))
    result = pool.iloc[indices[0]].copy()
    result["similarity"] = ((1 - distances[0]) * 100).clip(0, 100).round(1)
    return result.sort_values("similarity", ascending=False)


def strengths_weaknesses(row: pd.Series, top_n: int = 4):
    pairs = []
    for metric, label in LABELS.items():
        key = f"pct_{metric}"
        if key in row.index and pd.notna(row.get(key)):
            pairs.append((label, float(row[key])))
    pairs.sort(key=lambda x: x[1], reverse=True)
    if not pairs:
        return [], []
    return pairs[:top_n], list(reversed(pairs[-top_n:]))


def team_form(matches: pd.DataFrame, team_id: str, last_n: int = 10) -> pd.DataFrame:
    if matches.empty:
        return matches
    m = matches[(matches.home_id.astype(str) == str(team_id)) | (matches.away_id.astype(str) == str(team_id))].copy()
    m = m[m["completed"]].sort_values("date", ascending=False).head(last_n).sort_values("date")
    if m.empty:
        return m
    def outcome(r):
        home = str(r.home_id) == str(team_id)
        gf = r.home_score if home else r.away_score
        ga = r.away_score if home else r.home_score
        if pd.isna(gf) or pd.isna(ga): return "-"
        return "V" if gf > ga else "E" if gf == ga else "D"
    m["result"] = m.apply(outcome, axis=1)
    return m


def team_summary(matches: pd.DataFrame, team_id: str) -> dict:
    m = matches[(matches.home_id.astype(str) == str(team_id)) | (matches.away_id.astype(str) == str(team_id))]
    m = m[m["completed"]].copy()
    if m.empty:
        return {"games":0,"wins":0,"draws":0,"losses":0,"gf":0,"ga":0,"ppg":0.0}
    wins=draws=losses=gf=ga=0
    for r in m.itertuples():
        home = str(r.home_id) == str(team_id)
        a = r.home_score if home else r.away_score
        b = r.away_score if home else r.home_score
        if a is None or b is None: continue
        gf += int(a); ga += int(b)
        if a>b: wins+=1
        elif a==b: draws+=1
        else: losses+=1
    games = wins+draws+losses
    return {"games":games,"wins":wins,"draws":draws,"losses":losses,"gf":gf,"ga":ga,"ppg":round((wins*3+draws)/games,2) if games else 0.0}
