from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from config import LEAGUES
from analytics import (
    RADAR_METRICS, LABELS, similar_players, strengths_weaknesses,
)
from charts import radar_chart, heatmap_figure
from ui.common import load_players, player_profile, player_heatmap, source_badges


TABLE_COLUMNS = [
    "player", "club", "league", "position", "minutes", "rating",
    "goals90", "assists90", "xg90", "xa90", "performance_score",
    "market_value_m", "value_score",
]


def _enrich_player(row: pd.Series) -> pd.Series:
    try:
        profile = player_profile(int(row.player_id))
        for key in [
            "age", "height_cm", "preferred_foot", "nationality",
            "market_value_m", "club",
        ]:
            value = row.get(key)
            if pd.isna(value) or value in ("", None):
                row[key] = profile.get(key, value)
    except Exception:
        pass
    return row


def _player_selector(df: pd.DataFrame, label: str, key: str | None = None):
    labels = {
        f"{row.league_key}:{int(row.player_id)}":
            f"{row.player} — {row.club} ({LEAGUES[row.league_key].name})"
        for row in df.sort_values("player").itertuples()
    }
    selected = st.selectbox(
        label,
        list(labels),
        format_func=lambda value: labels[value],
        key=key,
    )
    league_key, player_id = selected.split(":")
    row = df[
        (df.league_key == league_key)
        & (df.player_id.astype(str) == player_id)
    ].iloc[0].copy()
    return league_key, int(player_id), row


def _profile_view(df: pd.DataFrame):
    league_key, player_id, player = _player_selector(df, "Jogador", "profile_player")
    player = _enrich_player(player)

    left, right = st.columns([1, 7])
    with left:
        st.image(
            f"https://img.sofascore.com/api/v1/player/{player_id}/image",
            width=105,
        )
    with right:
        st.header(player.player)
        st.caption(f"{player.club} · {player.league} · {player.position}")

    cols = st.columns(6)
    cols[0].metric("Idade", "—" if pd.isna(player.age) else int(player.age))
    cols[1].metric(
        "Minutos",
        "—" if pd.isna(player.minutes) else int(player.minutes),
    )
    cols[2].metric(
        "Nota",
        "—" if pd.isna(player.rating) else f"{player.rating:.2f}",
    )
    cols[3].metric(
        "Performance",
        "—" if pd.isna(player.performance_score)
        else f"{player.performance_score:.1f}",
    )
    cols[4].metric(
        "Valor",
        "—" if pd.isna(player.market_value_m)
        else f"€ {player.market_value_m:.1f} mi",
    )
    cols[5].metric(
        "Pé",
        player.get("preferred_foot") or "—",
    )

    radar_col, heat_col = st.columns(2)
    with radar_col:
        st.subheader("Percentis por posição")
        st.plotly_chart(
            radar_chart(player, RADAR_METRICS),
            use_container_width=True,
        )
    with heat_col:
        st.subheader("Mapa de calor da temporada")
        try:
            heatmap = player_heatmap(
                player_id,
                int(player.tournament_id),
                int(player.season_id),
            )
            if heatmap.empty:
                st.info("Heatmap indisponível para este atleta.")
            else:
                st.pyplot(heatmap_figure(heatmap), use_container_width=True)
        except Exception as exc:
            st.info(f"Heatmap indisponível: {exc}")

    rows = []
    metrics = [
        "goals90", "assists90", "xg90", "xa90", "key_pass90",
        "passes_final_third90", "pass_accuracy_pct", "long_balls90",
        "big_chances_created90", "dribbles90", "shots90",
        "shots_on_target90", "tackles90", "interceptions90",
        "recoveries90", "clearances90", "duel_win_pct",
        "aerial_win_pct",
    ]
    for metric in metrics:
        if metric in player and pd.notna(player[metric]):
            pct = player.get(f"pct_{metric}")
            rows.append({
                "Métrica": LABELS.get(metric, metric),
                "Valor": round(float(player[metric]), 2),
                "Percentil": None if pd.isna(pct) else round(float(pct), 0),
            })
    st.subheader("Métricas reais de temporada")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    strong, weak = strengths_weaknesses(player)
    a, b = st.columns(2)
    with a:
        st.subheader("Pontos fortes")
        for name, value in strong:
            st.progress(int(value), text=f"{name} — P{value:.0f}")
    with b:
        st.subheader("Pontos a desenvolver")
        for name, value in weak:
            st.progress(int(value), text=f"{name} — P{value:.0f}")

    st.subheader("Jogadores similares")
    similar = similar_players(
        df,
        player_id,
        league_key=league_key,
        n=10,
    )
    if similar.empty:
        st.info("Amostra insuficiente para similaridade.")
    else:
        st.dataframe(
            similar[
                [
                    "player", "club", "league", "position", "minutes",
                    "rating", "performance_score", "market_value_m",
                    "similarity",
                ]
            ],
            hide_index=True,
            use_container_width=True,
        )


