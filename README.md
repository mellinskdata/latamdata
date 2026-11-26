# LATAMDATA v2 — React e API de partidas

Dashboard React/Vite para visão geral, ranking de jogadores e clubes, comparação,
laboratório de gráficos e perfil estatístico. O serviço FastAPI opcional atende
as partidas. O aplicativo Streamlit continua em `app.py`.

## Executar e verificar localmente

Requer Node.js 22 ou superior e Python 3.12. A partir da raiz do repositório:

```bash
python -m pip install -r backend/requirements.txt pytest httpx
python scripts/build_public_snapshot.py
python -m pytest -q tests
cd frontend
npm ci
npm test
npm run build
npm run dev
```

Frontend: http://localhost:5173. Em outro terminal, na raiz:

```bash
uvicorn backend.main:app --reload --port 8000
```

O proxy `/api` do Vite funciona no desenvolvimento. Um site estático precisa de
roteamento próprio para o backend em produção; sem ele, a seção Partidas mostra
a indisponibilidade. `npm run preview -- --host 127.0.0.1` serve o build local.

`npm test` verifica o cálculo e a filtragem do ranking em memória e a renderização
do perfil no servidor. Esses testes não substituem revisão visual ou interação
real em desktop/mobile.

## Dados e limites

`predev`, `pretest` e `prebuild` regeneram o JSON a partir de
`data/snapshots/bra_a_2026.csv` e `team_bra_a_2026.csv`. Assim, um JSON antigo ou
importado manualmente de HAR não é reutilizado silenciosamente no build.
O JSON é ignorado pelo Git.

O JSON registra o horário de geração separadamente da data do commit dos CSVs,
além dos hashes SHA-256 das entradas. Em checkout sem histórico completo ou com
CSVs alterados, a data da fonte é declarada indisponível. A data do commit não
comprova o horário de atualização do provedor.

O catálogo público contém 26 definições de métricas, com disponibilidade variável
por entidade. Os CSVs não fornecem uma classificação verificável nem quantidades
de partidas e titularidades por atleta; esses campos permanecem indisponíveis.
Os dados são snapshots, sem garantia de atualização ao vivo.

O importador `scripts/import_har.py` continua disponível para capturas autorizadas.
O arquivo importado deve ficar fora do repositório público e não é usado pelo
build padrão. A fonte do HAR e seus direitos não foram comprovados nesta revisão.

## Publicação depende de autorização dos dados

Estar versionado no GitHub não concede uma licença de redistribuição.
A revisão em 24/11/2026 encontrou restrições expressas nos termos do
[FotMob](https://www.fotmob.com/tos.txt) e nos
[termos Disney/ESPN](https://disneytermsofuse.com/brazilian-portuguese/).
O [suporte oficial ESPN](https://support.espn.com/hc/en-us/articles/360035445091-Terms-of-Use)
remete aos termos Disney. Não foi encontrada autorização de uso para este projeto.

Antes de publicar os dados, obtenha autorização escrita/licença adequada ou
substitua-os por fonte com redistribuição permitida. Um build técnico aprovado
não resolve essa condição. Não trate os snapshots atuais como base livre.

Para futura implantação no Cloudflare Pages, o diretório raiz do projeto é
`frontend`, o comando é `npm run build` e a saída é `dist`. Isso descreve a
configuração; nenhum deploy foi executado nesta validação.

## Estado da revisão

Consulte [docs/validation/VALIDACAO.md](docs/validation/VALIDACAO.md) para os SHAs
auditados, os testes, as evidências de CI e os itens realmente pendentes.
