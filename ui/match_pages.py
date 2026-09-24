from __future__ import annotations

import pandas as pd
import streamlit as st

from config import LEAGUES
from scout_analytics import team_form, team_summary, prepare_players, prepare_team_stats, TEAM_LABELS
from ui.common import (
    league_matches, league_teams, league_players, league_team_stats,
    match_list, normalize_name,
)
from charts import team_fingerprint_chart


def home_page(season: int):
    st.title("LATAMDATA")
    st.subheader("Football intelligence for South America")
    st.success("Times, jogos e atletas reais. Não há fallback para jogadores fictícios.")

    frames = []
    for key in LEAGUES:
        try:
            frames.append(league_matches(key, season))
        except Exception:
            pass

    if not frames:
        st.warning("Não foi possível carregar partidas agora.")
        return

    df = pd.concat(frames, ignore_index=True)
    now = pd.Timestamp.now(tz="UTC")
    left, right = st.columns(2)
    with left:
        st.subheader("Últimos jogos")
        match_list(
            df[df.date <= now].sort_values("date", ascending=False).head(6),
            "home_last_",
        )
    with right:
        st.subheader("Próximos jogos")
        match_list(
            df[df.date > now].sort_values("date").head(6),
            "home_next_",
        )

    st.divider()
    st.subheader("Radar LATAMDATA · Brasileirão Série A")
    try:
        players = prepare_players(league_players("bra_a", season))
        qualified = players[players.minutes.fillna(0) >= 600].copy()
        left, right = st.columns(2)
        with left:
            st.markdown("**Maior Impact Score**")
            cols = [
                "player", "club", "position", "age", "minutes",
                "performance_score", "archetype",
            ]
            st.dataframe(
                qualified.sort_values(
                    "performance_score", ascending=False
                )[cols].head(8),
                hide_index=True,
                use_container_width=True,
            )
        with right:
            st.markdown("**Oportunidades Sub-23**")
            u23 = qualified[qualified.age.fillna(99) <= 23]
            cols = [
                "player", "club", "position", "age", "minutes",
                "opportunity_score", "market_value_m", "archetype",
            ]
            st.dataframe(
                u23.sort_values(
                    "opportunity_score", ascending=False
                )[cols].head(8),
                hide_index=True,
                use_container_width=True,
            )
    except Exception as exc:
        st.caption(f"Radar de atletas temporariamente indisponível: {exc}")