def scout_page(season: int):
    st.title("Scout de jogadores")
    source_badges()

    selected = st.multiselect(
        "Campeonatos carregados",
        list(LEAGUES),
        default=["bra_a"],
        format_func=lambda x: LEAGUES[x].name,
    )
    if not selected:
        return

    with st.spinner("Carregando jogadores reais..."):
        df, errors = load_players(selected, season)

    for key, error in errors:
        st.warning(f"{LEAGUES[key].name}: {error}")

    if df.empty:
        st.error(
            "A fonte real de jogadores está indisponível agora. "
            "O app não substitui os dados por jogadores fictícios."
        )
        return

    st.caption(f"{len(df)} atletas reais carregados.")
    tab_discover, tab_profile = st.tabs(["Descobrir", "Perfil"])

    with tab_discover:
        query = st.text_input("Pesquisar jogador ou time")
        a, b, c = st.columns(3)
        positions = sorted(df.position.dropna().unique())
        positions_selected = a.multiselect(
            "Posição",
            positions,
            default=positions,
        )
        maximum = int(max(900, df.minutes.fillna(0).max()))
        min_minutes = b.slider(
            "Minutos mínimos",
            0,
            maximum,
            min(450, maximum),
            90,
        )
        sort_by = c.selectbox(
            "Ordenar por",
            [
                "performance_score", "rating", "minutes",
                "xg90", "xa90", "value_score",
            ],
        )

        filtered = df[
            df.position.isin(positions_selected)
            & (df.minutes.fillna(0) >= min_minutes)
        ].copy()
        if query:
            filtered = filtered[
                filtered.player.str.contains(query, case=False, na=False)
                | filtered.club.str.contains(query, case=False, na=False)
            ]
        filtered = filtered.sort_values(
            sort_by,
            ascending=False,
            na_position="last",
        )

        show = filtered[TABLE_COLUMNS].copy()
        show.columns = [
            "Jogador", "Clube", "Liga", "Pos.", "Minutos", "Nota",
            "Gols/90", "Ast/90", "xG/90", "xA/90", "Performance",
            "Valor € mi", "Value Score",
        ]
        st.dataframe(
            show.head(300),
            hide_index=True,
            use_container_width=True,
        )

        if not filtered.empty:
            x_axis = (
                "market_value_m"
                if filtered.market_value_m.notna().sum() >= 8
                else "rating"
            )
            plot_df = filtered[filtered[x_axis].notna()]
            if not plot_df.empty:
                st.plotly_chart(
                    px.scatter(
                        plot_df,
                        x=x_axis,
                        y="performance_score",
                        size="minutes",
                        color="position",
                        hover_name="player",
                        hover_data=["club", "league", "xg90", "xa90"],
                    ),
                    use_container_width=True,
                )

    with tab_profile:
        _profile_view(df)


def compare_page(season: int):
    st.title("Comparar jogadores")
    source_badges()

    selected = st.multiselect(
        "Campeonatos",
        list(LEAGUES),
        default=["bra_a"],
        format_func=lambda x: LEAGUES[x].name,
        key="compare_leagues",
    )
    if not selected:
        return

    df, errors = load_players(selected, season)
    for key, error in errors:
        st.warning(f"{LEAGUES[key].name}: {error}")
    if df.empty:
        st.error("A fonte real de jogadores está indisponível.")
        return

    a, b = st.columns(2)
    with a:
        _, _, p1 = _player_selector(df, "Jogador A", "compare_a")
    with b:
        _, _, p2 = _player_selector(df, "Jogador B", "compare_b")

    with a:
        st.subheader(p1.player)
        st.plotly_chart(radar_chart(p1, RADAR_METRICS), use_container_width=True)
    with b:
        st.subheader(p2.player)
        st.plotly_chart(radar_chart(p2, RADAR_METRICS), use_container_width=True)

    metrics = [
        ("Nota", "rating"),
        ("Performance", "performance_score"),
        ("Gols/90", "goals90"),
        ("Assistências/90", "assists90"),
        ("xG/90", "xg90"),
        ("xA/90", "xa90"),
        ("Passes-chave/90", "key_pass90"),
        ("Dribles/90", "dribbles90"),
        ("Desarmes/90", "tackles90"),
        ("Interceptações/90", "interceptions90"),
        ("Duelos %", "duel_win_pct"),
        ("Minutos", "minutes"),
    ]
    comparison = pd.DataFrame({
        "Métrica": [item[0] for item in metrics],
        p1.player: [p1.get(item[1]) for item in metrics],
        p2.player: [p2.get(item[1]) for item in metrics],
    })
    st.dataframe(comparison, hide_index=True, use_container_width=True)
