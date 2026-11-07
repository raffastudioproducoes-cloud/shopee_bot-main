# Release Auto Orbital 3.3.0 — preparação 05/11/2026, consolidação 07/11/2026

## Situação e autorização

- **Aprovado pelo proprietário:** Rafa autorizou promoção do conjunto acumulado em `staging` para `main`, SemVer e atualização da documentação do projeto e do Vault.
- **Classificação:** MINOR `3.2.0 → 3.3.0`; funcionalidades compatíveis novas com correções PATCH incorporadas.
- **Estado em 07/11/2026:** branch `release/3.3.0-20261105` candidata à promoção, reconciliada com as PRs #307, #304 e #306 já integradas em staging. Não declarar produção até CI do release, PR de promoção e deploy live com SHA. Acompanhar fechamento no Vault `TASK.md`.
- **Origens conferidas:** `main=561345b102f95979eb979167ec52e9d823681768` (produção 3.2.0); `staging=9eede9d79db65263094c27c43f25a022f9e83ec2` (Render `dep-dbm39ijncjis738ogs10` live) antes do bump. Comparação registrou 72 arquivos diferentes; os 10 commits exclusivos em main, por histórico de merges anteriores, não adicionaram diferenças de arquivo em `staging...main`. A verificação de conflitos deve continuar no PR de promoção.
- **Reconciliação em 07/11:** CI #1028 da PR #307 (base técnica), #1030 da PR #304 (ordem/Shopee Vídeo), #1032 da PR #306 (duas seções) **SUCCESS** nos três jobs obrigatórios. Staging no SHA `6a3b3228936a5860bd03a8060fd183c6c2cdb94d`, Render deploy `dep-dbnc6hp42hec73ca3ik0` **LIVE**, `GET /health` **HTTP 200** com `{"status":"ok"}`. A indisponibilidade de Actions em 05–07/11 foi encerrada; conservar como histórico na issue #305.

## O que compõe a 3.3.0

1. **Análises reais por publicação:** somente `publish_jobs` concluídos pelo Auto Orbital com ID externo confirmado; cache `publication_insights`, consulta oficial específica do post Threads, ranking por post e estado indisponível quando API não fornece dado. Não somar visualizações gerais de conta/página; evitar dupla contagem de IDs externos.
2. **Análises de conta e perfil:** seletor `Todos os perfis`/individual com validação de titularidade no backend, história dos perfis arquivados e respeito a período/rede; não alterna perfil operacional.
3. **Posts e Criar Post:** busca contextual já existente e paginação visual de 15 por página; quota compacta substitui banner de plano; fluxo de campanha ordenado 01–06, com ativação e histórico por último.
4. **Listas:** busca por nome/produtos, ordenação nos dois sentidos para nome/criação/quantidade/edição/campanhas efetivamente ativadas, leitura protegida de uso e quota compacta.
5. **Produtos:** busca semântica segura por termos equivalentes, campo único na TopBar apenas em Meus Produtos, edição de nome/descrição curta, até 5 imagens e 2 vídeos adicionais privados, prévia persistida; IA Gemini opcional para sugerir descrição com revisão manual. Card sem indicadores duplicados.
6. **Planos e interface:** cotas por recurso, comparação Free/Pro/Premium em Configurações, CTA apenas quando existir upgrade, badge visual animada e layout responsivo com movimento reduzido.
7. **Correções:** tratamento do salvamento de personalização sem `.single()` em UPDATE, limpeza de skeleton e detalhes duplicados, isolamento por conta/perfil.
8. **Credenciais:** nove cards em ordem alfabética PT-BR dentro das seções **Já credenciados** e **Ainda não cadastrados**, com classificação pelo cadastro `connected` e não pelo teste recente; IA salva em qualquer provedor conta como cadastrada. Card informativo Shopee Vídeo permanece sem conexão funcional enquanto falta aprovação oficial. Layout responsivo, contagens, estados vazios e retentativa segura. Os seis testes de credenciais agora integram o workflow no runner Node 20.

