# LATAMDATA v2 — validação em 24/11/2026

**Resultado: verificações técnicas executáveis aprovadas; entrega ainda não liberada para publicação nem para encerrar todas as pendências do PR.** Revisão visual, deploy de teste e autorização dos dados continuam abertos, com os motivos abaixo. Não houve push, edição de PR, alteração de workflows remotos ou deploy.

## Estado auditado e alcance da evidência

- PR: https://github.com/mellinskdata/latamdata/pull/1 — aberto, rascunho, sem merge.
- Head remoto do PR: `7230441aa0944f9c82bf052791a4cdf31f1bd107`, de 20/10/2026.
- `main` observada: `a0f888d28c8d5898ed82ca36bb7407dd03753ed4`, de 23/11/2026.
- Antes da integração, a `main` tinha 34 commits ausentes no PR; o PR tinha dois commits próprios. As diferenças da `main` são os seis CSVs de snapshots, sem mudanças no aplicativo ou nas validações.
- A integração foi feita apenas na branch local `validation/latamdata-v2`, sem conflitos. O ponto local após essa integração é `d7f9c589c6a2307d9e199915b869f66d33f66ccf`.
- Os dados da Série A passaram de 723 para 737 atletas; permanecem 20 clubes. Os snapshots recentes não entraram automaticamente no PR remoto.

| Data | Commit na main | Arquivos alterados |
| --- | --- | --- |
| 20/11 | `7efdd56d06856ebfe2513fb89ce2e76fb0493517` | 4 CSVs |
| 21/11 | `9e0fca14d8cd47eeb233b2c373d888a2d933fc4f` | 4 CSVs |
| 22/11 | `3fdc3a32fb3365dea156d84607615fed9e7690e6` | 4 CSVs |
| 23/11 | `a0f888d28c8d5898ed82ca36bb7407dd03753ed4` | 5 CSVs |

## Situação dos cinco itens do PR

| Item | Situação real | Evidência e limite |
| --- | --- | --- |
| Instalação e build via CI | Aprovado para o head remoto de outubro | Os dois runs abaixo terminaram com sucesso. A cópia corrigida também passou em instalação limpa e build local; suas novas alterações ainda precisam rodar no GitHub depois de publicadas. |
| Interface e filtros desktop/mobile | Parcial | Sete testes React verificam cálculos, filtros e perfil em Node. O navegador não conseguiu acessar a prévia local; nenhuma revisão visual, interação de toque ou screenshot foi aprovada. |
| Termos dos provedores | Revisão concluída; autorização pendente | Os termos consultados restringem extração/redistribuição. A presença dos CSVs no GitHub não comprova permissão. Não foi encontrado documento autorizando o projeto. |
| Deploy Cloudflare Pages | Pendente | Build estático gerado e configuração confrontada com a documentação oficial. Nenhum deploy remoto foi executado; a restrição a alterações externas foi preservada. |
| Fonte ESPN | Consulta e contrato técnico verificados | Consulta de 2026 respondeu, normalização e cache funcionaram; falhas foram testadas sem rede. Isso não constitui garantia de disponibilidade, cobertura futura ou licença. |

CI existente no mesmo SHA `7230441…`, em 20/10/2026:

