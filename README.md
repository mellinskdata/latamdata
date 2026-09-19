# LATAMDATA v0.2

Plataforma Streamlit de football intelligence focada em Brasil e América do Sul.

## O que já funciona

- Busca de times
- Página de clube com campanha e forma recente
- Calendário e resultados
- Pesquisa de jogos por equipe
- Central da partida, com estatísticas, escalações e eventos quando a fonte disponibiliza
- Brasileirão Série A
- Brasileirão Série B
- Liga Profesional Argentina
- Scout de jogadores com filtros, percentis, radar, heatmap, similaridade e value score
- Comparador de jogadores

## Dados

A camada de times e partidas consulta endpoints JSON usados pelo site da ESPN e não exige chave. Como não é uma API contratada, a integração fica isolada em `data/espn_client.py` e possui timeout, retry e tratamento de falhas.

A camada player-level ainda usa `players.csv` e `events.csv`, que são dados sintéticos. A interface sinaliza isso explicitamente.

## Rodar

    pip install -r requirements.txt
    streamlit run app.py

## Estrutura

    app.py
    analytics.py
    charts.py
    config.py
    data/
      __init__.py
      espn_client.py
    players.csv
    events.csv
    requirements.txt

## Próximos passos

1. Fonte real player-level.
2. Banco histórico em DuckDB/PostgreSQL.
3. IDs canônicos de jogadores e clubes.
4. Shortlists persistentes.
5. Modelo de valuation e detecção de jogadores subvalorizados.
6. Mais ligas sul-americanas.
