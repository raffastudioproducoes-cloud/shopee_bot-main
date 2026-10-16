# Escalabilidade do ShopeeAutoVendas — plano futuro (Fases 0 a 7)

Status: EM EXECUÇÃO CONTROLADA (preparação do scheduler e Fase 4.2 em `main`; fila implantada em `staging` em `330137f` e promovida em `efba7a4`, com CI verde, Render live e health `200`).
Custo novo da análise: R$ 0. Nenhum código, banco, produção ou Vault foi alterado na análise.
Método: 4 auditorias paralelas do Codex (somente leitura: scheduler/jobs, estado/rate limit/cache/storage, banco/Supabase, infra/observabilidade/resiliência) cruzadas com o Vault e o código. Onde o código recente diverge da doc antiga, vale o código.
Restrição geral: não contratar serviço pago, não provisionar Redis/fila/cluster agora, não aumentar workers antes de resolver o scheduler, não fazer overengineering. Preferir monólito modular scale-ready. Manter compatibilidade com Render Free + Supabase Free.

## Veredito
Hoje o sistema é seguro só com 1 instância e 1 worker. Dois bloqueios permanecem para escala horizontal completa:
1. Scheduler ainda vive no processo da aplicação; a separação em worker está preparada por configuração, mas não foi provisionada em staging.
2. Bots de publicação ainda não têm idempotência por item remoto (reexecução após falha parcial pode duplicar o post na rede).
O runner de migrações já usa `pg_advisory_lock`; não é mais um bloqueio aberto.
O resto (sessão JWT, OAuth state, mídia nova, proxy) já é stateless. Render Free permite no máximo 1 instância (https://render.com/docs/scaling): escala real exige plano pago; dá para preparar tudo sem custo.

## FASE 0 — Arquitetura AS-IS
```
Internet → Render Free (1 container Docker, hiberna sem tráfego)
            ├─ nginx → React (estático)
            ├─ Flask/gunicorn (workers=1) ← proxy do /api, ProxyFix, /health
            │    └─ post_fork: init_scheduler() (APScheduler + jobstore)  ← mesmo processo
            ├─ FastAPI/uvicorn (API real, JWT em cookie httpOnly)
            └─ migrações rodam no boot do Flask
                       ↓
          Supabase Postgres (Free) + Storage (post-media privado, avatars)
          APIs externas: Shopee, Meta, TikTok, X (desativado), Gemini/OpenAI/Anthropic
```

## FASE 1 — Auditoria de scale-readiness (P0 crítico, P1 alto, P2 médio, P3 melhoria)

| Prio | Componente | Problema (evidência) | Bloqueia escala horizontal? | Solução futura | Custo |
|---|---|---|---|---|---|
| P0 | Scheduler | Um scheduler por processo, sem lock; workers=1 é a única proteção (gunicorn.conf.py:13, scheduler/__init__.py:203-219). Com 2 workers ou 2 instâncias: publicação duplicada ou perdida. | Sim | Claim atômico em fila no Postgres (FOR UPDATE SKIP LOCKED); depois worker exclusivo | $0 |
| P0 | Publicação | Os 5 bots chamam a rede e só depois gravam `activities`. Se cair no meio, o retry duplica. Threads multi-parte repete partes. | Sim | idempotency_key único por post+rede+parte e external_id gravado | $0 |
| P0 | Migrações | Rodam no boot sem lock (database/migrations/__init__.py:64-73). Duas instâncias podem aplicar a mesma. | Sim | pg_advisory_lock no runner | $0 |
| P0 segurança | Logs | Senha do DSN do Postgres pode ir ao log em debug (database/__init__.py:88-90). Token do Threads na URL e na exceção (apis/threads.py:85-87, 29-36). | Não | Mascarar o DSN e passar o token fora da URL | $0 |
| P1 | Rate limits | Em memória: login, cadastro, reset (auth.py), busca Shopee (catalog.py), Flask-Limiter memory:// (web/limiter.py) | Sim | RateLimitBackend (local agora, Redis depois) | $0 |
| P1 | Pool de conexões | Até 10 conexões por processo + a do scheduler; multiplica com 2 instâncias | Se estourar | DB_POOL_MAX configurável, Session Pooler | $0 |
| P1 | N+1 | Posts e listas fazem várias consultas por item (posts.py:779-791, lists.py:161-170) | Não, mas derruba capacidade | Consulta em lote ou view/RPC por tela | $0 |
| P1 | Escritas compostas | Via REST, sem transação, com compensação manual | Não | RPC Postgres ou transação | $0 |
| P1 | publishNow | Pode cair no jobstore de memória | Sim | Job persistido e claimável | $0 |
| P1 | Retry/resiliência | Retry simples, sem jitter, sem Retry-After, sem circuit breaker | Não | Helper único (timeout, retry só se idempotente, jitter) | $0 |
| P1 | Observabilidade | Sem request_id/correlation id; /health só liveness; request_logs e audit_events sem retenção | Não | X-Request-ID, /health/ready, política de retenção | $0 |
| P1 | Índices | Faltam compostos user_id/profile_id + created_at | Não | Propor após EXPLAIN, sem criar às cegas | $0 |
| P1 | Preço/comissão | Colunas TEXT, convertidas na API | Não | Colunas numeric novas com backfill | $0 |
| P2 | Storage legado | web/media e /media/<path> ainda existem; mídia nova já está no Supabase Storage | Não | StorageBackend + migração lazy | $0 |
| P2 | Cache | Só caches de cliente e token por instância, sem dado de usuário. Read-heavy reais: dashboard, catálogo Shopee, categorias | Não | CacheBackend (NoOp ou local) com TTL e invalidação | opcional |
| P2 | Teste de credenciais | ThreadPoolExecutor local; morre no restart | Não | Tratar como job idempotente | $0 |

Já seguros para multi-instância: sessão JWT em cookie, OAuth state assinado por usuário e perfil, avatar e mídia nova no Storage, proxy com ProxyFix e X-Forwarded-*, CORS restrito.
Limites oficiais: Render Free = 1 instância máx., sem disco persistente (https://render.com/docs/scaling, https://render.com/docs/free). Supabase Free = 500 MB banco, 1 GB Storage, egress 5 GB num doc e 10 GB em outro (reconfirmar) (https://supabase.com/docs/guides/platform/billing-on-supabase). Conexões: ~60 diretas e ~200 no pooler no tier pequeno.

## FASE 2 — Arquitetura TO-BE
- Target A (hoje, grátis): 1 instância; só preparação (travas e idempotência no Postgres, request_id, readiness, DSN e token fora do log, interfaces RateLimit/Cache/Storage com backend local).
- Target B (crescimento, Render pago, 2+ instâncias HTTP): API stateless 2+ réplicas + worker exclusivo de scheduler; fila no Postgres (publish_jobs com SKIP LOCKED), sem Redis; rate limit distribuído só se houver mais de uma instância; cache seletivo; DATABASE_WRITE_URL e DATABASE_READ_URL apontando para o mesmo banco.
- Target C (alta escala): load balancer com N réplicas, N workers, Redis (cache, rate limit, circuit breaker), réplica de leitura, observabilidade externa, storage com lifecycle. Só com SLO formal e receita que pague.
- Escolha da fila: Postgres com SKIP LOCKED (já temos Supabase, durável, transacional, sem serviço novo). Celery/Redis/RQ/Dramatiq/Arq só quando latência ou vazão exigir.
- Campos de publish_jobs: id, post_id, user_id, profile_id, network, run_at, idempotency_key UNIQUE, status, attempt, max_attempts, locked_at, locked_by, started_at, finished_at, next_attempt_at, last_error, external_id.
- Interfaces: RateLimitBackend.hit(key, limit, window, scope); CacheBackend get/set/delete/get_or_set (candidatos: dashboard TTL 15-60 s, catálogo Shopee 5-15 min por credencial+busca, categorias 24 h — hipóteses a validar por teste de carga, com invalidação em CRUD, nunca segredo); StorageBackend (legado local, Supabase, S3 futuro); db.read()/db.write() (ambos no mesmo writer por enquanto). Read-after-write (login, troca de perfil, OAuth callback, CRUD, upload, scheduler, restore) sempre no writer.

## Capacidade L0–L5 (números = hipótese a validar por teste de carga, exceto limites oficiais)
| Nível | Usuários ativos | Infra | Custo | Gatilho para o próximo (inicial, a validar) |
|---|---|---|---|---|
| L0 atual | 1-3 | Render Free + Supabase Free | $0 | p95 > 2 s quente, job perdido, banco > 300 MB |
| L1 | 5-10 | igual + request_id, readiness, retenção de logs | $0 | 5xx > 1%, 429 externo recorrente |
| L2 | ~20 | 1 instância no limite, claim no Postgres | $0 | CPU ou memória > 70% sustentado, banco > 400 MB |
| L3 | ~50 | Render pago, scheduler separado, rate limit distribuído | pago | precisar de 2 instâncias ou p95 > 1 s sob carga |
| L4 | ~200 | Web horizontal, worker e fila, Supabase Pro | pago | fila com atraso > 5 min, 429 dos provedores |
| L5 | 1 mil+ | Réplicas, observabilidade externa | pago | SLO formal e auditoria |

Matriz de capacidade do banco: N0 Free; N1 Pro; N2 índices/queries/pooling; N3 cache read-heavy; N4 read replica; N5 particionamento/arquivamento; N6 outro Postgres gerenciado só com motivo real. Sempre PostgreSQL-compatible.

## PLANO POR FASES (a executar com autorização explícita; cada fase com commits pequenos, testes, rollback e relatório PASS/FAIL)
- FASE 3 — Preparação sem custo. Primeiro segurança (DSN e token fora do log), depois abstrações (RateLimit/Cache/Storage/db read-write), idempotência, config centralizada, /health e /readiness, timeouts e retry policy, structured logging com request_id.
- FASE 4 — Scheduler/jobs. `publication_claims`, `SCHEDULER_ENABLED` e `publish_jobs` já foram implantados. A fila deduplica ocorrências localmente; faltam reconciliação por provedor, teste real de publicação e teste de carga antes de subir workers ou instâncias.

### FASE 4.2 — Fila durável e desfecho seguro (staging e main implantados; publicação real e reconciliação pendentes)

Contrato mínimo antes de separar processos ou aumentar réplicas:

- Cada disparo cria ou recupera um item em `publish_jobs`, identificado por uma chave determinística da agenda e da sua ocorrência. A chave única absorve o mesmo disparo entregue duas vezes.
- Um worker faz claim atômico somente de item `pending`. O claim grava `locked_by`, `locked_at`, incrementa `attempt` e não permite dois workers executarem o mesmo item. Lease vencido em `running` vira `unknown`, pois a rede pode ter recebido a postagem antes da perda do worker.
- O resultado só é `succeeded` quando o publicador devolve confirmação do provedor; o identificador externo, quando devolvido pela API, fica no item.
- Erro antes de qualquer chamada externa pode ir a `failed`. Erro durante ou depois de chamada externa é `unknown`: não recebe retry automático, pois poderia duplicar a postagem. A retomada só será possível após reconciliação específica por provedor.
- Esta entrega não promete exactly-once remoto: as APIs sociais não oferecem uma chave de idempotência comum. Ela garante deduplicação local e evita repetir automaticamente efeitos externos de confirmação incerta.
- Testes obrigatórios: criação idempotente, claim concorrente com 2/5 workers simulados, lease vencido, conclusão com `external_id` e bloqueio de retry em estado `unknown`.
- FASE 5 — Banco. Advisory lock nas migrações, índices compostos só após EXPLAIN, retenção de request_logs, N+1 em lote, numeric para preço. Migrações pequenas e reversíveis, sem apagar dados, sem mexer em RLS sem teste.
- FASE 6 — Testes. Unit, integração, concorrência, idempotência, retry, restart com lock expirado, fumaça de carga local leve (sem atacar APIs externas reais).
- FASE 7 — Documentação no Vault (Projetos/ShopeeAutoVendas/): 33-Escalabilidade-e-Capacidade, 34-Arquitetura-Scale-Ready, 35-Plano-de-Evolucao-de-Infra (28 a 32 já existem), mais updates do 00-INDICE-Estado-Atual, 01-Status-e-Checklist, 02-Arquitetura-e-Tecnologias, 07-Diagrama-de-Arquitetura e 04-Backlog.
Ordem recomendada: P0 de segurança nos logs → idempotência + fila no Postgres → advisory lock nas migrações → rate limit/cache/storage abstratos → índices/N+1/retenção.

## Arquivos que seriam alterados na Fase 3 (lista consolidada)
- Novos: api/backends/rate_limit.py, cache.py, storage.py; database/migrations/049_* (índices) e 050_* (retenção e publish_jobs).
- Segurança de logs: database/__init__.py, apis/threads.py, api/utils/log_sanitizer.py.
- Estado e rate limit: api/routers/auth.py, catalog.py, credentials.py, web/limiter.py.
- Observabilidade e health: api/middleware.py, api/main.py, web/__init__.py, api/audit_log.py, api/audit_trail.py.
- Banco: database/migrations/__init__.py (advisory lock), api/database.py, .env-example.
- Scheduler (Fase 4): scheduler/__init__.py, scheduler/bot_post*.py (5 arquivos), database/schedulers.py, api/internal_client.py, web/routes/internal.py, gunicorn.conf.py, Dockerfile.
- Consultas: api/routers/posts.py, lists.py, products.py, logs.py, notifications.py, dashboard.py.
- Apis e utilitários: apis/facebook.py, instagram.py, tiktok.py, x.py, shopee.py, llm.py, utils/__init__.py.
- CI e frontend: .github/workflows/*, frontend/src/pages/legal/PrivacyPolicyPage.tsx (retenção LGPD).

## Testes necessários (resumo)
Concorrência (2 e 5 workers simulados, só 1 chamada externa), idempotência (dois publishNow simultâneos), restart (job claimado e worker morto, lock expira e outro retoma), falha parcial (Threads multi-parte não republica), retry (attempt, last_error, max_attempts), rede (external_id gravado, sem chamada se idempotency_key finalizada).

## Restrições e rollback
Não contratar serviço, não apagar dados, não migrar o Supabase sem justificativa, não instalar Kubernetes, não criar microserviço, não aumentar workers cegamente, não criar cache sem invalidação. Rollback: commits pequenos, migrações reversíveis quando possível, nenhuma mudança destrutiva misturada com refatoração.
