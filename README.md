# LATAMDATA

Plataforma de football intelligence e scouting quantitativo focada em Brasil e América do Sul.

## Cobertura inicial

- Brasileirão Série A
- Brasileirão Série B
- Liga Profesional Argentina

## Produto

O LATAMDATA combina uma central de jogos com uma camada própria de análise de atletas.

### Scout de jogadores

- base real de atletas e temporada
- gols, assistências, xG, xA e xGOT
- finalizações e finalizações no alvo
- passe e criação de chances
- dribles
- desarmes, interceptações, recuperações, cortes e bloqueios
- dados de goleiros
- idade, altura, nacionalidade e valor de mercado quando disponível
- percentis por posição
- radar multidimensional
- relatório estatístico detalhado
- mapa de finalizações
- jogadores similares
- comparação lado a lado
- exportação CSV

### Modelos LATAMDATA

A plataforma calcula:

- Impact Score
- Reliability Score
- Value Score
- Opportunity Score
- dimensões de Finalização, Criação, Posse e Defesa
- arquétipos por função
- pontos fortes e fracos
- sinais de gols vs xG e assistências vs xA

Esses índices são modelos próprios e não são notas oficiais das fontes.

### Times e jogos

- pesquisa de clubes
- calendário e resultados
- forma recente
- elenco estatístico
- central da partida
- estatísticas
- escalações
- eventos

## Arquitetura de dados

Jogadores e métricas avançadas são obtidos por uma integração web não oficial com FotMob.

Jogos e match center usam endpoints JSON públicos utilizados pela ESPN.

O acesso a provedores fica isolado em adaptadores para que a fonte possa ser substituída sem reescrever a camada de análise ou a interface.

O projeto também possui suporte a snapshots de jogadores em data/snapshots. A aplicação tenta a fonte ao vivo e pode cair para o último snapshot real disponível. Um workflow diário prepara a atualização desses snapshots.

Não existe fallback sintético para jogadores.

## Rodando

    pip install -r requirements.txt
    streamlit run app.py

## Estrutura

    app.py
    scout_analytics.py
    charts.py
    config.py
    data/
      espn_client.py
      fotmob_provider.py
      snapshots/
    ui/
      common.py
      match_pages.py
      scout_pages.py
    scripts/
      refresh_snapshots.py

## Próximas evoluções

- força relativa de ligas
- histórico por temporada
- shortlists persistentes
- filtros por função tática
- perfis de equipe e Tactical Fingerprint
- relatórios PDF de scouting
- banco PostgreSQL
- modelos de valuation e potencial
- expansão para outras ligas sul-americanas
