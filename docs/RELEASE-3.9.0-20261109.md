# Auto Orbital 3.9.0 — Release MINOR em produção

**Data:** 09/11/2026 (BRT)
**Autorização:** Rafa homologou em staging ("parece que a campanha foi direitinho, tá aprovado") e autorizou expressamente o merge na `main` ("Pode merger com a main. Está aprovado tudo.").
**Repositório:** raffastudioproducoes-cloud/shopee_bot-main
**Versão:** 3.8.0 → 3.9.0 (**MINOR**: funcionalidade compatível nova, conforme `docs/RULES.md`). A PATCH 3.8.1 existiu somente em staging e foi incorporada a esta release.

## 1. Escopo publicado

- **PATCH 3.8.1 (incorporada):** o limite do plano conta somente dias de publicação selecionados; ativação direta sem exigir "Salvar rascunho"; migration 095 (já aplicada no Supabase compartilhado em 09/11 durante o deploy de staging).
- **PR #391:** dias da semana selecionados com o azul padrão (`--gradient-cta`); prazo de espera de 90 s **somente** em `POST /api/campaigns/drafts/{id}/activate` (demais rotas seguem em 30 s) com 504 orientando a conferir a seção 06; painel de andamento da ativação (etapas, cronômetro, barra indeterminada, avisos); confetti no botão ao concluir, desativado por `prefers-reduced-motion`.
- **PR #392:** prévia do calendário e histórico por rede paginados de 10 em 10 com páginas numeradas; contadores da campanha mostram só valores maiores que zero.
- **PR #393:** a seção 06 lista somente campanhas em preparação, ativas ou pausadas; concluídas e canceladas ficam no histórico de postagens.

## 2. Portões e evidências

| Gate | Evidência | Resultado |
|---|---|---|
| CI do PR de promoção (#395) | [run 42652032262](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42652032262) | SUCCESS (API, frontend, F4E/PostgreSQL, staging externo) |
| Gate SemVer do PR | [run 42652032556](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42652032556) | SUCCESS (3.8.0 → 3.9.0) |
| CI push `main` (#1277) | [run 42652476333](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42652476333) | SUCCESS |
| Staging 3.9.0 | deploy Render `dep-dboutjo473hc73b4qss0` (commit `f6b26aa`) | LIVE; smoke de segurança e ZAP passivo SUCCESS |
| Produção | deploy Render `dep-dbov227avr4c73bvifjg` (serviço `srv-da6vrla6iojc7380a13g`) | **LIVE no commit `f3edf13aa617fda890d9ac29b7e28ab6344644bc`** |

Cadeia de PRs: #391 (`efcc5be`), #392 (`b25b312`), #393 (`16521a3`), #394 release/bump (`f6b26aa`), #396 sincronização de histórico (`f829b48`) e #395 promoção `staging → main` (`f3edf13`, **merge commit**).

## 3. Logs de boot da produção (consultados no Render)

- Gunicorn iniciado; worker `PublishingGeventWorker`; migrations já aplicadas e ignoradas, **incluindo `095_campaign_active_weekday_quota.sql`**; scheduler inicializado e iniciado; `Application startup complete`.
- A instância antiga recebeu `term` e pausou o processamento do scheduler, compatível com a troca de instância.
- Nenhum log de nível erro ou crítico na janela do deploy; único aviso foi o de tamanho de chunk do build (conhecido; plano de estabilização, fase 4).

## 4. Histórico `main` × `staging` (lição operacional)

Os squash merges de release deixavam `main` e `staging` com históricos divergentes. O PR de promoção #395 ficou com `mergeable_state: dirty`, e **o GitHub não executa workflows de `pull_request` em PR com conflito**: o gate de SemVer não aparecia. Correção:

- PR #396: merge commit com estratégia `ours` na `staging` (árvore idêntica; a `main` passou a ser ancestral).
- Promoção #395 feita como **merge commit**, não squash. Resultado: árvores de `main` e `staging` idênticas e `staging` é ancestral da `main`.
- **Regra daqui em diante:** promover `staging → main` com merge commit. Squash recria a divergência e o gate de SemVer deixa de rodar.

## 5. Integridade e limites

- Nenhuma migration nova nesta promoção; nenhuma alteração de RLS, cron, `pg_net`, gateway ou segredo; nenhuma publicação social real foi disparada.
- O ambiente desta sessão não alcança a URL pública (tentativa de `curl` retornou falha de conexão). **Não registrar `/health`, `/api/health/ready` ou `/login` como HTTP 200.** O que está comprovado é o deploy LIVE no commit e os logs de boot.
- QA autenticada em produção não foi executada pelo agente; a homologação foi feita por Rafa em staging.
- **Pendência de decisão (Rafa):** existem duas campanhas ativas idênticas "Primeiro teste real" (450 planejados cada), criadas em staging; como staging e produção compartilham o Supabase, o cancelamento de uma delas é decisão de Rafa. Hipótese não confirmada: a primeira ativação excedeu 30 s no proxy, concluiu no servidor, e a segunda criou outra.

## 6. Próximos passos

Plano de estabilização do Vault (`65-Plano-Estabilizacao-Pos-Release-3-8-0-2026-11-09.md`) e achados S-01 a S-06 de `docs/SEGURANCA-AUDITORIA-20261107.md`.
