from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import add_percentiles, add_value_score, similar_players, player_strengths_weaknesses, RADAR_METRICS
from charts import radar_chart, heatmap_figure
from config import APP_NAME, APP_TAGLINE, DEFAULT_SEASON, LEAGUES
from data.espn_client import ESPNClient, normalize_scoreboard, normalize_teams, teams_from_matches, match_header, match_team_stats, match_lineups, match_events

ROOT = Path(__file__).parent
st.set_page_config(page_title=APP_NAME, page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container{padding-top:1.1rem;max-width:1500px}
[data-testid="stMetricValue"]{font-size:1.5rem}
.hero{padding:1.2rem 1.35rem;border:1px solid rgba(128,128,128,.25);border-radius:16px;margin-bottom:1rem}
.pill-real,.pill-demo{display:inline-block;padding:.16rem .55rem;border-radius:999px;font-size:.74rem;margin-bottom:.6rem}
.pill-real{background:rgba(30,170,100,.14)} .pill-demo{background:rgba(240,170,30,.14)}
.score{font-size:1.75rem;font-weight:750;text-align:center}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def api():
    return ESPNClient()

@st.cache_data(ttl=900, show_spinner=False)
def get_matches(league_key: str, season: int):
    league = LEAGUES[league_key]
    return normalize_scoreboard(api().scoreboard(league.espn_slug, season), league_key, league.name)

@st.cache_data(ttl=3600, show_spinner=False)
def get_teams(league_key: str, season: int):
    league = LEAGUES[league_key]
    try:
        teams = normalize_teams(api().teams(league.espn_slug), league_key, league.name)
        if not teams.empty:
            return teams
    except Exception:
        pass
    return teams_from_matches(get_matches(league_key, season))

@st.cache_data(ttl=900, show_spinner=False)
def get_summary(league_key: str, event_id: str):
    return api().summary(LEAGUES[league_key].espn_slug, event_id)

@st.cache_data(show_spinner=False)
def load_players():
    players = pd.read_csv(ROOT / "players.csv")
    events = pd.read_csv(ROOT / "events.csv")
    return add_value_score(add_percentiles(players)), events


def fmt_date(value):
    if pd.isna(value):
        return ""
    value = pd.Timestamp(value)
    try:
        value = value.tz_convert("America/Sao_Paulo")
    except Exception:
        pass
    return value.strftime("%d/%m/%Y %H:%M")


def score_text(row):
    if pd.notna(row.home_score) and pd.notna(row.away_score):
        return f"{int(row.home_score)} × {int(row.away_score)}"
    return "×"


def team_matches(matches, team_id):
    tid = str(team_id)
    return matches[(matches.home_id.astype(str) == tid) | (matches.away_id.astype(str) == tid)].copy()


def team_summary(matches, team_id):
    completed = team_matches(matches, team_id)
    completed = completed[completed.completed == True]
    wins = draws = losses = gf = ga = 0
    tid = str(team_id)
    form = []
    for row in completed.sort_values("date").itertuples():
        home = str(row.home_id) == tid
        a = row.home_score if home else row.away_score
        b = row.away_score if home else row.home_score
        if pd.isna(a) or pd.isna(b):
            continue
        a, b = int(a), int(b)
        gf += a; ga += b
        if a > b: wins += 1; form.append("V")
        elif a == b: draws += 1; form.append("E")
        else: losses += 1; form.append("D")
    games = wins + draws + losses
    return {"games": games, "wins": wins, "draws": draws, "losses": losses, "gf": gf, "ga": ga, "ppg": round((wins * 3 + draws) / games, 2) if games else 0.0, "form": form[-10:]}


def open_match(league_key, event_id):
    st.session_state.match = (league_key, str(event_id))
    st.session_state.match_open = True
    st.session_state.return_page = st.session_state.get("page", "Jogos")
    st.rerun()


def render_match(row, key_prefix="match"):
    c1, c2, c3, c4, c5 = st.columns([1.25, 3, 1.15, 3, 1.3])
    c1.caption(fmt_date(row.date))
    c2.write(f"**{row.home}**")
    c3.markdown(f"<div class='score'>{score_text(row)}</div>", unsafe_allow_html=True)
    c4.write(f"**{row.away}**")
    if c5.button("Abrir", key=f"{key_prefix}_{row.league_key}_{row.event_id}", use_container_width=True):
        open_match(row.league_key, row.event_id)


def render_match_center():
    league_key, event_id = st.session_state.match
    st.title("Central da partida")
    if st.button("← Voltar"):
        st.session_state.match_open = False
        st.session_state.page = st.session_state.get("return_page", "Jogos")
        st.rerun()
    try:
        summary = get_summary(league_key, event_id)
        header = match_header(summary)
        st.markdown("<span class='pill-real'>DADOS REAIS</span>", unsafe_allow_html=True)
        left, center, right = st.columns([2, 1, 2])
        with left:
            if header["home_logo"]: st.image(header["home_logo"], width=72)
            st.subheader(header["home"])
        with center:
            hs = "-" if header["home_score"] in (None, "") else header["home_score"]
            as_ = "-" if header["away_score"] in (None, "") else header["away_score"]
            st.markdown(f"<div class='score' style='margin-top:1.8rem'>{hs} × {as_}</div>", unsafe_allow_html=True)
            st.caption(header["status"])
        with right:
            if header["away_logo"]: st.image(header["away_logo"], width=72)
            st.subheader(header["away"])
        st.caption(f"{fmt_date(header['date'])} · {header['venue']}")
        tabs = st.tabs(["Estatísticas", "Escalações", "Eventos"])
        with tabs[0]:
            stats = match_team_stats(summary)
            st.info("Sem estatísticas detalhadas para esta partida.") if stats.empty else st.dataframe(stats.T, use_container_width=True)
        with tabs[1]:
            lineups = match_lineups(summary)
            if lineups.empty:
                st.info("Escalações não disponíveis para esta partida.")
            else:
                for team in lineups.team.unique():
                    st.subheader(team)
                    st.dataframe(lineups[lineups.team == team][["starter", "jersey", "player", "position"]], hide_index=True, use_container_width=True)
        with tabs[2]:
            events = match_events(summary)
            st.info("Eventos-chave não disponíveis para esta partida.") if events.empty else st.dataframe(events, hide_index=True, use_container_width=True)
    except Exception as exc:
        st.error(f"Não consegui carregar esta partida agora: {exc}")


def sidebar():
    st.sidebar.markdown(f"# ⚽ {APP_NAME}")
    st.sidebar.caption(APP_TAGLINE)
    pages = ["Início", "Times", "Jogos", "Scout de jogadores", "Comparar jogadores", "Dados & fontes"]
    if "page" not in st.session_state:
        st.session_state.page = "Início"
    selected = st.sidebar.radio("Navegação", pages, index=pages.index(st.session_state.page if st.session_state.page in pages else "Início"))
    st.session_state.page = selected
    st.sidebar.divider()
    season = int(st.sidebar.number_input("Temporada", 2018, 2030, DEFAULT_SEASON, 1))
    st.sidebar.caption("Times e jogos usam dados online. O scout player-level continua demonstrativo por enquanto.")
    return selected, season

page, season = sidebar()
if st.session_state.get("match_open") and st.session_state.get("match"):
    render_match_center()
    st.stop()

if page == "Início":
    st.markdown(f"<div class='hero'><small>FOOTBALL INTELLIGENCE</small><h1>{APP_NAME}</h1><p>{APP_TAGLINE}</p></div>", unsafe_allow_html=True)
    st.markdown("<span class='pill-real'>TIMES E JOGOS REAIS</span> <span class='pill-demo'>SCOUT DEMO</span>", unsafe_allow_html=True)
    st.write("Pesquise clubes, navegue pelas partidas e abra uma central de jogo. O módulo de scouting mantém os algoritmos anteriores e fica separado da camada de dados online.")
    frames = []
    for key in LEAGUES:
        try: frames.append(get_matches(key, season))
        except Exception: pass
    if frames:
        matches = pd.concat(frames, ignore_index=True)
        now = pd.Timestamp.now(tz="UTC")
        a, b = st.columns(2)
        with a:
            st.subheader("Últimos jogos")
            for row in matches[matches.date <= now].sort_values("date", ascending=False).head(8).itertuples():
                st.write(f"**{row.home} {score_text(row)} {row.away}**")
                st.caption(f"{fmt_date(row.date)} · {row.league}")
        with b:
            st.subheader("Próximos jogos")
            for row in matches[matches.date > now].sort_values("date").head(8).itertuples():
                st.write(f"**{row.home} × {row.away}**")
                st.caption(f"{fmt_date(row.date)} · {row.league}")
    else:
        st.warning("A fonte online está indisponível agora. O scout demonstrativo continua funcionando.")

elif page == "Times":
    st.title("Times")
    st.markdown("<span class='pill-real'>DADOS REAIS</span>", unsafe_allow_html=True)
    league_key = st.selectbox("Campeonato", list(LEAGUES), format_func=lambda k: LEAGUES[k].name)
    try:
        teams = get_teams(league_key, season).sort_values("team")
        query = st.text_input("Pesquisar time", placeholder="Flamengo, River, Coritiba...")
        if query:
            teams = teams[teams.team.str.contains(query, case=False, na=False)]
        if teams.empty:
            st.info("Nenhum time encontrado.")
        else:
            labels = {r.team_id: r.team for r in teams.itertuples()}
            team_id = st.selectbox("Abrir time", teams.team_id.tolist(), format_func=lambda x: labels[x])
            team = teams[teams.team_id == team_id].iloc[0]
            if team.logo: st.image(team.logo, width=90)
            st.header(team.team)
            matches = get_matches(league_key, season)
            summary = team_summary(matches, team_id)
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Jogos", summary["games"]); m2.metric("Vitórias", summary["wins"]); m3.metric("Empates", summary["draws"]); m4.metric("Derrotas", summary["losses"]); m5.metric("Pts/jogo", summary["ppg"])
            if summary["form"]:
                st.write("Forma recente: " + "  ".join(summary["form"]))
            st.subheader("Partidas")
            for row in team_matches(matches, team_id).sort_values("date", ascending=False).head(30).itertuples():
                render_match(row, "team")
    except Exception as exc:
        st.error(f"Não consegui carregar os times: {exc}")

elif page == "Jogos":
    st.title("Jogos")
    st.markdown("<span class='pill-real'>DADOS REAIS</span>", unsafe_allow_html=True)
    selected = st.multiselect("Campeonatos", list(LEAGUES), default=list(LEAGUES), format_func=lambda k: LEAGUES[k].name)
    frames = []
    for key in selected:
        try: frames.append(get_matches(key, season))
        except Exception as exc: st.warning(f"{LEAGUES[key].name}: {exc}")
    matches = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if matches.empty:
        st.info("Nenhuma partida encontrada.")
    else:
        query = st.text_input("Pesquisar time")
        if query:
            matches = matches[matches.home.str.contains(query, case=False, na=False) | matches.away.str.contains(query, case=False, na=False)]
        mode = st.radio("Mostrar", ["Recentes", "Próximos", "Todos"], horizontal=True)
        now = pd.Timestamp.now(tz="UTC")
        if mode == "Recentes": matches = matches[matches.date <= now].sort_values("date", ascending=False).head(80)
        elif mode == "Próximos": matches = matches[matches.date > now].sort_values("date").head(80)
        else: matches = matches.sort_values("date", ascending=False)
        for row in matches.itertuples(): render_match(row, "games")

elif page == "Scout de jogadores":
    st.title("Scout de jogadores")
    st.markdown("<span class='pill-demo'>PLAYER-LEVEL DEMONSTRATIVO</span>", unsafe_allow_html=True)
    st.caption("Os algoritmos são funcionais; jogadores, métricas, valores e eventos desta seção ainda são sintéticos.")
    df, events = load_players()
    discover, profile = st.tabs(["Descobrir", "Perfil"])
    with discover:
        c1, c2, c3, c4 = st.columns(4)
        leagues = c1.multiselect("Ligas", sorted(df.league.unique()), default=sorted(df.league.unique()))
        positions = c2.multiselect("Posições", sorted(df.position.unique()), default=sorted(df.position.unique()))
        ages = c3.slider("Idade", int(df.age.min()), int(df.age.max()), (18, 25))
        max_value = c4.slider("Valor máximo (€ mi)", 0.5, float(max(15, df.market_value_m.quantile(.95))), 6.0, 0.5)
        filtered = df[df.league.isin(leagues) & df.position.isin(positions) & df.age.between(*ages) & (df.market_value_m <= max_value) & (df.minutes >= 600)].sort_values("value_score", ascending=False)
        st.dataframe(filtered[["player", "club", "league", "age", "position", "minutes", "market_value_m", "performance_score", "value_score"]].head(100), hide_index=True, use_container_width=True)
        if not filtered.empty:
            fig = px.scatter(filtered, x="market_value_m", y="performance_score", size="minutes", color="position", hover_name="player", hover_data=["club", "age", "value_score"])
            st.plotly_chart(fig, use_container_width=True)
    with profile:
        labels = {r.player_id: f"{r.player} — {r.club} ({r.position})" for r in df.itertuples()}
        player_id = st.selectbox("Jogador", df.sort_values("player").player_id.tolist(), format_func=lambda x: labels[x])
        player = df[df.player_id == player_id].iloc[0]
        st.header(player.player); st.caption(f"{player.club} · {player.league} · {player.position}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Idade", int(player.age)); m2.metric("Performance", player.performance_score); m3.metric("Valor", f"€ {player.market_value_m:.2f} mi"); m4.metric("Value Score", player.value_score)
        a, b = st.columns(2)
        a.plotly_chart(radar_chart(player, RADAR_METRICS), use_container_width=True)
        b.pyplot(heatmap_figure(events[events.player_id == player_id]), use_container_width=True)
        strengths, weaknesses = player_strengths_weaknesses(player)
        x, y = st.columns(2)
        with x:
            st.subheader("Pontos fortes")
            for name, pct in strengths: st.progress(int(pct), text=f"{name} — P{pct:.0f}")
        with y:
            st.subheader("Pontos a desenvolver")
            for name, pct in weaknesses: st.progress(int(pct), text=f"{name} — P{pct:.0f}")
        st.subheader("Jogadores similares")
        similar = similar_players(df, player_id)
        st.dataframe(similar[["player", "club", "league", "age", "market_value_m", "performance_score", "value_score", "similarity"]], hide_index=True, use_container_width=True)

elif page == "Comparar jogadores":
    st.title("Comparar jogadores")
    st.markdown("<span class='pill-demo'>PLAYER-LEVEL DEMONSTRATIVO</span>", unsafe_allow_html=True)
    df, _ = load_players()
    labels = {r.player_id: f"{r.player} — {r.club} ({r.position})" for r in df.itertuples()}
    ids = df.player_id.tolist()
    a, b = st.columns(2)
    id1 = a.selectbox("Jogador A", ids, index=0, format_func=lambda x: labels[x])
    id2 = b.selectbox("Jogador B", ids, index=1, format_func=lambda x: labels[x])
    p1, p2 = df[df.player_id == id1].iloc[0], df[df.player_id == id2].iloc[0]
    with a: st.plotly_chart(radar_chart(p1, RADAR_METRICS), use_container_width=True)
    with b: st.plotly_chart(radar_chart(p2, RADAR_METRICS), use_container_width=True)
    metrics = [("Performance", "performance_score"), ("Value Score", "value_score"), ("Valor € mi", "market_value_m"), ("xG/90", "xg90"), ("xA/90", "xa90"), ("Passes prog./90", "prog_pass90"), ("Conduções prog./90", "prog_carry90"), ("Interceptações/90", "interceptions90"), ("Duelos %", "duel_win_pct")]
    st.dataframe(pd.DataFrame({"Métrica": [m[0] for m in metrics], p1.player: [p1[m[1]] for m in metrics], p2.player: [p2[m[1]] for m in metrics]}), hide_index=True, use_container_width=True)

else:
    st.title("Dados & fontes")
    st.markdown("""
### Times e partidas
A camada online consulta endpoints JSON utilizados pelo site da ESPN para Brasileirão Série A, Série B e Liga Profesional Argentina. O provider está isolado em data/espn_client.py para poder ser substituído sem reescrever o aplicativo.

### Scouting de jogadores
O módulo de jogadores ainda usa a base sintética original. Isso fica explicitamente sinalizado no produto para não misturar dado real e simulado.

### Arquitetura
A próxima etapa é adicionar uma fonte player-level estável, IDs canônicos entre provedores, banco histórico e modelo de valuation.
""")
