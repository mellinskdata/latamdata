# LATAMDATA — Web Dashboard v0.2

Nova interface **React + Vite** e um serviço opcional **FastAPI**, preparados para serem integrados ao repositório já existente `mellinskdata/latamdata`, sem substituir o Streamlit.

## Implementado

- Visão geral: indicadores, artilheiros, assistências, xG e classificação
- Ranking de atletas e clubes com seletor de métricas catalogadas da captura (152 no total; 103 preenchidas para jogadores); busca, filtros, mínimo de minutos, por 90 min, ordenação e CSV
- Comparação de até quatro jogadores, radar de percentis por posição e tabela detalhada
- Laboratório: dispersão interativa com eixos configuráveis e ranking em barras
- Perfil de atleta: radar, percentis, estatísticas agrupadas e relatório para impressão/PDF
- Clubes: classificação, resumo de temporada, elenco e estatísticas coletivas
- Partidas: frontend conectado ao adaptador ESPN já presente no repositório original (requer backend integrado e acesso online)
- Identidade LATAMDATA exclusiva, dark mode responsivo para desktop e mobile

## Como rodar o frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse http://localhost:5173. No repositório público, a etapa `predev` transforma automaticamente os snapshots CSV já existentes em JSON compatível caso o arquivo de desenvolvimento não esteja presente.

Para produção estática: `npm run build`. Publique a pasta `frontend/dist` no Cloudflare Pages, com raiz de projeto `frontend`, comando `npm run build` e diretório de saída `dist`.

## Como habilitar o backend (jogos)

O backend também funciona de forma independente. Você pode colocá-lo na raiz do repositório Streamlit sem sobrescrever nenhum arquivo existente:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

O Vite encaminha `/api` para a porta 8000. A API usa um adaptador próprio para consultar os placares ESPN; os dados dependem da disponibilidade do provedor. Em produção, configure o proxy `/api` para o backend publicado. Sem backend, a seção Partidas explica claramente a indisponibilidade e não inventa resultados.

## Dados e advertências de publicação

`frontend/public/data/serie-a-2026.json` contém uma **cópia de desenvolvimento** dos dados do Brasileirão presentes no arquivo HAR fornecido pelo usuário, identificada com a data 20/10/2026. São 676 atletas únicos (678 registros, 2 duplicados), 20 equipes e um catálogo de 152 métricas. Os registros são uma captura histórica, **não** atualização em tempo real. Os dados não foram gerados artificialmente.

**Antes de publicar o dataset em site aberto:** confirme os direitos de redistribuição/licença da fonte original. Para lançamento comercial, substituir por dados licenciados ou pelos snapshots já disponíveis no GitHub do projeto. A interface e os cálculos desta versão são implementação independente, sem reaproveitamento do HTML/CSS do site analisado.

## Integração segura ao GitHub

Recomendação: criar branch `feature/react-dashboard`, adicionar `frontend/` e `backend/`, revisar a licença da base fornecida, testar CI e abrir PR. Não substitua `app.py` ou `data/` do Streamlit. Acesse a plataforma anterior enquanto a transição acontece.

## Limites desta entrega

Não foi possível executar `npm install` neste ambiente (sem acesso externo). A validação da interface é estática, e testes de interação/browser devem ser feitos no primeiro deploy. Não inclui autenticação, banco de dados próprio, atualizações em tempo real ou mapas de finalizações e passes por evento (esses dados não constam na captura do HAR). O endpoint de jogos requer rede e as bibliotecas instaladas.

### Execução no Windows

Você também pode executar `iniciar-windows.bat` (frontend) e, em outra janela, `iniciar-api-windows.bat` (serviço de partidas). É necessário instalar Node.js e Python.

### Atualizar uma captura autorizada

```bash
python scripts/import_har.py caminho/captura.har --output frontend/public/data/serie-a-2026.json
```

O importador extrai somente as estatísticas do Brasileirão, não copia HTML/CSS/JS ou logotipos de terceiros.

### Implantação no GitHub público

No branch público **não inclua o JSON obtido a partir do HAR** sem autorização/licença para redistribuir a base. O script `scripts/build_public_snapshot.py` gera automaticamente uma versão com as métricas presentes nos CSVs já publicados no projeto. Ela é funcional, porém tem menos indicadores do que o conjunto de 152 métricas da captura (e não inclui uma tabela de classificação verificável); por isso, a UI informa a indisponibilidade da classificação até que uma fonte autorizada seja integrada.