def teams_page(season: int):
    st.title("Times")
    key = st.selectbox(
        "Campeonato",
        list(LEAGUES),
        format_func=lambda x: LEAGUES[x].name,
    )

    try:
        teams = league_teams(key, season).sort_values("team")
        query = st.text_input("Pesquisar time")
        if query:
            teams = teams[teams.team.str.contains(query, case=False, na=False)]
        if teams.empty:
            st.info("Nenhum time encontrado.")
            return

        labels = {row.team_id: row.team for row in teams.itertuples()}
        team_id = st.selectbox(
            "Time",
            teams.team_id.tolist(),
            format_func=lambda x: labels[x],
        )
        team = teams[teams.team_id.astype(str) == str(team_id)].iloc[0]

        if team.logo:
            st.image(team.logo, width=80)
        st.header(team.team)

        matches = league_matches(key, season)
        summary = team_summary(matches, team_id)
        cols = st.columns(5)
        metrics = [
            ("Jogos", summary["games"]),
            ("Vitórias", summary["wins"]),
            ("Empates", summary["draws"]),
            ("Derrotas", summary["losses"]),
            ("Pts/jogo", summary["ppg"]),
        ]
        for col, (label, value) in zip(cols, metrics):
            col.metric(label, value)

        form = team_form(matches, team_id, 10)
        if not form.empty:
            st.write("Forma recente: " + " ".join(form.result.astype(str)))

        tab_games, tab_players, tab_fingerprint = st.tabs(
            ["Partidas", "Jogadores", "Tactical Fingerprint"]
        )
        with tab_games:
            club_matches = matches[
                (matches.home_id.astype(str) == str(team_id))
                | (matches.away_id.astype(str) == str(team_id))
            ]
            match_list(
                club_matches.sort_values("date", ascending=False).head(30),
                "team_",
            )

        with tab_players:
            with st.spinner("Carregando elenco estatístico real..."):
                players = prepare_players(league_players(key, season))
            club_norm = normalize_name(team.team)
            names = players.club.fillna("").map(normalize_name)
            players = players[
                names.map(
                    lambda value: value == club_norm
                    or club_norm in value
                    or value in club_norm
                )
            ]
            if players.empty:
                st.info("Não consegui casar o nome do clube entre as duas fontes.")
            else:
                columns = [
                    "player", "position", "minutes", "rating",
                    "goals90", "assists90", "xg90", "xa90",
                    "performance_score",
                ]
                st.dataframe(
                    players[columns].sort_values("minutes", ascending=False),
                    hide_index=True,
                    use_container_width=True,
                )

        with tab_fingerprint:
            try:
                advanced = prepare_team_stats(league_team_stats(key, season))
                club_norm = normalize_name(team.team)
                names = advanced.team.fillna("").map(normalize_name)
                matched = advanced[
                    names.map(
                        lambda value: value == club_norm
                        or (value and value in club_norm)
                        or (club_norm and club_norm in value)
                    )
                ]
                if matched.empty:
                    st.info("Fingerprint avançado indisponível para este clube.")
                else:
                    profile = matched.iloc[0]
                    st.subheader("Tactical Fingerprint")
                    st.caption(
                        f"Estilo detectado: **{profile.tactical_style}** · "
                        "percentis comparados aos times da mesma liga."
                    )
                    left, right = st.columns([1, 1.25])
                    with left:
                        st.plotly_chart(
                            team_fingerprint_chart(profile),
                            use_container_width=True,
                        )
                    with right:
                        metrics = [
                            "expected_goals_team",
                            "expected_goals_conceded_team",
                            "_xg_diff_team",
                            "possession_percentage_team",
                            "ontarget_scoring_att_team",
                            "big_chance_team",
                            "touches_in_opp_box_team",
                            "accurate_pass_team",
                            "poss_won_att_3rd_team",
                            "total_tackle_team",
                            "interception_team",
                        ]
                        rows = []
                        for metric in metrics:
                            value = profile.get(metric)
                            pct = profile.get(f"pct_{metric}")
                            if pd.notna(value):
                                rows.append(
                                    {
                                        "Métrica": TEAM_LABELS.get(metric, metric),
                                        "Valor": round(float(value), 2),
                                        "Percentil": None if pd.isna(pct)
                                        else round(float(pct), 0),
                                    }
                                )
                        st.dataframe(
                            pd.DataFrame(rows),
                            hide_index=True,
                            use_container_width=True,
                        )
            except Exception as exc:
                st.info(f"Fingerprint avançado indisponível: {exc}")
    except Exception as exc:
        st.error(str(exc))


def games_page(season: int):
    st.title("Jogos")
    selected = st.multiselect(
        "Campeonatos",
        list(LEAGUES),
        default=list(LEAGUES),
        format_func=lambda x: LEAGUES[x].name,
    )

    frames = []
    for key in selected:
        try:
            frames.append(league_matches(key, season))
        except Exception as exc:
            st.warning(f"{LEAGUES[key].name}: {exc}")

    if not frames:
        st.info("Nenhuma partida disponível.")
        return

    df = pd.concat(frames, ignore_index=True)
    query = st.text_input("Buscar time")
    if query:
        df = df[
            df.home.str.contains(query, case=False, na=False)
            | df.away.str.contains(query, case=False, na=False)
        ]

    mode = st.radio(
        "Mostrar",
        ["Recentes", "Próximos", "Todos"],
        horizontal=True,
    )
    now = pd.Timestamp.now(tz="UTC")
    if mode == "Recentes":
        df = df[df.date <= now].sort_values("date", ascending=False).head(80)
    elif mode == "Próximos":
        df = df[df.date > now].sort_values("date").head(80)
    else:
        df = df.sort_values("date", ascending=False)

    match_list(df, "games_")
