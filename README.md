# LATAMDATA

Plataforma em Streamlit para análise de futebol e scouting quantitativo com foco em Brasil e América do Sul.

## Cobertura atual

- Brasileirão Série A
- Brasileirão Série B
- Liga Profesional Argentina

## O que já funciona

- pesquisa de times
- calendário, resultados e central da partida
- forma recente e resumo dos clubes
- elenco estatístico real por clube
- pesquisa e filtros de jogadores
- gols, assistências, xG, xA e outras métricas quando disponíveis
- percentis por posição
- radar estatístico
- mapa de calor de temporada quando disponível
- pontos fortes e pontos a desenvolver
- jogadores similares por distância de cosseno
- comparação lado a lado
- Performance Score
- Value Score experimental quando há valor de mercado disponível

## Fontes

### Times e partidas

A camada data/espn_client.py consome endpoints JSON públicos usados pela ESPN para calendário, resultados e detalhes de partidas.

### Jogadores

A camada data/sofascore_client.py consome endpoints web públicos usados pelo SofaScore para estatísticas reais de temporada e heatmaps quando disponíveis.

Essa integração com SofaScore é **não oficial**. Ela não deve ser tratada como uma API contratada, nem como um dataset open-source/CC0. O provider foi isolado para poder ser substituído futuramente por uma fonte licenciada sem reescrever o restante do app.

O projeto **não possui mais fallback para jogadores fictícios**. Se a fonte real estiver indisponível, a interface mostra a falha em vez de gerar atletas ou números sintéticos.

## Métricas derivadas pelo LATAMDATA

O app calcula sobre os dados obtidos:

- percentis por posição
- Performance Score por perfil posicional
- pontos fortes e fracos
- similaridade estatística
- Value Score experimental

Essas métricas são modelos próprios do projeto e não são notas oficiais das fontes.

## Rodando localmente

    pip install -r requirements.txt
    streamlit run app.py

## Estrutura

    app.py
    analytics.py
    charts.py
    config.py
    data/
      espn_client.py
      sofascore_client.py
    ui/
      common.py
      match_pages.py
      scout_pages.py
    requirements.txt

## Próximos passos

- enriquecer valor de mercado com uma fonte licenciada/confiável
- persistência em PostgreSQL
- shortlists
- histórico por temporada
- força relativa entre ligas
- relatório PDF
- modelos próprios de valuation e potencial
- mais ligas sul-americanas
