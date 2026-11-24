## Entrega

Dashboard React/Vite separado do Streamlit, com visão geral, ranking, comparação, laboratório, perfil, clubes e API opcional FastAPI para partidas.

## Estado comprovado em 24/11/2026

- [x] CI do head remoto `7230441…`: build React e testes Python aprovados em 20/10.
- [x] Fonte ESPN: consulta atual respondendo; testes de normalização, cache e falhas executados na cópia local.
- [x] Revisão dos termos dos provedores concluída: autorização de redistribuição não comprovada.
- [ ] Integrar e publicar as correções locais, com novos checks de CI para o SHA resultante.
- [ ] Revisão visual e interação real em desktop/mobile.
- [ ] Documentar licença/autorização dos dados ou substituir a fonte.
- [ ] Deploy de teste Cloudflare Pages e validação do roteamento da API em produção.

## Correções locais preparadas

Perfil de xG por ID da métrica, datas de origem separadas da geração, regeneração obrigatória do snapshot no build, campos desconhecidos sem zeros fictícios, API mais robusta e lockfile npm. Na cópia integrada à main de 23/11, passaram 31 testes Python, sete React e instalação/build limpos.

Esses resultados locais não são checks remotos do PR. O pacote de validação não realizou push ou deploy, e a descrição proposta precisa ser atualizada quando as mudanças forem publicadas.

## Dados

O build padrão usa os CSVs existentes; não incorpora o HAR. Isso não torna a base livre para redistribuição. Os termos FotMob e Disney/ESPN exigem análise da autorização aplicável. Não há classificação verificável nem contagem de jogos/titularidades individuais nos CSVs.

## Evidências

- https://github.com/mellinskdata/latamdata/actions/runs/39509321246
- https://github.com/mellinskdata/latamdata/actions/runs/39509321253
- `docs/validation/VALIDACAO.md`
