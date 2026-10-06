# MEMORY — Shopee Auto Vendas

> Estado atual do projeto AGORA. Fonte primária: vault Obsidian
> `Projetos/ShopeeAutoVendas/00-INDICE-Estado-Atual.md` (cruzado com código + consulta SQL
> read-only ao Supabase pelas sessões anteriores) + verificação direta do código nesta
> sessão (2026-09-29). Este arquivo é um resumo local; o vault continua sendo a fonte viva
> mais detalhada — não duplicar histórico de sessão aqui, só o estado atual.

## Repositório

- `C:\Users\rafae\Documents\Projetos\ShopeeAutoVendas\shopee_bot-main`, branch `main` (trabalho em `feature/*`; v2.0.0, ver `CHANGELOG.md`).
- Hospedagem: Render (Free), `https://shopee-bot-fj0w.onrender.com`. Banco: Supabase
  (projeto `autovendas`).
- Flask (legado, produção) e FastAPI (novo) coexistem no **mesmo container Docker** —
  implementado no código (Fase 8.1), validação em produção real ainda pendente.

## Redes sociais conectadas — estado real (não o desejado)

| Rede | Estado real |
| --- | --- |
| **Threads** | Único caso com `access_token` de usuário de fato salvo no Supabase. Publicação real em produção não confirmada nesta verificação. |
| **X (Twitter)** | App único configurado (env vars), botão "Conectar X" existe no frontend, mas `user_access_token` está nulo — nenhum usuário concluiu o OAuth. |
| **Instagram** | Mesma situação do X — app configurado, `user_access_token` nulo. |
| **Facebook** | Migrado de token de Página colado manualmente para OAuth de app único (reaproveita o app do Instagram). Credencial nunca validada com sucesso confirmado ("Testar conexão"). |
| **TikTok** | App único configurado, domínio verificado no painel TikTok for Developers. `user_access_token` nulo. Aprovação de parceiro para "Direct Post" público pode ser um bloqueio adicional externo (`apis/tiktok.py`, `.env-example`). |
| **Kwai** | Sem API pública de postagem confirmada (só API de anunciantes/ads). Frontend mostra "em breve" para usuário comum. |

Só existe **1 usuário em produção** (`rafastudio`, ADMIN) — confirmado via SQL read-only.

## Decisões importantes recentes (mais recente primeiro)

1. **Migração app-por-usuário → app-único de OAuth** (X, TikTok, Instagram, depois
   Facebook) — o dono do SaaS registra um único app por rede; o usuário final só clica
   "Conectar" e autoriza, nunca cola client_id/secret. Detalhe completo:
   `27-Migracao-App-Unico-OAuth.md` (vault). Facebook exigiu reforma maior: o mecanismo
   anterior (App Access Token + `/me/accounts`) só via Páginas do próprio app, não de
   usuários do SaaS — precisou de OAuth de usuário de verdade.
2. **Histórico de requisições (`request_logs`)** — a pedido do dono do projeto ("não quero
   mais passar print de cada erro"), toda requisição à API nova é registrada (método, path,
   status, duração, usuário, redirect de callback OAuth). Desligado por padrão, ligado em
   produção via `REQUEST_LOGGING_ENABLED=true`. Detalhe: `28-Historico-de-Requisicoes.md`
   (vault).
3. **Coexistência no mesmo container** em vez de dois Web Services Render separados —
   decisão por custo/complexidade (plano Free do Render).
4. **Scheduler in-process** mantido (ADR 19, vault) — sem worker separado; gatilho de
   revisão ainda não disparou.
5. **TikTok/Kwai virarem "em breve" para usuário comum** — última mudança visível no
   `git log` (`514d84a`), movidos para o fim da lista de credenciais no frontend.

## O que falta (real, não aspiracional)

- Cadastrar a callback URL de cada rede no painel de desenvolvedor correspondente (X
  Developer Portal, Meta for Developers, TikTok for Developers) — a env var já está no
  Render.
- Clicar "Conectar" e autorizar de fato em X, Instagram e TikTok — ação humana, não código
  faltando.
- Validar em produção real no Render que o subprocesso uvicorn sobe corretamente e que
  `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` estão configurados.
- Testar publicação real de Threads e Facebook em produção (credenciais existem, nenhum
  sucesso confirmado até a última verificação do vault).
- Recolar o Client Secret do TikTok na tela de credenciais (não dá para inspecionar um
  segredo cifrado às cegas para confirmar se ainda carrega espaço em branco).
- Kwai permanece fora até existir API pública de postagem confirmada — decisão antiga, não
  pendência nova.

## Nota de precisão sobre o contexto desta tarefa

O contexto fornecido junto com a instrução desta rodada de documentação afirmava que
"Threads, X, Facebook, Instagram — funcionando end-to-end (OAuth completo, testado e
confirmado)". A evidência real (código + consulta SQL ao Supabase, registrada no vault em
2026-09-28) **não confirma essa afirmação**: só o Threads tem token de usuário de fato salvo.
As outras três têm o mecanismo de OAuth implementado e a UI pronta, mas nenhum usuário
completou a conexão. Esta tabela e o restante do documento refletem o estado real, não o
contexto inicial.

## Atualização 2026-10-05 (nota datada; o conteúdo acima é de 2026-09-29)

- **Branch de trabalho**: `chore/phase-12-integration` (worktree `wt-int`). Segundo
  `git log main..HEAD`, estes commits ainda não estão em `main`; `VERSION` segue 2.0.0 e as
  mudanças estão em `CHANGELOG.md` como "Não lançado".
- **Feito no código desta branch**: multi-perfil completo (`profile_id` em 16 tabelas, migrações
  até 039, backup/restore e bots por perfil), UI de perfis (editar/excluir/ativar/TopBar),
  segurança do servidor (claim `pwv`, validação do `profile_id`, trigger 037, rate limits),
  Dockerfile não-root + `HEALTHCHECK`, gunicorn com timeout e supervisão, CI/CD endurecidos.
- **Estado das redes**: sem alteração desde a verificação de 2026-09-28 (só o Threads tem token
  de usuário salvo); esta rodada não consultou o Supabase.
- **Pendências manuais de Rafa (não são código)**:
  - Env vars do serviço `shopee-bot-staging` no Render (copiar as de produção).
  - Trocar o branch de produção do serviço no Render de `master` para `main`.
  - Branch protection: exige GitHub Pro ou repositório público (GitHub Free não oferece em repo privado).
  - Secret `RENDER_STAGING_DEPLOY_HOOK_URL` no GitHub (só se quiser deploy automático de staging).
  - Cadastrar as callback URLs de cada rede (X, Meta, TikTok) nos painéis de desenvolvedor.
  - Conectar X, Instagram e TikTok (ação humana: clicar "Conectar" e autorizar) e recolar o Client Secret do TikTok.
  - Aplicar as migrações 037, 038 e 039 no Supabase (ver `docs/RULES.md` item 11) e conferir disco/permissão de escrita do container não-root.
  - Merge dos PRs da branch `chore/phase-12-integration` em `main`.

## Referências

- Vault Obsidian: `00-INDICE-Estado-Atual.md` (fonte viva mais detalhada, rede a rede,
  cruzada com Supabase), `27-Migracao-App-Unico-OAuth.md`, `28-Historico-de-Requisicoes.md`,
  `26-Deploy-Render.md`
- `docs/ROADMAP_MIGRACAO.md`, `docs/CHECKLIST_MIGRACAO.md`
