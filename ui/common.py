from __future__ import annotations

import unicodedata
import pandas as pd
import streamlit as st

from config import LEAGUES
from data.espn_client import (
    ESPNClient, normalize_scoreboard, normalize_teams, teams_from_matches,
    match_team_stats, match_lineups, match_events, match_header,
)
from data.sofascore_client import SofaScoreClient, normalize_profile
from analytics import prepare_players


@st.cache_resource
def espn_client():
    return ESPNClient()


@st.cache_resource
def sofascore_client():
    return SofaScoreClient()


@st.cache_data(ttl=900, show_spinner=False)
def league_matches(league_key: str, season: int):
    league = LEAGUES[league_key]
    return normalize_scoreboard(
        espn_client().scoreboard(league.espn_slug, season),
        league_key,
        league.name,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def league_teams(league_key: str, season: int):
    league = LEAGUES[league_key]
    try:
        df = normalize_teams(
            espn_client().teams_endpoint(league.espn_slug),
            league_key,
            league.name,
        )
        if not df.empty:
            return df
    except Exception:
        pass
    return teams_from_matches(league_matches(league_key, season))


@st.cache_data(ttl=900, show_spinner=False)
def match_summary(league_key: str, event_id: str):
    return espn_client().summary(LEAGUES[league_key].espn_slug, event_id)


@st.cache_data(ttl=21600, show_spinner=False)
def league_players(league_key: str, season: int):
    league = LEAGUES[league_key]
    client = sofascore_client()
    season_id = client.season_id(league.sofascore_tournament_id, season)
    return client.league_players(
        league.sofascore_tournament_id,
        season_id,
        league_key,
        league.name,
    )


@st.cache_data(ttl=21600, show_spinner=False)
def player_profile(player_id: int):
    return normalize_profile(sofascore_client().player_profile(int(player_id)))


@st.cache_data(ttl=21600, show_spinner=False)
def player_heatmap(player_id: int, tournament_id: int, season_id: int):
    return sofascore_client().player_season_heatmap(
        int(player_id), int(tournament_id), int(season_id)
    )


def load_players(league_keys: list[str], season: int):
    frames, errors = [], []
    for key in league_keys:
        try:
            df = league_players(key, season)
            if not df.empty:
                frames.append(df)
        except Exception as exc:
            errors.append((key, str(exc)))
    if not frames:
        return pd.DataFrame(), errors
    return prepare_players(pd.concat(frames, ignore_index=True)), errors


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode().lower()
    return "".join(c for c in value if c.isalnum())


def format_date(value) -> str:
    try:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return ts.tz_convert("America/Sao_Paulo").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value or "")


def score_text(row) -> str:
    if pd.notna(row.home_score) and pd.notna(row.away_score):
        return f"{int(row.home_score)} x {int(row.away_score)}"
    return "x"


def source_badges():
    st.caption("Dados reais de jogadores: SofaScore (integração web não oficial). Times e jogos: ESPN.")


def match_list(df, prefix: str = ""):
    if df.empty:
        st.info("Nenhuma partida encontrada.")
        return
    for row in df.itertuples():
        a, b, c, d, e = st.columns([1.4, 3, 1.2, 3, .8])
        a.caption(format_date(row.date))
        b.write(f"**{row.home}**")
        c.markdown(f"### {score_text(row)}")
        d.write(f"**{row.away}**")
        with e:
            if st.button("Abrir", key=f"{prefix}{row.league_key}_{row.event_id}"):
                st.session_state.match = (row.league_key, str(row.event_id))
                st.rerun()


def render_match_center():
    state = st.session_state.get("match")
    if not state:
        return False

    league_key, event_id = state
    st.title("Central da partida")
    if st.button("Voltar"):
        del st.session_state.match
        st.rerun()

    try:
        data = match_summary(league_key, event_id)
        header = match_header(data)

        left, center, right = st.columns([2, 1, 2])
        with left:
            if header["home_logo"]:
                st.image(header["home_logo"], width=70)
            st.subheader(header["home"])
        with center:
            hs = "-" if header["home_score"] in (None, "") else header["home_score"]
            aws = "-" if header["away_score"] in (None, "") else header["away_score"]
            st.markdown(f"## {hs} x {aws}")
        with right:
            if header["away_logo"]:
                st.image(header["away_logo"], width=70)
            st.subheader(header["away"])

        st.caption(
            f"{format_date(header['date'])} · {header['venue']} · {header['status']}"
        )
        tab_stats, tab_lineups, tab_events = st.tabs(
            ["Estatísticas", "Escalações", "Eventos"]
        )
        with tab_stats:
            frame = match_team_stats(data)
            if frame.empty:
                st.info("Sem estatísticas detalhadas para esta partida.")
            else:
                st.dataframe(frame.T, use_container_width=True)
        with tab_lineups:
            frame = match_lineups(data)
            if frame.empty:
                st.info("Escalações indisponíveis.")
            else:
                st.dataframe(frame, hide_index=True, use_container_width=True)
        with tab_events:
            frame = match_events(data)
            if frame.empty:
                st.info("Eventos indisponíveis.")
            else:
                st.dataframe(frame, hide_index=True, use_container_width=True)
    except Exception as exc:
        st.error(str(exc))
    return True
