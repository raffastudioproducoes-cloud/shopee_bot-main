<div align="center">

# Shopee Auto Vendas

### Automação de divulgação de links de afiliado da Shopee e redes sociais.

[![Stage](https://img.shields.io/badge/stage-MVP--Beta-2563EB)](https://github.com/raffastudioproducoes-cloud/shopee_bot-main)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![APScheduler](https://img.shields.io/badge/APScheduler-3.11-FF6F00)](https://apscheduler.readthedocs.io)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-336791?logo=postgresql&logoColor=white)](https://supabase.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.120.2-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![License](https://img.shields.io/badge/license-proprietary-0F172A)](#licença)

</div>

---

## Sumário

1. [Apresentação](#apresentação)
2. [Objetivo](#objetivo)
3. [Público-alvo](#público-alvo)
4. [Funcionalidades principais](#funcionalidades-principais)
5. [Tecnologias](#tecnologias)
6. [Arquitetura e estrutura](#arquitetura-e-estrutura)
7. [Configuração do ambiente](#configuração-do-ambiente)
8. [Desenvolvimento e testes](#desenvolvimento-e-testes)
9. [Build e distribuição](#build-e-distribuição)
10. [Segurança e privacidade](#segurança-e-privacidade)
11. [Integrações e redes sociais](#integrações-e-redes-sociais)
12. [Documentação](#documentação)
13. [Roadmap](#roadmap)
14. [Licença](#licença)
15. [Contato](#contato)

---

## Apresentação

**Shopee Auto Vendas** é uma plataforma web para automatizar a divulgação de
links de afiliado da Shopee e de outras redes. O usuário cadastra produtos,
monta listas e agenda posts; a aplicação publica nos canais conectados no
horário programado, com tentativas e tratamento de erro.

Atualmente a publicação automática está operacional para **Shopee** e
**Threads**. As demais redes (X, Facebook, Instagram, TikTok, Kwai) já
possuem armazenamento cifrado de credencial, mas aguardam a implementação do
wrapper de API para publicação automática.

**Migração em andamento (iniciada em 2026-09-04):** frontend Flask/Jinja2/Alpine.js
estar sendo migrado para React 19 + TypeScript + TanStack Router + TanStack Query
+ Vite + Tailwind CSS + Zustand, com nova API Python (FastAPI) servindo JSON e
mantendo a estrutura do Supabase.

Versão atual: **MVP / Beta** · Idioma: **Português Brasileiro** · Plataforma: **Web**

## Objetivo

Reduzir o trabalho manual de divulgação recorrente, permitindo ao usuário:

- cadastrar produtos e listas de produtos da Shopee;
- agendar posts (únicos ou recorrentes, por cron) para os canais conectados;
- conectar credenciais de redes sociais de forma cifrada;
- acompanhar atividades e histórico de publicação;
- disparar posts sob demanda fora do agendamento.

## Público-alvo

- Afiliados da Shopee
- Marketers de mídias sociais
- Pequenos lojistas e criadores de conteúdo
- Quem divulga links de afiliado em múltiplas redes
- Operações que precisam de agendamento recorrente de posts

## Funcionalidades principais

| Módulo | Recursos |
| --- | --- |
| **Usuários** | Cadastro, login, alteração de senha, controle de acesso |
| **Produtos** | Catálogo de produtos da Shopee e listas de produtos |
| **Posts** | Criação, agendamento (cron/data) e execução sob demanda |
| **Credenciais** | Shopee, Threads, X, Facebook, Instagram, TikTok e Kwai (cifradas) |
| **Painel** | Visão consolidada de posts e atividades recentes |
| **Scheduler** | APScheduler com jobstore em banco (sobrevive a reinícios) |
| **Atividades** | Histórico de ações e publicações |
| **API Python (nova)** | FastAPI com endpoints REST para frontend React (coexistindo com Flask durante migração) |
| **CI/CD** | GitHub Actions com lint + test da API Python e deploy no Render |

## Tecnologias

- **Python 3.13**
- **Flask 3.1** (blueprints, Flask-Login, Flask-WTF, Flask-Babel, Flask-Limiter)
- **APScheduler 3.11** com executor gevent
- **Gunicorn 23** (1 worker gevent; scheduler sobe no hook `on_starting`)
- **FastAPI 0.120.2** (nova API, coexistindo com Flask durante migração)
- **PostgreSQL** via **Supabase** (psycopg 3 + pool de conexões)
- **SQLAlchemy** (jobstore do scheduler) e migrations versionadas
- **cryptography** (Fernet) para cifrar credenciais em repouso
- **Docker** / **docker-compose** para build e execução
- **Render** como hospedagem (web service + Render PostgreSQL)
- **React 19** (em migração) com TypeScript, TanStack Router, TanStack Query, Vite, Tailwind CSS, Zustand, Lucide React
- **GitHub Actions** para CI/CD (lint + test da API Python, e deploy no Render via webhook)
- **Supabase** como banco externo (tabelas e RLS mantidos)

## Arquitetura e estrutura

```
shopee_bot-main/
├── apis/                   # wrappers de API (shopee, threads; demais pendentes)
├── database/               # acesso ao BD: uma subclasse por tabela + migrations
├── scheduler/              # APScheduler: bot_post, update_products
├── api/                    # nova API Python (FastAPI) para frontend React
│   ├── main.py             # FastAPI app
│   ├── config.py           # variáveis de ambiente
│   ├── database.py         # conexão com Supabase
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── products.py
│   │   ├── posts.py
│   │   └── credentials.py
│   ├── requirements.txt
│   └── README.md
├── web/                    # Flask atual (até a migração completa)
│   ├── routes/
│   │   ├── auth.py
│   │   ├── panel/
│   │   ├── posts.py
│   │   ├── products.py
│   │   ├── product_lists.py
│   │   ├── users.py
│   │   ├── activities.py
│   │   └── startup.py
│   ├── templates/          # HTML (Jinja2)
│   └── static/
├── .github/
│   └── workflows/
│       ├── ci.yml          # CI: lint + test da API Python
│       ├── cd.yml          # CD: deploy no Render via webhook
│       └── README.md
├── docs/
│   ├── CHECKLIST_MIGRACAO.md
│   └── ROADMAP_MIGRACAO.md
├── tests/                  # testes automatizados (pytest)
├── clogging.py             # logger compartilhado
├── gunicorn.conf.py        # produção: 1 worker gevent, on_starting -> scheduler
├── Dockerfile              # imagem (web + scheduler no mesmo container)
├── docker-compose.yml      # web + postgres + nginx
├── requirements.txt
├── README.md
└── LICENSE
```

Princípios adotados:

- Web e scheduler no **mesmo processo** (o scheduler inicia no `on_starting`
  do Gunicorn), simplificando hospedagem em containers únicos.
- Nova API Python (FastAPI) **coexiste** com o Flask durante a migração. O
  frontend React aponta para a nova API, enquanto os templates Jinja2
  remanescentes continuam usando o Flask até a migração estar completa.
- Jobstore do scheduler em **PostgreSQL**, então os agendamentos sobrevivem a
  reinícios do container.
- Credenciais sensíveis **cifradas em repouso** (`cryptography.fernet`); a chave
  vem de variável de ambiente, nunca do código.
- Segredos fornecidos apenas por variáveis de ambiente ou Secrets da
  plataforma de hospedagem.
- Migrations versionadas em `database/migrations/`.
- CI/CD com GitHub Actions: lint + test da API Python em cada push/PR, e
  webhook de deploy no Render.

## Configuração do ambiente

Requisitos:

- Python 3.13
- Acesso a um PostgreSQL (Supabase ou local)
- Conta Render (para deploy)
- Variáveis de ambiente conforme `.env-example`

Clone o repositório:

```bash
git clone https://github.com/raffastudioproducoes-cloud/shopee_bot-main.git
cd shopee_bot-main
```

Prepare o ambiente local:

```bash
python -m venv .venv
# Windows (PowerShell):
#   .venv\Scripts\activate.bat
# Linux/macOS:
#   source .venv/bin/activate
pip install -r requirements.txt
cp .env-example .env
# edite .env com os dados reais (Supabase, Threads, chaves, etc)
```

O `.env` é ignorado pelo Git e nunca deve ser commitado.

### Variáveis de ambiente

| Variável | Descrição | Obrigatória |
| --- | --- | --- |
| `POSTGRES_HOST` | Host do PostgreSQL (Supabase ou local) | **Sim** |
| `POSTGRES_USER` | Usuário do PostgreSQL | **Sim** |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL | **Sim** |
| `POSTGRES_DB` | Nome do banco | **Sim** |
| `POSTGRES_PORT` | Porta do PostgreSQL | Não |
| `APP_ENCRYPTION_KEY` | Chave Fernet para cifrar credenciais | **Sim** |
| `FLASK_SESSION_SECRET` | Segredo da sessão Flask | **Sim** |
| `THREADS_CLIENT_ID` | Client ID do OAuth do Threads | Não |
| `THREADS_CLIENT_SECRET` | Client Secret do OAuth do Threads | Não |
| `THREADS_CALLBACK_URL` | URL de callback do OAuth do Threads | Não |
| `THREADS_BOT_TOKEN` | Token do bot do Threads | Não |
| `GEMINI_API_KEY` | Chave da API Gemini (para copywriter IA) | Não |

### Supabase

O projeto usa Supabase como banco externo. A estrutura de tabelas e RLS já
está configurada. Para usar localmente, configure as variáveis de ambiente
acima com as credenciais do seu projeto Supabase.

## Desenvolvimento e testes

### Ambiente de desenvolvimento

Flask atual (Jinja2):

```bash
flask --debug --app web run
```

Nova API Python (FastAPI) — para uso com frontend React:

```bash
pip install -r api/requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

A nova API coexiste com o Flask. Durante a migração, o frontend React aponta
para `http://localhost:8000` (FastAPI), enquanto os templates Jinja2 continuam
usando o Flask em outra porta.

### Testes automatizados (pytest)

```bash
pytest
```

### Lint (flake8)

```bash
flake8 api/ --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 api/ --count --exclude=__init__.py --max-line-length=120 --statistics
```

### CI local (GitHub Actions)

Para testar o CI localmente, use `act`:

```bash
act push -j lint-and-test
```

## Build e distribuição

### Local / servidor próprio (docker-compose)

Sobe web + PostgreSQL + nginx (proxy reverso com TLS):

```bash
docker compose up -d
```

### Render (hospedagem atual)

O projeto está hospedado no Render como Web Service, com variáveis de ambiente
configuradas no dashboard.

URL: `https://shopee-bot-fj0w.onrender.com`

Para fazer deploy no Render:

1. Criar um novo Web Service no dashboard do Render
2. Conectar ao repositório GitHub
3. Configurar as variáveis de ambiente (PostgreSQL, Cloudinary, Threads, chaves)
4. Configurar o comando de start: `gunicorn web:app --config=gunicorn.conf.py`

A imagem sobe com `gunicorn web:app --config=gunicorn.conf.py`; o scheduler
inicializa junto no mesmo container.

### CI/CD com GitHub Actions

Os pipelines estão em `.github/workflows/`:

- **ci.yml**: lint + test da API Python em cada push/PR
- **cd.yml**: webhook de deploy no Render (se houver integração configurada)

Para configurar o CD no Render:

1. No Render, ir em Settings → Webhooks
2. Copiar o URL do webhook
3. Colocar no GitHub Actions como secret `RENDER_DEPLOY_HOOK_URL`

## Segurança e privacidade

- Credenciais de redes sociais são **cifradas em repouso** (Fernet); a chave
  (`APP_ENCRYPTION_KEY`) fica em variável de ambiente.
- Segredos (banco, Threads, chaves) **não estão no código**;
  variáveis em `.env` (ignorado) ou Secrets da plataforma.
- Correções de **XSS/injeção SQL** e `search_path` definido (commit
  `b116f9d`).
- **Rate limiting** global (Flask-Limiter) e proteção de força bruta no login.
- **CSRF** (Flask-WTF) e `login_required` nas rotas protegidas.
- `ProxyFix` habilita operação correta atrás de reverse proxy (nginx / Render).
- Sem credenciais ou senhas padrão expostas no repositório.
- Logs, issues e documentação não devem conter credenciais ou dados pessoais.
- Processamento de formulários de credenciais: **try/except padronizado em
  todas as 7 redes** (Shopee, Threads, X, Facebook, Instagram, TikTok, Kwai),
  com preservação dos valores digitados na sessão e mensagem de erro amigável
  em vez de 500 genérico. Commit [`c9731c8`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/c9731c8).
- Credenciais não usadas publicamente: função `public.rls_auto_enable()`
  declarada `SECURITY DEFINER` teria sido acessível por `anon`/`authenticated`
  via RPC; revoke `EXECUTE` para `anon`, `authenticated` e `public`.
- Tabelas com RLS habilitado sem policies: criadas **policies de rejeição
  explícitas** `block_all_api` em todas as 18 tabelas (`USING (false)
  WITH CHECK (false)` para `anon, authenticated`), documentando que o acesso
  externo via API está bloqueado por design — o backend usa conexão direta
  com usuário admin que bypassa RLS; o frontend não usa Supabase JS client.

**Migração para React + FastAPI (2026-09-04):**

- **Ícones:** substituição de Material Symbols (Google Fonts, que falha no
  Render) por SVG inline via macro `_icon.html`. Zero dependência de CDN externo.
- **Inputs de senha:** macro `secret_input` nunca exibe `value="{{ value }}"`,
  evitando exposição de credenciais quando o Alpine.js ou CDN falham.
- **CORS:** a nova API FastAPI usa CORS restrito à origem do frontend React.
- **CSRF e rate limiting:** mantidos da implementação anterior; a nova API
  está em avaliação para implementação equivalente.

Este projeto adota princípios da **LGPD**: minimização de dados, finalidade
explícita, controle de acesso e transparência sobre tratamento e retenção.

## Integrações e redes sociais

| Rede | Estado | Detalhe |
| --- | --- | --- |
| **Shopee** | ✅ Operacional | Wrapper + validação de credencial (`query_auth_validate`) |
| **Threads** | ✅ Operacional | Wrapper + OAuth (callback aceita `GET ?code=`) |
| **X** | ⏸️ Pendente | Wrapper de API implementado (`apis/x.py`) com validação de Bearer Token (OAuth 2.0 Client Credentials) e postagem de texto/produto. Falta: (1) page_id ou user_id não é salvo na tabela (tabela só tem app_id/secret); (2) wrapper de scheduler para publicar automaticamente; (3) validação end-to-end com credentials reais. |
| **Facebook** | ⏸️ Pendente | Wrapper de API implementado (`apis/facebook.py`) com App Access Token, Page Access Token e postagem de texto/produto na Timeline. Falta: (1) page_id não é salvo na tabela (tabela só tem app_id/secret); (2) wrapper de scheduler; (3) validação end-to-end. |
| **Instagram** | ⏸️ Pendente | Wrapper de API implementado (`apis/instagram.py`) via Meta Graph API (Instagram Basic Display + Content Publish). Suporta postagem de texto via media container. **Pré-requisitos críticos**: (1) `user_access_token` com permissões `instagram_basic` e `instagram_content_publish` não é salvo na tabela (hoje só tem app_id/secret); (2) conta deve ser Business/Creator com Instagram Graph API habilitada; (3) wrapper de scheduler. |
| **TikTok** | ⏸️ Pendente | Wrapper de API implementado (`apis/tiktok.py`) definindo contrato. **Limitação da plataforma**: TikTok não publica texto puro via API — só vídeos. Wrapper atual levanta `NotImplementedError` para `post_text` e `validate_credentials` até que OAuth user flow e upload/publish de vídeo estejam implementados (documentação: developers.tiktok.com). |
| **Kwai** | ⏸️ Pendente | Wrapper de API implementado (`apis/kwai.py`) definindo contrato. **Limitação da plataforma**: Kwai não disponibiliza API pública documentada para postagem de conteúdo via programação (a plataforma funciona via app móvel; API de parceiros/Advertisers é restrita). Wrapper atual levanta `NotImplementedError` até que uma API pública seja disponibilizada ou um agregador com suporte seja usado. |

Todas as wrappers implementadas seguem o padrão de `apis/shopee.py` e `apis/threads.py`.
As redes X, Facebook e Instagram usam API pública documentada (X API v2, Meta Graph API v18.0).
TikTok e Kwai não permitem publicação prática via API pública hoje; os wrappers definem o contrato e lançam `NotImplementedError` com documentação até que os pré-requisitos (OAuth user token, vídeo para TikTok, API pública para Kwai) estejam disponíveis.

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [README](README.md) | Visão geral, arquitetura, operação, segurança e roadmap |
| `24-Deploy-HuggingFace-Spaces.md` | Deploy free-tier (HF Spaces), Secrets, OAuth do Threads |
| `18-Roadmap-Mestre.md` | Roadmap mestre do produto (repositório de documentação) |
| `docs/CHECKLIST_MIGRACAO.md` | Checklist por módulo da migração para React + FastAPI |
| `docs/ROADMAP_MIGRACAO.md` | Roadmap detalhado da migração para React + FastAPI |
| `api/README.md` | Documentação da nova API Python (FastAPI) |

Este projeto adota **Documentação Viva**: uma funcionalidade não é considerada
concluída sem atualizar o README e a documentação técnica aplicável.

## Roadmap

Concluído:

- Cadastro de usuários, produtos e listas (Sprints 0–2)
- Senha padrão e criptografia de credenciais
- Rate limiting e correções de XSS/injeção
- Testes automatizados (login, criar produto, criar post, publicar)
- Banco em Supabase e redesign de frontend (Stitch)
- Scheduler com jobstore persistente
- Ícones SVG inline substituindo Material Symbols (2026-09-04)
- Inputs de senha sem exibir valor secreto (2026-09-04)
- API Python (FastAPI) estruturada para frontend React (2026-09-04)
- GitHub Actions: CI lint+test e CD deploy no Render (2026-09-04)

Próximo:

- Hospedagem em produção (Render — este deploy)
- Beta fechado com usuários reais
- OAuth do Threads em produção (callback corrigido; falta validação end-to-end)
- Wrappers de API para X, Facebook: implementados (validação + postagem de texto/produto, mas sem schedule nem page_id na tabela). Instagram: wrapper implementado, mas requer user_access_token (OAuth) e conta Business/Creator. TikTok e Kwai: wrappers com contrato — TikTok precisa de OAuth user flow e vídeo; Kwai não tem API pública de postagem.
- Domínio próprio (Render Custom Domain ou Cloudflare Worker) e monitoramento (UptimeRobot) — rota `/health` implementada para monitoramento externo.
- Publicação automática multicanal completa
- Migração do frontend para React 19 + TypeScript + TanStack Router + TanStack Query + Vite + Tailwind CSS + Zustand (módulos: Auth, Painel, Produtos, Listas, Posts, Credenciais, Usuários)

## Licença

Software proprietário © Raffa Studio Produções — Shopee Auto Vendas.
Uso, cópia, modificação ou distribuição somente com autorização expressa do
titular.

## Contato

**Raffa Studio Produções**

E-mail: **contato.raffasp@gmail.com**

---

Desenvolvido para automatizar quem vende no Brasil.
