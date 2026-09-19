
# ScoutLATAM

MVP de uma plataforma de scouting quantitativo para futebol sul-americano.

## Recursos

- Busca e filtros por liga, posição, idade, minutos e valor de mercado
- Performance Score
- Custo-benefício
- Percentis por posição
- Radar estatístico
- Heatmap médio
- Pontos fortes e fracos automáticos
- Jogadores similares por distância de cosseno
- Comparação lado a lado

## Rodando localmente

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instale:

```bash
pip install -r requirements.txt
```

Execute:

```bash
streamlit run app.py
```

## Dados

`players.csv` e `events.csv` são **sintéticos**, gerados apenas para demonstração.

Formato esperado de `players.csv`:

- player_id
- player
- club
- league
- nationality
- age
- position
- foot
- height_cm
- matches
- minutes
- market_value_m
- performance_score
- métricas por 90

Formato esperado de `events.csv`:

- player_id
- x
- y

O campo deve usar dimensões 105 x 68 no exemplo atual.

## Próximos passos

- PostgreSQL
- autenticação
- shortlists
- histórico por temporada
- filtros por archetype
- força relativa das ligas
- valuation por machine learning
- xG/xA próprios
- relatórios PDF
- importação via API