- [LATAMDATA React checks #2](https://github.com/mellinskdata/latamdata/actions/runs/39509321246): jobs frontend e backend concluídos; `npm install`, `npm run build`, geração de snapshot e testes Python passaram.
- [LATAMDATA CI #13](https://github.com/mellinskdata/latamdata/actions/runs/39509321253): compilação Python e smoke test dos snapshots passaram.

Esses runs não validam a combinação dos snapshots de novembro com as correções desta cópia local.

## Correções preparadas e verificadas localmente

1. **Perfil de xG:** procura a métrica pelo ID 26, em vez de usar a posição 26 de um catálogo que tem 26 entradas. O valor agora distingue xG real, zero e ausência de dado.
2. **Datas e origem:** separa `built_at` da data do commit dos CSVs, registra SHA e hashes das entradas e retira as datas fixas de outubro da interface. Histórico raso ou CSVs alterados resultam em data da fonte indisponível, sem falsa indicação de atualização.
3. **Snapshot antigo:** `predev`, `pretest` e `prebuild` regeneram os CSVs atuais, evitando incorporar silenciosamente um JSON antigo ou importado de HAR. Uma sentinela de arquivo privado foi introduzida somente no arquivo ignorado de teste; o build a substituiu e não a incluiu na saída.
4. **Campos desconhecidos:** partidas e titularidades ausentes nos CSVs deixam de aparecer como zero e usam o indicador de ausência na interface.
5. **API de partidas:** envelopes inválidos passam a retornar 502; eventos malformados são ignorados e placares inválidos não são truncados ou inventados. O TTL usa relógio monotônico. A lista da interface não corta silenciosamente os eventos após 160 registros e rejeita respostas sem um array de partidas.
6. **Reprodução e CI:** lockfile npm, instalação por `npm ci`, sete testes React e cobertura de disparo para o gerador e os snapshots. Checkout com histórico completo permite resolver a data dos CSVs. README atualizado para o estado efetivo da base e de seus direitos.

## Testes executados

| Verificação | Resultado |
| --- | --- |
| Suite original antes das correções | 6 testes Python aprovados |
| Suite Python após as correções | 31 testes aprovados |
| Testes React em memória e renderização no servidor | 7 testes aprovados |
| `npm ci` com o lockfile novo | Aprovado |
| `npm run build` após instalação limpa | Aprovado, Vite 6.4.6 |
| JSON construído | 737 atletas, 20 clubes, 26 definições de métricas, data do commit 23/11/2026 |
| Substituição de JSON antigo no build | Aprovada; sentinela ausente na saída |
| Compilação Python, incluindo módulos Streamlit | Aprovada |
| Smoke test original de analytics nos três snapshots atuais | Aprovado |
| `git diff --check` | Aprovado |

Ambiente local: Node.js 24.22.3, npm 11.19.1 e Python 3.12.14. A CI preparada mantém Node.js 22 e Python 3.12; a execução remota das alterações novas permanece pendente.

Os testes Python incluem saúde HTTP, validação de temporada, respostas vazias, cache por temporada e expiração, timeout, erro HTTP, conexão indisponível, respostas malformadas, placares ausentes/inválidos e metadados de origem. A execução emitiu um aviso de depreciação da combinação instalada Starlette/httpx, sem falha.

Os testes React cobrem busca sem acentos, combinação de clube/posição/minutos, cálculo e ordenação por 90 minutos, mudança de categoria, reinício de paginação e xG do perfil. Não validam layout, acessibilidade completa, exportação por download, impressão, menu móvel ou interação com gráficos.

## Consulta ESPN

Em 24/11/2026, a requisição configurada no adaptador, `dates=2026&limit=500`, respondeu com:

- 383 IDs de evento distintos e 20 equipes.
- 359 registros `Full Time`, 21 `Scheduled` e três `Postponed`.
- 380 pares distintos de mandante e visitante; os três pares repetidos contêm um registro adiado e outro concluído. Portanto, 383 eventos não significam 383 confrontos diferentes.
- Datas retornadas entre 28/01 e 03/12/2026, em UTC. A segunda chamada no mesmo processo usou o cache.

Somente os totais e metadados da consulta foram preservados em `espn-check.json`; não foi incluído um dump de jogos. O endpoint não constitui um contrato documentado de API para o projeto. Uma resposta atual não certifica todos os placares nem cobertura histórica completa.

## Revisão dos direitos e condição de publicação

Fontes primárias consultadas em 24/11/2026:

- [FotMob — termos de 22/10/2026](https://www.fotmob.com/tos.txt), seção de uso de dados: restringe extração, reprodução e redistribuição sem consentimento escrito.
- [ESPN — referência oficial aos termos](https://support.espn.com/hc/en-us/articles/360035445091-Terms-of-Use) e [Disney — versão brasileira](https://disneytermsofuse.com/brazilian-portuguese/), seções 2 e restrições adicionais: restringem reprodução, uso externo e extração automatizada sem autorização.
- A origem exata e a autorização do HAR não foram demonstradas pelo repositório; o HAR não foi usado nesta revisão.

A conclusão operacional é que a publicação dos dados atuais depende de autorização documentada ou substituição da fonte. Atribuição ou acesso público ao endpoint, isoladamente, não comprovam esse direito. A revisão dos termos está feita; a condição de uso ainda não está resolvida.

## Menor sequência restante

1. Aplicar as correções em uma cópia atualizada do PR, após integrar a `main`, e obter os checks remotos para esse novo SHA. O pacote inclui o patch e uma proposta de descrição; nenhum deles foi aplicado no GitHub.
2. Documentar a autorização de FotMob/ESPN/HAR, conforme as fontes efetivamente usadas, ou trocar por dados que permitam a distribuição pretendida. Essa decisão não pode ser suprida por um teste técnico.
3. Revisar em navegador desktop (1440×900) e mobile (390×844, além de 360 px): sete seções, menu, filtros combinados, ausência de resultados, paginação, CSV, comparação, gráficos, perfil/impressão, estados de partidas sem backend e com resposta/erro. Registrar resultado e viewport. Isso pode ocorrer localmente antes de qualquer implantação.
4. Somente com fonte adequada e autorização para alteração externa, executar preview no Cloudflare Pages: raiz `frontend`, build `npm run build`, saída `dist`. Verificar carregamento direto, assets, JSON, atualização da página e comportamento de `/api`; o proxy Vite de desenvolvimento não é uma configuração de produção. [Documentação oficial](https://developers.cloudflare.com/pages/configuration/build-configuration/).
5. Atualizar o checklist do PR com a evidência do SHA final e só então encerrar as pendências correspondentes. Manter o rascunho enquanto esses critérios não estiverem cobertos.