## Dados, segurança e dependências

- **Banco único:** Supabase `wcentenooirmwwlwlljp`, compartilhado por produção/staging. Migrações aditivas `087_product_personalization.sql` e `088_publication_insights.sql` já verificadas em `public.migrations`. Em `publication_insights`: RLS e acesso exclusivo service_role conforme QA anterior.
- **Agendamentos:** conservar exatamente `auto-orbital-wake-v1` (`*/2 * * * *`) e `auto-orbital-uptime-sample-v1` (`*/12 * * * *`), ativos. A função `app_internal.wake_dispatch_if_needed()` e o `pg_net` não foram migrados nem devem ser duplicados.
- **Campanhas:** manter flags de execução e proteção fail-closed existentes, sem ativar novos disparos ou enviar postagem de teste. Contadores de jobs `unknown` não autorizam replay.
- **Integrações:** Facebook/Instagram ainda sem credenciais sociais conectadas; X bloqueado, TikTok sem fonte de insights validada. Os 14 views de conta Threads e 3 views de conta Facebook mostrados externamente **não** integram os indicadores por post. O post Threads rastreável consultado na API individual mostrou 0 views/likes/replies/reposts; clicks indisponíveis. Não assumir comparabilidade exata entre períodos de postagem e lifetime do post.

## Evidência existente antes da promoção

- **Staging atual:** deploy `dep-dbnc6hp42hec73ca3ik0` do SHA `6a3b322` LIVE, GET público `/health` HTTP 200, resposta `{"status":"ok"}`. Não confundir esta verificação de disponibilidade com teste autenticado de UX.
- **CI GitHub Actions recuperada:** [#1028](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42345512375), [#1030](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42345936793), [#1032](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42346491914) com **success**. #1032 cobriu Node 20 com os seis contratos de Credenciais, Python 3.13 e PostgreSQL isolado. Local: seleção frontend **73/73 PASS** e `tsc && vite build` passou; testes API **1264 PASS**, scheduler **208 PASS/1 XFAIL**, DB 4, SemVer 5, web/CSP 27 foram verificados em #307. Os 23 testes frontend opcionais fora da seleção CI registraram falhas legadas; não declarar suíte opcional integral verde. Runs anteriores sem steps permanecem históricos.
- **Não homologados nesta preparação:** QA autenticado da divisão de credenciais em desktop/mobile, publicação real em Facebook/Instagram/X, pagamento/checkout ou automação de campanhas externas. Sem autorização para testar postagem externa ou ativar pagamentos. Pytest completo da API passou no runner Python 3.13 nas CIs acima.

## Gate de promoção e acompanhamento

1. PR de release com VERSION/CHANGELOG e reconciliação das três PRs anteriores → staging; Render staging `live`, checar saúde.
2. PR `staging → main`, revisar diff/conflitos, SemVer e CI; não ignorar status impeditivo sem decisão.
3. Verificar deploy Render produção `srv-da6vrla6iojc7380a13g`, SHA, `/api/health/ready`, logs e preservação dos dois cron jobs.
4. Atualizar este documento e o Vault `TASK.md`, guia mestre e índice com PRs/SHAs/deploy, classificação dos testes e pendências reais. Não declarar conclusão antecipada.

## Referências

- [CHANGELOG](../CHANGELOG.md), [Guia mestre](GUIA-MESTRE-IA.md), [Análises](ANALISE-REDES-PLANO.md), [Regras](RULES.md).
- PRs de Análises [#298](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/298), [#300](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/300), [#301](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/301), [#302](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/302).
- Vault: `Projetos/ShopeeAutoVendas/40-Guia-Mestre-IA-Auto-Orbital.md`, `TASK.md`, `64-Analytics-Posts-Confirmados-2026-11-05.md`.
