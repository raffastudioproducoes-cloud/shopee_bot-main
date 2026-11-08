> **08/11/2026 — AUTO ORBITAL 3.6.0 EM PRODUÇÃO:** após autorização de Rafa, [PR #357](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/357) promoveu o código testado na staging para `main` SHA `699e81bd18e2b12fc3824f914045627a45844cc2`, com CI/SemVer verdes. Render `dep-dbod0q7b9u1s73dhci7g` **LIVE**; `/health` e `/api/health/ready` OK; login exibe **3.6.0**. A versão traz download seguro da foto Shopee e herança de descrição de Produtos para novos posts/campanhas, sem alterar o produto com edições/IA locais. QA autenticada e integrações externas permanecem pendentes. [Release e evidências](docs/RELEASE-3.6.0-20261108.md), [contrato detalhado](docs/PRODUTOS-DESCRICOES-CAMPANHAS-20261108.md). Todas as notas abaixo com versões antigas são registros históricos.

> **05/11/2026 — Editor de produtos (apenas staging, registro histórico):** personalização inclui botão explícito “Selecionar imagens ou vídeos” para PC/celular (5 imagens extras/2 MP4), além de gerador Gemini de descrição curta. O seletor Casual/Profissional/Divertido/Persuasivo e o botão são o mesmo componente de Criar Post; a API existente `POST /posts/generate-copy` aceita `description_only=true`, usando credencial Gemini do usuário, sem links e com até 280 caracteres ponderados, sem salvar automaticamente. URL Shopee, comissão e preços imutáveis. Sem migração, ambiente novo, crons ou mudança de main; versão oficial 3.2.0, MINOR 3.3.0 candidata pós-aprovação.

> **Dashboard por conta — PR de staging #265 (04/11/2026, homologação pendente):** visão geral soma informações por titular em todos os perfis (Free 1, Pro até 3, Premium até 5, ADMIN conforme política), inclusive dados históricos desvinculados de perfis excluídos; os módulos operacionais continuam isolados por perfil. Postagens e atividades recentes exibem dados da conta, e ações rápidas abrem os fluxos de criação corretos. **Ressalva de integridade:** campanhas F4E ainda podem ser apagadas em cascata por `DELETE` físico do perfil; este PR não modifica exclusão, banco, serviços, cron ou `main`. Não excluir perfis para homologar essa retenção até solução própria aprovada. [PR #265](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/265).

> **Operação 04/11/2026 — disponibilidade contínua:** `main` = clientes/produção, `staging` = desenvolvimento e QA, Supabase/Postgres = **único banco compartilhado**. Nenhuma operação de desenvolvimento pode pausar produção ou serviços comuns. Release com SemVer pré-definido, CI, promoção staging→main e smoke sem interrupção. Parada planejada somente com autorização de Rafa e aviso 24h antes, seguido de aviso de retorno. Render Free atual não garante 24/7 por hibernação; upgrade pago depende de aprovação. Ver AGENTS.md/TASK.
> **Release concluída 04/11/2026 — v3.1.0 EM PRODUÇÃO:** campanhas F4E integradas na `main` pelo [PR #248](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/248), SHA `5e9cae5`, após resolução de conflitos com [PR #250](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/250). CI #887 SUCCESS, Render produção `dep-dblbb3o473hc73b0gqkg` LIVE, scheduler iniciado e `/api/health/ready` HTTP 200 `status=ok`. Somente os seguintes **gates de aceite F4E** ficam abertos, por escolha de Rafa: teste manual, gateway de pagamento e confirmação externa de publicações nas redes. Não há checkout real validado ou postagem externa comprovada nesta release; as notas abaixo são registros históricos de instantes anteriores.
> **04/11/2026, atualização de execução F4E:** uma campanha ADMIN de homologação foi ativada em staging com autorização específica de Rafa, 1 publicação Threads prevista às **01:45 BRT** de hoje. Banco confirmou mídia/OAuth verificados e `post`/agenda/job com origem `campaign`; `pending` até o horário, entrega externa ainda sem confirmação. Acompanhamento agendado para 01:55 BRT. `main` não mudou; versão 3.0.0.
> **Atualização de homologação (04/11/2026):** PR #245 merged em `staging` (`4a4e0ab`), CI #877 SUCCESS, Render `dep-dblaq067bikc73affoh0` LIVE. Scheduler reativado, `/api/health/ready` ok e tela ADMIN funcionando; produção não foi modificada. Rascunho único de teste Threads salvo para disparo real, **ainda não ativado**. E2E externo e promoção main seguem pendentes; `VERSION=3.0.0`.

> **Estado operacional 04/11/2026:** a F4E (campanhas com reserva por rede/dia, Storage privado, OAuth, executor, pausa/retomada e histórico) está integrada **somente no staging** (PR #243, migrations 076–079 no Supabase). A correção HTTP/2 do PR #244 está LIVE. Após autorização de Rafa, `SCHEDULER_ENABLED=true` reativou o scheduler de staging em `dep-dblakvjm8hqs738nl8h0`; o cron de recuperação voltou a avançar. Produção permanece na `main` com o fluxo de posts legados. Envio real de campanha, conciliação de 12 resultados `unknown`, pagamento e promoção para produção seguem pendentes. `VERSION=3.0.0`; veja `docs/TASK.md`.

> **F4E-2B3 (03/11/2026, proposta em revisão):** identidade composta dos pais e testes SQL isolados, sem integração ao executor, DDL no Supabase ou campanhas executáveis. [Matriz de pontos de proteção e gates](docs/F4E-2B3-PROPOSTA-IDENTIDADE-PAIS-20261103.md). CI/PR ainda pendentes neste registro; VERSION=3.0.0.

> **F4E-2A PRE-DEPLOY (PR #231):** preflight autenticado de leitura parcial para rascunho e revisão, política de plano, cronograma e volume por rede. Retorna `preflight_only`, `checks_complete=false`, `reservation_available=false`, `reserved=false`, `activated=false`; não reserva, não chama RPC, não gera jobs/posts e não prova OAuth, retenção física de mídia ou vaga concorrente. Antes de qualquer reserva/execução: proteger mídia e rascunho contra exclusão concorrente, rever writes diretos service_role e validar guardas de dispatch em ambos ambientes. CI, revisão e deploy ainda não confirmados neste registro; `VERSION=3.0.0`.

> **03/11/2026 — Fechamento operacional F4E-1: integrada em staging e LIVE (atualização posterior ao PR draft).** [PR #229](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/229) squash `24c45b671e416d071c80c1c914eecaf6344db0b9`, [CI #764 SUCCESS](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41702740725) com PostgreSQL 16. Render `dep-dbl3aibbc2fs738kfllg` LIVE nesse SHA; navegador confirmou `/health` e `/api/health/ready` = `{"status":"ok"}`. A migration `20261103191911` está aplicada ao Supabase compartilhado e a `074_f4e1_inert_campaign_reservations.sql` registrada uma vez em `public.migrations` (boot seguro); reservas e ocorrências 0/0 pós-deploy, RLS ativo sem policies, acesso anon/authenticated negado. **Não há executor F4E, campanhas ativadas, agendamentos/jobs/posts ou cobrança; sem promoção de código a main/produção.** F4E-2, barreiras de dispatch, validação por rede/OAuth/mídia, decisão de downgrade e QA de planos são tarefas futuras sujeitas a nova aprovação. Rafa confirmou em mobile tags, mensagens, criação e separação de perfis; escolha de planos ainda indisponível. `VERSION=3.0.0`. Esta nota de fechamento prevalece sobre qualquer registro histórico abaixo que diga “PR draft”.

> **03/11/2026 — F4E-1: DDL inerte aplicada ao Supabase compartilhado, ainda em PR draft.** Por coordenação de Rafa, a migration Supabase `20261103191911 / 074_f4e1_inert_campaign_reservations` foi aplicada; `public.migrations` recebeu `074_f4e1_inert_campaign_reservations.sql`. A inspeção reportada após a aplicação encontrou zero reservas e ocorrências, RLS ativo sem policies, anon/authenticated sem acesso e service_role com SELECT/RPC, sem DELETE. Draft legado preservado. Não foram criados jobs F4E, executor ou publicações, nem houve merge ou deploy de main/produção. [PR draft #229](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/229); [CI #755](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41701678290) verificou a proposta anterior. Rafa confirmou em mobile apenas tags, mensagens e perfil; QA visual completo em desktop não foi comprovado, e escolha de plano permanece futura. F4E-2, validação por rede e retenção física de mídia continuam pendentes. VERSION permanece 3.0.0. Esta nota prevalece sobre estados anteriores abaixo.

> **03/11/2026 — F4D **integrada apenas em staging**: [PR #219](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/219) squash `9adbd5a455022acecc580c7daba75bd445a8ec22`, [CI #728](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41696637695) SUCCESS (API 1.165; frontend 38 contratos + TypeScript/Vite; scheduler 175 + 1 xfailed; SQL 4; segurança/web 27; externo skipped esperado). Render staging `dep-dbl2obp5efls73f9durg` LIVE no mesmo SHA; browser confirmou `/health` e `/api/health/ready` como `{"status":"ok"}`. UI autenticada desktop/mobile ainda não verificada. Nenhuma migration/SQL/ativação/job/post externo, cobrança ou alteração de `main`/produção. `VERSION=3.0.0`.**
>
> **F4E auditada somente leitura: dispatch central de produção pode reivindicar agendamentos com origem staging se a configuração de dispatch estiver habilitada (flag real Render não verificada); separar F4E-1 inerte/transacional de F4E-2 execução protegida e não inserir campanha em `schedulers`/`publish_jobs` antes de guardas simultâneos nos dois ambientes. Não houve DDL nem autorização de ativação.**

> **03/11/2026 — F4C2 guardas de campanha integradas em staging (evidência pós-merge):** [PR #217](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/217) squash-merge **somente staging** SHA `d80f60d289c314064fa6ac728c4b23f898a767c2`, [CI #722](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41692608479) SUCCESS (API 1.157, scheduler 175 + 1 xfailed, SQL 4, web 27, frontend/build aprovados). Render staging `dep-dbl2d1k9v7es73datmag` LIVE no SHA; navegador confirmou `/health` e `/api/health/ready` = `{"status":"ok"}`. Free bloqueado para novas campanhas; Pro até 15 dias e 3 unidades de rede/dia, Premium até 30 dias e 15; ADMIN bypass comercial com ownership e segurança. **F4C2 é preparatória:** não há ativação nem automação operacional; 2/5 campanhas ativas exigem reserva atômica F4E. Nenhuma migration 074/SQL, postagem ou alteração de `main`/produção. `VERSION=3.0.0` inalterada. QA de usuário autenticado e concorrência real ainda pendentes. Esta nota prevalece sobre fotografias pré-merge abaixo.

> **03/11/2026 — F4C2, histórico da preparação pré-merge:** campanhas Free bloqueadas nas entradas de prévia/criação/edição/upload; Pro até 15 dias inclusivos e 3 publicações/dia, Premium até 30 dias e 15/dia; cada rede conta uma unidade no rascunho com planejamento. ADMIN ignora cotas comerciais, não segurança/ownership nem teto absoluto de 30 dias. Política de conta e limites auditados são relidos no servidor sem cache. Leitura/exclusão de rascunho legado permanecem disponíveis após downgrade. Não há ativação nem automação operacional: limite de 2/5 campanhas ativas ainda depende de reserva transacional na F4E; consumo retorna `null`, nunca zero fictício. Sem migration 074 nem mutação de banco. Ver [contrato F4](docs/PLANOS-F4-POLITICAS-E-FASES-20261103.md), seção 8.

> **Auto Orbital — F4C1 concluída em staging (03/11/2026):** PR #215 squash-merge apenas em staging SHA `397f0f760570c7aa39a1756f6a9e05deaf205d2f`, CI #717 verde, migration 073 autorizada e aplicada (Supabase `20261103175106`, `public.migrations` id=68), Render `dep-dbl20fss728c739c6kag` LIVE, `/health` e `/api/health/ready` = `{"status":"ok"}`. Sem post externo nem promoção `main`/produção; `VERSION=3.0.0`. Cotas protegidas por RPC; F4C2 campanhas/automação é etapa posterior. Ver [contrato F4](docs/PLANOS-F4-POLITICAS-E-FASES-20261103.md) e `CHANGELOG.md`.

> **07/11/2026 — diagnóstico de credenciais ADMIN (candidato staging):** painéis IA/Shopee recolhíveis e compactos, logos e grade social somente de status; único botão de teste auditável, sem formulário de overrides na tela. [Contrato e limites](docs/ADMIN-DIAGNOSTICO-CONEXOES-20261107.md). `VERSION=3.4.0` mantida; main não autorizada nesta tarefa.

> **07/11/2026 — proposta em staging:** a próxima versão da Shopee Afiliados usa App ID/Secret global de ADMIN e ID de afiliado individual por conta; gera links `an_redir` sem reutilizar links do administrador. Migração 090 aditiva e homologação de comissão antes de produção. Veja [contrato Shopee](docs/SHOPEE-API-GLOBAL-ID-AFILIADO-20261107.md). `VERSION=3.4.0` permanece vigente até aprovação da release 3.5.0.

> **Entrada obrigatória para agentes e IAs:** leia primeiro [AGENTS.md](AGENTS.md) e o [Guia Mestre de Contexto](docs/GUIA-MESTRE-IA.md) — propósito, localização do Vault, arquitetura, módulos, fluxos, APIs, segurança, RLS, custos, limites e método de verificação. Documentos históricos não substituem o código implantado.

<div align="center">

> **Homologação de posts, 02/11/2026:** PR [#186](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/186) implementa geração de uma descrição de IA por rede, limites validados e avisos de compatibilidade de mídia. Somente staging, sem publicação real de teste; [detalhes](docs/POSTS-COPY-IA-POR-REDE-20261102.md).

# Shopee Auto Vendas

> **07/11/2026 — Interface de Perfis na candidata 3.5.0 (somente staging):** `/profiles` organiza o cadastro dentro do card principal (foto/nome, cota e campos editáveis da conta titular); cards secundários exibem apenas foto/nome. O e-mail de login continua protegido por verificação e não pode ser alterado neste formulário. Nenhum gateway, banco, cron ou produção foi alterado. Ver [contrato da identidade](docs/CADASTRO-IDENTIDADE-PLANOS-20261107.md) e [`VERSION`](VERSION), atualmente `3.4.0`.

> **07/11/2026 — Análises (staging):** [PR #326](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/326), CI #1077 e deploy Render LIVE levaram o catálogo de nove redes à página, sem lojas. Após feedback de Rafa, os cards redundantes do topo foram removidos: **Rede** é o único filtro e **Detalhamento por rede** lista nove redes quando em “Todas”, com traços/status para integrações futuras sem números fictícios. [Matriz de dados por rede](docs/ANALISE-REDES-COBERTURA-20261107.md). `VERSION=3.4.0`, candidata 3.5.0; ajuste posterior ainda exige CI/deploy de staging e QA mobile, não promover `main` automaticamente.

### Divulgação automática de afiliado, do garimpo ao post.

[![React](https://img.shields.io/badge/React-19-06B6D4?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vite.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-38BDF8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3FCF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![Render](https://img.shields.io/badge/Render-deploy-46E3B7?logo=render&logoColor=white)](docs/ROADMAP_MIGRACAO.md)
[![License](https://img.shields.io/badge/license-proprietary-0F172A)](#licença)

</div>

---

## Sumário

1. [Apresentação](#apresentação)
2. [Objetivo](#objetivo)
3. [Funcionalidades principais](#funcionalidades-principais)
4. [Tecnologias](#tecnologias)
5. [Estrutura do projeto](#estrutura-do-projeto)
6. [Instalação](#instalação)
7. [Desenvolvimento](#desenvolvimento)
8. [Build](#build)
9. [Testes](#testes)
10. [Deploy](#deploy)
11. [Banco de dados](#banco-de-dados)
12. [Segurança](#segurança)
13. [Processo do projeto (ciclo operacional)](#processo-do-projeto-ciclo-operacional)
14. [Documentação](#documentação)
15. [Roadmap da migração](#roadmap-da-migração)
16. [Licença](#licença)
17. [Contato](#contato)

---

## Apresentação

> **07/11/2026 — Shopee Open Platform:** antes da integração com Shopee Vídeo de afiliados, o cadastro externo será tratado na ordem **relatório de pentest rejeitado → documentos pendentes → criação de aplicativo**. O motivo da rejeição não aparece nas capturas; não há app cadastrado na conta mostrada. [Checklist de regularização](docs/SHOPEE-OPEN-PLATFORM-CADASTRO-20261107.md) e [contrato de vídeo afiliado](docs/SHOPEE-VIDEO-AFILIADOS-GATE-20261107.md). Sem alterar app, tokens, envios ou produção até autorização e comprovação externas.

**Shopee Auto Vendas** é uma plataforma que automatiza a divulgação de links de
afiliado da Shopee (e, em expansão, de outras redes sociais). Um único painel
cobre o fluxo inteiro: garimpar produto na Shopee Open API, gerar o texto do
post com IA, agendar ou publicar na hora, e acompanhar tudo pelo histórico de
atividades.

Hospedado em **Render (Free)**: `https://shopee-bot-fj0w.onrender.com`.
Banco: **Supabase** (Postgres gerenciado).

> **Em migração**: o Flask (`web/`) segue no mesmo container servindo o proxy `/api/*`,
> o scheduler e o build do React; o painel Jinja legado fica desligado por padrão
> (`LEGACY_PANEL_ENABLED=false`) e o painel principal é o React (`frontend/`). Ver
> [Roadmap da migração](#roadmap-da-migração).

**Versão atual:** `3.6.0` na `main` e na `staging` (fonte oficial: [`VERSION`](VERSION), histórico: [`CHANGELOG.md`](CHANGELOG.md)). A release **3.6.0** incorporou download autenticado da imagem Shopee e cópia da descrição-base em novos posts/campanhas sem sobrescrever o catálogo; a **3.5.0** acumulou interfaces, análises e identidade cadastral, e a **3.4.0** centralizou a gestão de IA em ADMIN. Gateway de pagamento, teste manual autenticado e confirmação externa de publicações permanecem pendentes. O vídeo continua sem scanner antivírus isolado (ver `docs/POST-MEDIA-SECURITY.md`).

**Campanhas F4E em produção:** o menu possui `Criar POST` e prévia de campanha com ordem de produtos e calendário; a prévia isoladamente não ativa publicações. O ciclo de ativação, reserva e execução de campanha foi integrado em produção na v3.1.0, respeitando guardas de plano e ambiente. Evidência externa de postagem e cobrança por gateway dependem dos gates de aceite ainda abertos. Ver [documentação da campanha](docs/CAMPANHA-POR-LISTA-PREVIA-20261103.md), [TASK](docs/TASK.md) e o bloco `[3.1.0]` do `CHANGELOG.md`. O ícone do menu usa Lucide `square-pen` do design system.

**Governança de versão e deploy:** cada PR de código documenta sua mudança em `[Não lançado]`; após CI, homologação técnica no `staging` e aprovação do proprietário, uma PR `staging` → `main` promove a entrega. A versão atual `3.6.0` foi promovida pela PR #357 após CI/SemVer, e está LIVE no Render no deploy `dep-dbod0q7b9u1s73dhci7g`. Próximas alterações devem ser classificadas conforme SemVer sem presumir que testes externos já foram executados.

**Histórico anterior:** `2.6.0` (15/10/2026) trouxe painel administrativo, métricas/capacidade, separação cliente/`/admin` e overrides de credenciais. `2.5.0` adicionou splash, esqueletos de carregamento e correções de segurança. `2.4.0` (14/10/2026) aplicou a identidade AUTO ORBITAL, PWA, Ajuda/FAQ, documentos legais e callbacks Meta/Threads. O app Meta segue condicionado à aprovação da plataforma; X continua desabilitado pela regra do produto e TikTok foto é melhoria futura. O histórico de integração multi-perfil permanece preservado em `CHANGELOG.md`.

**Limitações de validação:** deploy/CI e autenticação não substituem teste externo de publicação; Threads 403 continua sob acompanhamento. `staging` e `main` usam o mesmo Supabase, e a decisão posterior de centralizar os disparos na produção demanda ajuste técnico próprio. O acesso de revisão `RafaelTesteCliente` deve ser preservado.

## Objetivo

Tirar o trabalho manual de quem divulga produto de afiliado:

- **garimpar** produto elegível (comissão, vendas, categoria) sem sair do painel;
- **gerar copy** com IA (Gemini) por persona, sem escrever do zero toda vez;
- **publicar agora ou programar recorrência**, com acompanhamento de ocorrências, falhas e resultados incertos;
- **organizar** produtos em listas reaproveitáveis entre posts;
- **conectar credenciais** de cada rede social de forma cifrada, nunca expostas de volta na tela;
- **acompanhar** o que foi feito por atividade, com histórico auditável.

## Funcionalidades principais

| Módulo | Recursos |
| --- | --- |
| **Garimpo** | Busca de produtos na Shopee Open API por categoria, palavra-chave, comissão mínima e vendas |
| **Produtos** | Cadastro, edição, listagem com busca — origem manual ou vinda do garimpo. Aba "Pesquisa Avançada" busca em tempo real no catálogo da Shopee (API de afiliados), com filtros e importação direta pro catálogo pessoal |
| **Listas de produtos** | Agrupamento de produtos reaproveitável entre posts |
| **Posts** | Criação de post com um produto, publicação imediata ou recorrente (até 7 dias, até cinco horários diários), histórico de ocorrências e tratamento de resultados incertos. Preview e variantes por rede com mídia privada e adaptação conforme compatibilidade; sucesso real depende de OAuth/escopos e teste na rede. |
| **Copywriter IA** | Geração de texto de post por persona com IA fornecida pela plataforma; o ADMIN gerencia Gemini/OpenAI/Anthropic em `/admin/credentials` (`apis/llm.py`, `api/routers/platform_ai.py`). |
| **Credenciais** | Shopee, Threads, X, Facebook, Instagram, TikTok, Kwai — cifradas em repouso (Fernet), nunca reexibidas |
| **Atividades** | Histórico auditável de ações do usuário |
| **Perfis e Configurações** | Até 3 perfis por conta (1 principal + 2 secundários, com avatar), editar/excluir/ativar sem recarregar a página e perfil ativo na TopBar; Shopee, assistente/IA e catálogo de produtos são compartilhados pela conta. Listas, posts, mídias, credenciais sociais, dashboard operacional, notificações, logs e backup/restore usam o perfil ativo (ver [Multi-perfil](#multi-perfil)). Página `/settings` com troca de senha. Administração de acesso (ADMIN/USER) na página Perfis |
| **Scheduler** | Jobs agendados in-process (APScheduler, jobstore em Postgres) — ADR em `19-ADR-Scheduler-In-Process.md` (Vault) |

## Tecnologias

**Frontend em produção hoje** (Flask + Jinja2):
- Flask 3.x + Jinja2 + Alpine.js, Tailwind CSS (build local, sem CDN)
- Gunicorn + gevent, deploy via Docker no Render

**Frontend novo** (em migração, ver [Roadmap](#roadmap-da-migração)):
- **React 19** + **TypeScript** estrito
- **Vite 6** + **TanStack Router** + **TanStack Query**
- **Tailwind CSS v4**
- **Zustand** (estado de auth)
- **Lucide React** (ícones — substitui Material Symbols via Google Fonts, que falhava no Render)

**Backend / API**:
- **FastAPI** (nova API em `api/`, coexistindo com o Flask atual durante a migração)
- Flask (rotas legadas em `web/`, ainda em produção)
- **Supabase** (Postgres) via Session Pooler
- Credenciais cifradas com **Fernet**

**Infra**:
- **Render** (Web Service, Docker) — Python 3.13 (build do frontend em Node 22 no `Dockerfile`); a imagem roda como usuário não-root e tem `HEALTHCHECK` em `/health`
- **GitHub Actions** — CI (lint, testes da API e build do frontend) e CD (ver [Deploy](#deploy))

## Estrutura do projeto

```text
shopee_bot-main/
├── api/                    # API nova (FastAPI) — em migração
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── requirements.txt
│   └── routers/            # auth, profiles, settings, products, lists, posts,
│                           # credentials, users, dashboard, notifications, catalog, logs
├── frontend/               # Frontend novo (React + Vite) — em migração
│   ├── src/
│   │   ├── api/            # clientes HTTP tipados por recurso
│   │   ├── lib/            # cliente HTTP base
│   │   ├── pages/          # Dashboard, Login, Panel, Products, Listas, Posts, Credentials, Profiles, Settings
│   │   ├── stores/         # Zustand (auth)
│   │   └── router.tsx      # TanStack Router (code-based)
│   └── vite.config.ts
├── web/                    # Frontend em produção hoje (Flask + Jinja2)
│   ├── routes/
│   ├── templates/
│   └── static/
├── apis/                   # wrappers das redes sociais (Shopee, Threads, X, ...)
├── database/               # acesso ao Postgres/Supabase (usado pelo Flask)
├── scheduler/              # APScheduler in-process
├── docs/                   # documentação da migração
├── tests/
│   └── api/                # testes da API FastAPI (isolados do conftest do Flask)
└── .github/workflows/      # CI (ci.yml) e trigger de deploy (cd.yml)
```

## Instalação

```bash
git clone https://github.com/raffastudioproducoes-cloud/shopee_bot-main.git
cd shopee_bot-main

# Flask (produção atual)
python -m venv .venv
.venv/Scripts/activate       # Windows; source .venv/bin/activate no Linux/Mac
pip install -r requirements.txt

# API nova (FastAPI)
pip install -r api/requirements.txt

# Frontend novo (React)
cd frontend && npm install
```

Requisitos: Python 3.13 (versão usada pela CI e pelo `Dockerfile`), Node.js 20+, conta Supabase (ou Postgres local via `docker-compose-dev.yml`).

## Desenvolvimento

```bash
# Flask (produção atual) — http://localhost:5000
python -m flask --app shopee_bot.web run --debug

# API nova (FastAPI) — http://localhost:8000
uvicorn api.main:app --reload

# Frontend novo (React) — http://localhost:5173, proxy /api -> :8000
cd frontend && npm run dev
```

## Build

```bash
cd frontend
npm run build       # tsc + vite build -> frontend/dist/
```

O Flask (`web/`) não tem build separado — Jinja2 é renderizado em runtime.

## Testes

```bash
# API nova (FastAPI) — isolada do conftest do Flask, não precisa de Postgres.
# É exatamente o que a CI roda.
python -m pytest tests/api --confcutdir=tests/api -q

# Lint bloqueante da CI (erros de sintaxe/nomes indefinidos em api/)
flake8 api/ --select=E9,F63,F7,F82

# Frontend: type check + build (também roda na CI; não há testes de frontend)
cd frontend && npm ci && npm run build

# Flask legado (precisa de Postgres local em localhost:5433 — ver conftest.py);
# NÃO roda na CI
pytest tests/test_auth_root.py tests/test_publish.py
```

> `--confcutdir=tests/api` é necessário: o `conftest.py` da raiz faz
> `gevent.monkey.patch_all()` (Flask legado), que trava as threads
> async do `anyio`/`httpx` usadas pelo `TestClient` do FastAPI.

## Deploy

- **Plataforma**: Render (Web Service, Docker), plano Free.
- **Build**: lê o `Dockerfile` da raiz (Python 3.13-slim + gunicorn + gevent).
- **CI** (`.github/workflows/ci.yml`, push/PR em `main`): job `api` (flake8 bloqueante + `pytest tests/api`, Python 3.13) e job `frontend` (`npm ci` + `npm run build`, Node 20); cache de pip/npm e `concurrency` por ref.
- **CD** (`.github/workflows/cd.yml`): dispara via `workflow_run` só quando a CI termina com sucesso em `main` (push) e chama o deploy hook do Render (secret `RENDER_DEPLOY_HOOK_URL`; sem o secret, o job emite warning e pula). `.github/dependabot.yml` (semanal) e `.github/pull_request_template.md` complementam o fluxo.
- **Fluxo de branches**: Git Flow (`main` produção, `staging` homologação, `feature/*`); ver `docs/RULES.md`. GitHub Pro está ativo (confirmado pelo Rafa, 2026-10-05); branch protection agora é possível, mas ainda não configurada.
- **Pendências em produção** (confirmado pelo Rafa, 2026-10-05): env vars do Render (`shopee-bot-staging`), branch de produção de `master` para `main`, callback URLs das redes, conectar redes sociais — ver `docs/TASK.md` item 10.13.
- **Auto-deploy**: integração nativa do Render com o GitHub, a cada push em `main` (serviço de produção `shopee-bot` já na branch `main`, verificado em 2026-10-06 via API do Render).
- **Banco**: Supabase, via Session Pooler (IPv4 — o Direct Connection só responde IPv6, incompatível com o Render Free).

Detalhes de infraestrutura e histórico de bugs resolvidos no deploy: Vault `26-Deploy-Render.md`.

### Variáveis de ambiente

A lista completa, com comentário de cada uma e valores placeholder, está em `.env-example`.
Principais grupos: Supabase (`SUPABASE_URL`, `SUPABASE_KEY`), JWT da API (`API_SECRET_KEY`),
Postgres do Flask/scheduler (`SHOPEE_PG_*`), bridge interno (`INTERNAL_API_SECRET`,
`FLASK_INTERNAL_URL`, `API_INTERNAL_URL`), OAuth de app único (`THREADS_*`, `X_CLIENT_ID/SECRET`,
`INSTAGRAM_*`, `FACEBOOK_*`, `TIKTOK_CLIENT_KEY/SECRET`, mais as `*_CALLBACK_URL`),
criptografia (`APP_ENCRYPTION_KEY`), mídia (bucket privado `post-media` no Supabase Storage, sem credencial de CDN externo) (IA: chave central cifrada e editável somente pelo ADMIN, isolada por ambiente),
`FRONTEND_URL`, `CORS_ORIGINS` e `REQUEST_LOGGING_ENABLED`. Nunca versionar valores reais.

### Processo no container

`gunicorn.conf.py` usa `timeout = 120` e sobe o uvicorn (FastAPI) em subprocesso com um
supervisor que o reinicia com backoff se ele cair.

## Banco de dados

Supabase (Postgres), schema com RLS habilitado em todas as tabelas:
`users`, `profiles`, `products`, `product_lists`, `product_lists_products`, `posts`,
`medias`, `posts_medias`, `posts_products`, `schedulers`, `apscheduler_jobs`,
`activities`, `activity_types`, `audit_events`, `request_logs`, `credential_checks`,
`migrations`, e uma tabela de credenciais por rede (`shopee_credentials`,
`threads_credentials`, `x_credentials`, `facebook_credentials`, `instagram_credentials`,
`tiktok_credentials`, `kwai_credentials`).

Migrações SQL numeradas em `database/migrations/` (hoje até a `042`), rodadas em sequência no
boot (`run_migrations`) e registradas na tabela `migrations`. Migração aplicada direto no
Supabase precisa ser registrada à mão — ver `docs/RULES.md` item 9. **Migrações 037, 038, 039, 040, 041 e 042 já foram aplicadas no Supabase (2026-10-06)** — verificado via MCP; registradas em `public.migrations`. Ver `docs/RULES.md` item 11 para procedimento e risco conhecido.

### Multi-perfil

Cada conta tem até 3 perfis (1 principal + 2 secundários), limite imposto também no banco por
trigger (migração 037). O perfil ativo vai no claim `profile_id` do JWT; o backend valida que o
perfil pertence ao usuário e, se não pertencer, cai no perfil principal. `GET /auth/me` devolve
o `profile_id` ativo e o frontend o lê de lá (sem `localStorage`). `profile_id` existe em 16
tabelas (036: `products`, `product_lists`; 038: as outras 14, com índice e backfill para o
perfil principal) com `ON DELETE SET NULL`. A 039 removeu o UNIQUE de `shopee_credentials.app_id`;
a 040 adiciona índice único com coalesce para deduplicar NULLs em `credential_checks`
e trocou o de `credential_checks` por `(user_id, profile_id, network)`. A 041 troca o UNIQUE `(product_id, user_id)` de `products` por `(user_id, product_id, perfil)`: o mesmo
produto pode existir em 2 perfis (duplicado no mesmo perfil = 409). Backup/restore e os bots
do scheduler também respeitam o perfil.

## Segurança

- Credenciais de rede social cifradas em repouso (Fernet, com rotação de chave e fallback)
- Rate limiting nas rotas de credenciais e no login
- CSRF global (Flask-WTF) + Content-Security-Policy, X-Frame-Options, HSTS
- Handler de exceção genérico em produção (não vaza traceback)
- Cookie de sessão `Secure; HttpOnly; SameSite=Lax`
- JWT da API invalidado na troca de senha (claim `pwv`); tokens antigos sem o claim continuam aceitos
- Rate limit também em criar perfil, backup e restore
- Container roda como usuário não-root

Para reportar uma vulnerabilidade, ver `SECURITY.md`.

## Processo do projeto (ciclo operacional)

```text
Garimpo (Shopee Open API)
        ↓
Cadastro de produto (manual ou do garimpo)
        ↓
Lista de produtos (opcional, agrupamento)
        ↓
Criação de post (copy manual ou gerado por IA)
        ↓
Agendamento ou publicação imediata
        ↓
Scheduler executa → publica na rede social
        ↓
Log de sucesso/falha + Atividade registrada
```

## Autenticação Supabase — preparação em PR #149 (01/11/2026)

O login por e-mail e Google, o cadastro com nome de usuário/e-mail/senhas iguais/aceite, a confirmação obrigatória de e-mail e a recuperação de senha por link estão em desenvolvimento na branch `feature/supabase-auth-email-google`. A nova UI de recuperação pede e-mail e permite definir nova senha somente após o link do Supabase Auth. A senha não é alterada na tabela comercial `public.users`.

**Ainda não foi implantado em produção.** Não ativar `SUPABASE_AUTH_ENABLED` antes de migrar com segurança as duas contas legadas, testar recuperação e confirmação reais, avaliar sessões internas e resolver a entrega a e-mails de clientes externos (Supabase SMTP padrão é limitado a membros da equipe). Consulte [docs/SUPABASE-AUTH-MIGRACAO.md](docs/SUPABASE-AUTH-MIGRACAO.md).

## F4D — plano, consumo e acesso (PR #219, sem deploy)

A interface consulta `GET /api/profiles/usage` com conta e perfil autenticados:
produtos/perfis são contados por conta e listas por perfil, sem depender da paginação.
Plano e ADMIN vêm do servidor; falhas de política não viram Free e consumo não
comprovado aparece como indisponível, nunca zero. Campanhas e automação continuam
sem ativação; o CTA de planos é apenas informativo, sem cobrança ou checkout.
O frontend preserva consulta e exclusão dos rascunhos legados após downgrade.
Consulte [o contrato F4D](docs/PLANOS-F4-POLITICAS-E-FASES-20261103.md#10-f4d--interface-de-plano-consumo-e-acesso).

Contratos específicos: `cd frontend && node --test tests/plan-access.test.mjs`
e `pytest tests/api/test_account_usage.py`. A CI executa esses contratos junto
ao build TypeScript/Vite e à suíte de API. A revisão visual autenticada em desktop
e mobile permanece necessária antes da promoção; esta seção não declara deploy.

## Documentação

| Documento | Conteúdo |
| --- | --- |
| `docs/RELEASE-3.6.0-20261108.md` | Release MINOR 3.6.0, decisões, QA/CI, SHAs, Render staging/main, limites e pendências |
| `docs/PRODUTOS-DESCRICOES-CAMPANHAS-20261108.md` | Contrato de herança das descrições, download seguro da imagem Shopee e matriz de testes |
| `docs/CHECKLIST_MIGRACAO.md` | Checklist da migração para React + FastAPI, por módulo |
| `docs/ROADMAP_MIGRACAO.md` | Roadmap detalhado da migração |
| `docs/rebranding/34-Rebranding-Auto-Orbital-Plano-Mestre.md` | Decisão aprovada em 2026-10-13: marca futura **Auto Orbital**; implementação ainda pendente |
| `api/README.md` | Endpoints, variáveis de ambiente e coexistência da nova API |
| Vault `00-INDICE-Estado-Atual.md` | Fonte viva de estado do projeto (ler antes de qualquer sessão) |
| Vault `26-Deploy-Render.md` | Infra de deploy, variáveis de ambiente, bugs resolvidos |
| Vault `21-Relatorio-Correcoes-Seguranca-2026-08-21.md` | Detalhe das correções de segurança aplicadas |

## Roadmap da migração

Migração por módulos, testando cada um antes de avançar:

- [x] **Fase 0** — estrutura (API stub, frontend stub)
- [x] **Fase 1** — Auth (login/logout, sessão via cookie)
- [x] **Fase 2** — Painel/Dashboard
- [x] **Fase 3** — Produtos (CRUD completo, 13 testes)
- [x] **Fase 4** — Listas de produtos
- [x] **Fase 5** — Posts (thread multi-parte, mídia, agendamento, publicação, copywriter IA)
- [x] **Fase 6** — Credenciais (forms sem expor valor, 6 redes + Threads, validação Shopee ao vivo)
- [x] **Fase 7** — Usuários (admin-only)
- [x] **Fase 8** — Scheduler: decidido manter in-process; consolidado via bridge HTTP interno (`web/routes/internal.py`) — ver `docs/ROADMAP_MIGRACAO.md`
- [x] **Fase 8.1** — Consolidação final: FastAPI sobe como subprocesso `uvicorn` no MESMO container do Flask (`gunicorn.conf.py`), proxy transparente `/api/*` (`web/routes/api_proxy.py`), OAuth do Threads migrado pra API nova (`api/threads_oauth.py`), coluna `network` em `posts` pra publicar em várias redes
- [ ] Aposentar o Flask (`web/`) — a topologia de deploy já está implementada no código (mesmo container); falta validar isso em produção no Render e confirmar `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` lá

**Publicação real por rede** (verificado em 2026-09-27, cruzando código + Supabase — ver
`vault/00-INDICE-Estado-Atual.md` no Vault Obsidian para o detalhe): os wrappers de
publicação de Threads, X, Facebook, Instagram e TikTok existem e estão registrados no
scheduler. Threads é o único com token de usuário conectado de fato hoje — X, Instagram e
TikTok têm app registrado (app_id/secret) mas ninguém completou o OAuth ("Conectar") ainda;
Facebook usa um token de Página colado manualmente e tem credencial completa, mas nunca foi
validado com sucesso confirmado. Kwai fica de fora (sem API pública confirmada).

## Licença

Software proprietário © Raffa Studio Produções. Uso, cópia, modificação ou
distribuição somente com autorização expressa do titular.

## Contato

**Raffa Studio Produções**
E-mail: **contato.raffasp@gmail.com**

### F4E-2B1 — contrato inerte de dispatch (PR #233; PRE-DEPLOY)

Contrato isolado e ainda não integrado ao executor: `CampaignDispatchIdentity` valida somente formato em memória; não comprova vínculo, posse ou imutabilidade persistida. `require_campaign_dispatch_authorization` sempre recusa, independentemente de flags. Não altera fluxo legado, não autoriza campanha e não protege o executor central de produção atual. Sem criação de jobs/posts/reservas, SQL, migrations, configuração ou chamadas externas. Antes de qualquer execução: identidade verificável e protegida entre reserva, ocorrência, job e post; guardas transacionais no claim e imediatamente antes da chamada externa; compatibilidade nos dois ambientes; proteção de mídia e revisão do acesso service_role. CI/revisão/deploy não confirmados neste registro. `VERSION=3.0.0`.
