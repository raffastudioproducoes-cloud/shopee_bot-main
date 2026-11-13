# Banco autoritativo: auditoria e plano — 13/11/2026

**Decisão do Rafa (literal):** "quem deve trabalhar com isso é o banco, se não o cliente pode subtrair o que já usou e continuar usando um limite que o plano dele não cobre; por isso o site não importa. A separação entre ambientes nunca deveria ter existido. Tira a ideia de desligar um ou outro; quem manda é o banco de dados. Nada deve ser resolvido pelo site ou pela API, senão abre brecha para invasão ou pegar planos sem ter pago."

**Natureza deste documento:** auditoria estática + plano. Nenhum código, migration, VERSION, CHANGELOG ou dado foi alterado.

**Base auditada:** `origin/staging` `f9d6d65d` (release 3.19.0). `origin/main` `c4656d45` tem o mesmo conteúdo (`git diff origin/main origin/staging` vazio). Então o que vale para staging vale para o código de produção.

**Não consultei o Supabase.** O banco é compartilhado com a produção e a regra do Vault proíbe acessar produção sem autorização. Tudo que depende do catálogo vivo (RLS, GRANTs, tabelas criadas à mão) aparece como **não confirmado**. A Fase 0 lista as consultas só de leitura que o Rafa precisa autorizar.

Legenda: `arquivo:linha` = fato lido no repositório. **Não confirmado** = hipótese ou fato que depende do banco vivo ou da configuração do Render.

---

## 1. Inventário: onde cada regra é decidida hoje

### 1(a) Quem pode executar uma publicação (claim)

| Fluxo | Onde fica o claim | Filtro de ambiente | Checa o plano na execução? |
|---|---|---|---|
| Post legado (recorrência `cron` e "Agora" `date`) | SQL montado em **Python** (`database/publish_jobs.py:151-253`), com `FOR UPDATE ... SKIP LOCKED` (`:202`) e lease em `publication_claims` (`database/publication_claims.py:6-20`) | `schedule.environment = current_environment()` (`database/publish_jobs.py:9-17`; `database/central_dispatch.py:56-83`); `schedulers.get_by_id` também filtra (`database/schedulers.py:75-86`) | **Não.** O claim não lê `users.plan_tier` nem cota. `scheduler/*.py` não faz nenhuma referência a plano/tier/quota (grep vazio) |
| Campanha (F4E) | Função SQL `claim_campaign_publication_f4e` **SECURITY DEFINER** (`database/migrations/078_campaign_executor.sql:5-43`), `FOR UPDATE OF s SKIP LOCKED` (`:25`) | `s.source_environment = p_environment AND r.source_environment = p_environment` (`078:16-17`); o worker passa `current_environment()` (`scheduler/campaign_dispatch.py:111,131`) | **Sim**, no claim: `ADMIN` ou `plan_tier IN (pro,plus,premium) AND campaign_paid_through > now()` (`078:23-24`) |
| Central (F0, desligado) | `ORBITAL_CENTRAL_DISPATCH_ENABLED=false` por padrão (`database/central_dispatch.py:16-28`); quando ligado, só a produção executa (`database/scheduler_environment.py:29-38`) | `dispatch_mode='central'` (`database/migrations/068_central_dispatch_compatibility.sql:31-50`) | Não |

O ambiente sai da branch do Render, não de uma variável editável: `main` → `production`, `staging` → `staging`, branch desconhecida falha (`database/scheduler_environment.py:10-27`). O jobstore do APScheduler é separado por ambiente: `apscheduler_jobs` ou `apscheduler_jobs_staging` (`scheduler/__init__.py:481-486`; `067_isolate_scheduler_environments.sql:15-26`). Toda agenda nova recebe o ambiente de quem a criou (`database/schedulers.py:100-123`).

O cron que acorda o site só olha itens de produção: `s.environment = 'production'`, `s.source_environment = 'production'` e `sc.environment = 'production'` (`docs/operations/wake-before-posts-cron.sql:70,79,86`). Isso foi o que obrigou a migração manual de 12/11 (`docs/operations/migracao-agendamentos-staging-para-producao-20261112.md`).

A deduplicação é feita assim:
- `publish_jobs.idempotency_key UNIQUE` (`053_create_publish_jobs.sql:10`) com `ON CONFLICT` no enqueue (`database/publish_jobs.py:126-148`).
- Depois do início do envio externo não há reenvio automático (`external_started_at` → `unknown`, `078:131-136`).

**Fato relevante para a unificação:** a chave de ocorrência do cron vem do **relógio de quem executa**, não do horário agendado: `datetime.now(...)` (`scheduler/__init__.py:157-167`). Dois executores que disparem a mesma agenda em minutos diferentes geram chaves diferentes e publicam duas vezes. Hoje a separação de ambientes esconde esse problema. Ele precisa ser corrigido antes de deixar mais de um executor pegar a mesma fila (ver o risco A3).

### 1(b) Limites de plano/cota: onde cada um é imposto

A política fica em `public.plan_limits` (`072_plan_limits_and_atomic_catalog_quotas.sql:7-28`). Só o `service_role` lê e altera, e o UPDATE fica auditado em `plan_limits_audit` (`072:30-50,138-145`).

Todas as funções de cota abaixo são **SECURITY INVOKER**, com EXECUTE só para `service_role` (`072:82-150`, `073:46-212`). São "opt-in": só valem quando a API decide chamá-las. **Não existe trigger em `posts`, `schedulers`, `publish_jobs`, `products` nem `product_lists`** (`072:1-3`, `073:1-3`). O único trigger de cota é o legado de perfis, com teto fixo de 3 (`072:156-169`).

| Limite | Onde é imposto hoje | Burlável? | Evidência |
|---|---|---|---|
| Produtos por conta (`products_per_account` 100/500/2000) | RPC `insert_product_with_plan_quota`, chamada só por `POST /products` | **Sim.** O restore de backup insere direto | `072:82-109`; `api/routers/products.py:233`; insert direto em `api/routers/users.py:549-552`; painel Flask legado `web/routes/products.py:145` (só com `LEGACY_PANEL_ENABLED=true`, `web/__init__.py:45-47,165-168`) |
| Listas por perfil (`lists_per_profile` 20/20/100) | RPC `insert_product_list_with_plan_quota`, só em `api/routers/lists.py:263` | **Sim.** O restore insere direto e sem deduplicar (cada restore do mesmo arquivo cria até 200 listas). A rota Flask de listas está **sempre registrada** | `072:111-136`; `api/routers/users.py:555-563`; `web/routes/product_lists.py:100-116`; `web/__init__.py:169`. Não confirmei se o login Flask (`web/routes/auth.py:20-42`) aceita contas atuais |
| Perfis por conta (`max_profiles_per_account` 1/3/5) | RPC `insert_profile_with_plan_quota`, mais o trigger legado com teto 3 para INSERT direto | Parcialmente. Um INSERT direto fora da RPC cai no teto fixo 3, não no plano: Free poderia ter 3 | `072:152-205`; `api/routers/profiles.py:388` |
| Publicações imediatas por hora (`immediate_per_hour` 1/3/5) | RPC `reserve_post_plan_quota('immediate')`, chamada pela API antes do disparo; janela móvel de 60 min **por perfil** | Fica no banco, mas só se a API chamar. A contagem é **por perfil**: Pro com 3 perfis faz 9/h. A execução não confere | `073:100-144`; `api/routers/posts.py:1832-1835,2401-2404`; `api/plan_quotas.py:17-58` |
| Horários recorrentes por dia (`recurring_slots_per_day` 1/5/5) | RPC `reserve_post_plan_quota('recurring')`. Conta **horários configurados** (capacidade), não publicações executadas | **Sim.** Apagar o post devolve a vaga no mesmo dia (`ON DELETE CASCADE`). Dá para publicar, apagar e criar outro horário mais tarde no mesmo dia, sem limite. Depois de rebaixar o plano, as recorrências já criadas continuam rodando | `073:19-30` (FK CASCADE em `:23`); `073:146-180`; `api/routers/posts.py:1698-1702,2428-2448`; o claim legado não checa plano (`database/publish_jobs.py:151-253`) |
| Campanhas ativas por perfil (`active_campaigns_per_profile` 0/2/5) | `reserve_campaign_f4e` (SQL), chamada por `reserve_campaign_networks_f4e` SECURITY DEFINER | Não achei caminho de burla. A contagem é por `status='reserved_no_dispatch'` | `095_campaign_active_weekday_quota.sql:50-62`; `076_campaign_network_reservations.sql:129-162` |
| Dias de campanha / postagens de campanha por dia | SQL (`095:63-120`; `076:197-213`). Vagas `succeeded/failed/unknown` continuam contando, e o purge recusa apagar vaga concluída | Não achei caminho de burla | `076:204-213`; `097_campaign_post_purge.sql:17-27` |
| Período pago da campanha | SQL na reserva, na ativação e **no claim** (`campaign_paid_through > now()`) | Não. Esse é o único fluxo que já segue o modelo "banco manda" | `076:146-157,292-306`; `078:23-24`; pausa em `078:162-189` |
| "Redes pagas" / rede desligada (X) | **Só Python:** a constante `DISABLED_NETWORKS = {"x": ...}`. O banco aceita `x` | O banco não impõe nada. A API bloqueia em posts e na ativação de campanha. Não existe mapeamento plano → redes | `api/network_limits.py:19-23`; `api/routers/posts.py:495-499`; `api/campaign_activation.py:152`; `076:168-172` aceita `x` |
| Automação (`automation_enabled`) | Coluna existe (`072:17`). Não achei onde é imposta | **Não confirmado** | — |
| Limites de formato por rede (caracteres, mídias) | Só Python, espelho do front | É validação de formato, não de plano. Fora do escopo comercial | `api/network_limits.py:1-12` |

### 1(c) Mudança de plano: quem escreve

| Campo | Quem escreve | Proteção no banco |
|---|---|---|
| `users.plan_tier` | API em Python com service_role: webhook Asaas (`api/billing_events.py:178-183`), concessão ADMIN (`api/plan_grants.py:74-108`), expiração de concessão (`api/plan_grants.py:110-122`, laço de 5 min em `api/main.py:154-161`), cancelamento pelo titular (`api/billing_events.py:186-197`). SQL só no rebaixamento pendente de campanha, **e só quando `p_environment='production'`** (`078:167-173`) | Só `CHECK (plan_tier IN ...)` (`072:68-77`). Nada impede que qualquer código com service_role grave `premium` |
| `users.campaign_paid_through` | Só `api/plan_grants.py:85,98,118`. **O webhook Asaas nunca escreve.** Cliente pagante via Asaas recebe `plan_tier`, mas a reserva, a ativação e o claim de campanha exigem `campaign_paid_through > now()` (`076:146-150`, `078:24`) | Nenhuma |
| `plan_grants` | API (`api/plan_grants.py`), em vários statements sem transação (UPDATE das antigas, INSERT, UPDATE `users`) | RLS `block_all_api`, REVOKE anon/authenticated (`099_plan_grants.sql:7-39`) |
| `billing_*`, `plan_prices`, `plan_periods` | API. O webhook grava o evento depois de conferir o token (`api/routers/billing.py:52-75`) e o job aplica (`api/billing_events.py:280-303`) | RLS `block_all_api`, REVOKE anon/authenticated, GRANT só service_role (`098_billing_asaas.sql:138-152`). Preço e período auditados por trigger (`098:32-56`) |

Para o **cliente**, os caminhos diretos estão fechados: tabelas com RLS e sem GRANT, funções sem EXECUTE para anon/authenticated. A brecha é estrutural:
- **Toda a autoridade é a chave service_role da API.** O banco não distingue "webhook de pagamento confirmado" de "qualquer linha de código da API".
- **O vencimento não é imposto no momento do uso.** As RPCs de cota leem só `plan_tier` (`072:91-92`, `073:64-65`). A volta para Free depende de jobs da aplicação: o laço da API (`api/main.py:154-161`) e o job de cobrança, que roda a cada 10 min (`scheduler/__init__.py:566-575`). Esses jobs não rodam enquanto o Render Free estiver dormindo.
- **O pagamento em sandbox altera o plano real.** O staging usa o sandbox do Asaas (`api/config.py`; `api/asaas_client.py:30-31`) e grava `users.plan_tier`, que é a mesma tabela da produção. O único freio é a lista `ASAAS_SANDBOX_TESTERS`, uma variável de ambiente lida em Python (`api/asaas_client.py:38-43`, `api/billing_events.py:179-181`).
- **O webhook confia no payload.** Ele confere o token, mas não reconsulta o pagamento no Asaas antes de liberar o plano (`api/billing_events.py:254-270`).

### 1(d) Contagem do que o cliente usou

| Registro | Onde fica | Dá para subtrair ou apagar? |
|---|---|---|
| Publicação imediata | `plan_immediate_dispatches`, sem FK para `posts` (`073:7-17`) | Apagar o post **não** devolve. Mas a própria RPC apaga linhas com mais de 24 h (`073:103-105`), e `release_failed_post_plan_quota` remove quando não existe scheduler nem job (`073:185-201`). Não há histórico de uso maior que 24 h |
| Recorrência | `plan_recurring_slots`, com `ON DELETE CASCADE` a partir de `posts` (`073:22-30`) | **Sim:** apagar o post devolve a cota (`api/routers/posts.py:2428-2448` → `_delete_thread_cascade`) |
| Execuções legadas | `publish_jobs`, com CASCADE a partir de `posts` e `schedulers` (`053:5-6`) e de `post_metrics` (`101_post_metrics.sql:22-23`) | **Sim:** apagar o post apaga o histórico de execução e as métricas. O reset manual de 12/11 apagou 481 posts e os jobs em cascata (`docs/operations/reset-historico-posts-20261112.md`) |
| Vagas de campanha | `campaign_network_slots_f4e` | Não. O purge recusa vagas `succeeded/failed/unknown` (`097:17-27`) |
| Auditoria de plano | `audit_events`, gravado pela API (`api/plan_grants.py:106-107`) | A tabela não tem trigger de imutabilidade (`034_create_audit_events_table.sql`). Quem tem service_role altera |

**Conclusão:** o banco não tem um livro de consumo durável. O "uso" hoje é derivado de linhas que o próprio cliente consegue apagar pela API.

### 1(e) RLS e GRANTs das tabelas críticas

- A varredura de 07/11 encontrou **63/63 tabelas `public` com RLS ativo e nenhuma policy permissiva**, sem EXECUTE para anon/authenticated em funções SECURITY DEFINER (`docs/SEGURANCA-AUDITORIA-20261107.md:12`). Na época o risco residual foi classificado como ALTO por causa da chave privilegiada no backend (S-01).
- `057_revoke_table_ddl_grants.sql:1-35` diz que `users`, `posts`, `schedulers`, `profiles`, `products` etc. **ainda têm SELECT/INSERT/UPDATE/DELETE concedidos a anon/authenticated**, e só o RLS segura. Uma camada de defesa só.
- `publish_jobs` e `publication_claims`: REVOKE ALL de anon/authenticated (`056_harden_internal_grants_and_fk_indexes.sql:8-11`).
- `plan_limits`, `plan_*`, `billing_*`, `plan_grants`, `account_billing_identity`, `post_metrics`, `apscheduler_jobs_staging`, `admin_wake_log`: RLS e REVOKE explícitos (`072:138-145`; `073:34-39`; `098:138-152`; `099:30-39`; `093:24-34`; `101:96-116`; `067:25-26`; `wake-before-posts-cron.sql:21-24`).
- `platform_*`: as migrations 089/090/091 têm RLS. Não conferi o GRANT de cada uma.
- **Não confirmado:** as tabelas criadas à mão em 12/11 (`bkp_reset_20261112_*`, `reset_historico_20261112_ids`, `migration_backup_staging_to_production_20261112`). Elas não passaram por migration. No Supabase, o padrão é tabela nova em `public` receber GRANT para anon/authenticated. Se o RLS estiver desligado nelas, posts e jobs copiados ficam legíveis com a chave publicável.

---

## 2. Desenho-alvo: o banco como autoridade

Princípio: a API e os workers só **pedem**. Quem decide se pode criar, se pode executar, quanto já foi consumido e qual é o plano vigente são funções e constraints do banco. A decisão vale para qualquer papel, inclusive o service_role. Quem estiver com a chave da API não consegue mais "dar" plano nem pular cota.

### 2(a) Uma fila só, com claim atômico e sem ambiente

- **A materialização fica no banco.** Uma função `materialize_due_publications()`, rodada por `pg_cron` a cada minuto, lê as regras de `schedulers` (dias, horário, fuso, `run_date`) e insere em `publish_jobs` uma ocorrência por **horário agendado**: `idempotency_key = scheduler_id || ':' || scheduled_at_utc`, com UNIQUE. A chave deixa de depender do relógio de quem executa (corrige `scheduler/__init__.py:157-167`). Rodar duas vezes cria as mesmas linhas.
- **Claim:** `claim_publication(p_worker text, p_worker_version text)`, SECURITY DEFINER, `search_path=''`. Ele:
  - seleciona `pending` vencido dentro da janela, com `FOR UPDATE SKIP LOCKED`;
  - revalida o direito (2b);
  - grava um lease (`locked_by`, `locked_at`, `lease_until`) e um `claim_token`.
  - **Não recebe ambiente.** Qualquer instância, produção ou staging, pode chamar.
- **Fechamento:** `mark_external_started(job, token)`, `finish_publication(job, token, status, ...)` e `recover_expired_leases()` ficam todos no banco. O lease vencido antes do contato externo volta a `pending`; depois do contato externo vira `unknown` e nunca é repetido automaticamente. As regras de `078:110-160` passam a valer também para o legado.
- **Garantia honesta:** o banco garante **no máximo uma** entrega por ocorrência, e uma só execução ativa por vez. "Exatamente uma vez" contra Threads/Meta/TikTok só existe se o provedor aceitar chave de idempotência. Sem isso, o estado `unknown` com conciliação manual continua sendo necessário (`api/routers/posts.py:1194-1250`).
- O APScheduler deixa de ser a fonte de horário. O worker só faz `loop: claim → publica → finish`.

### 2(b) Cotas impostas pelo banco no momento de criar e no momento de executar

- **Livro de consumo** `plan_usage_ledger(id, user_id, profile_id, kind, unit_at, period_key, publish_job_id, created_at)`:
  - append-only, sem FK com CASCADE para `posts`;
  - trigger que recusa UPDATE/DELETE para todos os papéis, menos a rotina de retenção do apagamento de conta.
  - Apagar post não devolve a cota do período.
- **No claim:** `claim_publication` só entrega o job se o consumo do período, lido no livro, estiver abaixo do limite do **plano vigente** (2c). O consumo é gravado na mesma transação do claim. Assim:
  - rebaixamento, vencimento e "apagar e recriar" deixam de funcionar;
  - o job recusado vira `failed` com motivo `plan_quota_exceeded`, ou fica retido (ver as perguntas 3 e 5).
- **Na criação** (aviso cedo, não é a barreira final): triggers `BEFORE INSERT` em `products`, `product_lists`, `profiles`, `schedulers` e `posts(publish_immediately)` chamam funções SECURITY DEFINER que travam `users FOR UPDATE` e comparam com `plan_limits`. Um trigger vale para qualquer INSERT: API, restore, Flask legado ou SQL. As RPCs atuais (`072`, `073`) viram atalhos finos ou somem.
- Os limites de **capacidade** (produtos, listas, perfis, horários configurados) podem devolver vaga ao apagar, porque medem o que existe agora. Os limites de **consumo** (por hora, por dia, campanhas) nunca devolvem.
- ADMIN fica isento, com o papel lido no banco (`users.access`), como já é hoje.

### 2(c) Plano e vencimento escritos só por funções do banco

- **Tabela `account_entitlements(id, user_id, tier, valid_from, valid_until, source, source_ref, created_at)`:**
  - `source` ∈ `asaas_payment`, `admin_grant`, `downgrade`;
  - `source_ref` é único por fonte: id do pagamento, id da concessão.
- **Funções de escrita:**
  - `billing_apply_paid_payment(env, payment_id, ...)`: idempotente; deriva tier e período do checkout gravado; confere `value_cents >= preço do plan_prices`; calcula `valid_until` no banco.
  - `billing_apply_reversal(...)`.
  - `admin_grant_plan(admin_id, user_id, tier, until, reason)`: confere que `admin_id` tem `access='ADMIN'` no banco.
  - `admin_revoke_plan(...)`.
- **Plano vigente:** `effective_tier(user_id)` = maior tier com `valid_from <= now() < valid_until`, senão `free`. Cotas e claims leem essa função. O vencimento passa a valer na hora do uso, sem depender de job.
- **`users.plan_tier` e `users.campaign_paid_through` viram cache.** Um trigger `BEFORE UPDATE OF plan_tier, campaign_paid_through ON users` recusa a alteração, a não ser que ela venha das funções acima (flag local de transação definida dentro delas). Quando a main não depender mais desse UPDATE direto, entra um papel de banco próprio para a API, sem UPDATE nessas colunas (2e).
- **Sandbox:** eventos com `environment='sandbox'` nunca geram direito sobre conta real, exceto para contas marcadas numa tabela do banco `billing_sandbox_accounts`. A variável de ambiente deixa de ser o freio (pergunta 4).
- **Autenticidade do pagamento:** o banco não fala com o Asaas. A API continua conferindo o token e deve **reconsultar o pagamento no Asaas** antes de chamar `billing_apply_paid_payment`. O banco garante a consistência: valor, período, idempotência e checkout existente da mesma conta.

### 2(d) Despachante no banco

- `pg_cron` roda `materialize_due_publications()`, `recover_expired_leases()`, `expire_entitlements_cache()` (só atualiza o cache de `users`) e o despertar.
- **Despertar:** a função atual (`docs/operations/wake-before-posts-cron.sql`) deixa de filtrar `environment='production'`. Quando existir job `pending` vencido ou prestes a vencer, ela acorda os workers cadastrados numa tabela `publication_workers(name, wake_url_secret_name, enabled)`, com segredos no Vault, seguindo a ordem de prioridade (pergunta 1). Quem acordar primeiro pega o claim. O lease impede a duplicação.

### 2(e) RLS fechado e GRANT mínimo

- `REVOKE SELECT, INSERT, UPDATE, DELETE` de anon/authenticated em todas as tabelas de negócio. Isso tira a dependência de uma camada só (`057:4`).
- RLS e REVOKE nas tabelas `bkp_*` e `migration_backup_*`, ou exportar e apagar essas tabelas (apagar exige autorização).
- Todas as funções novas com `SECURITY DEFINER SET search_path=''`, `REVOKE ALL FROM PUBLIC, anon, authenticated` e EXECUTE só para o papel que precisa delas.
- Fase final: papéis `app_api` (sem UPDATE em colunas de plano, sem DELETE em livro e auditoria) e `app_worker` (só EXECUTE nas funções de claim e fechamento) no lugar do service_role único.

### 2(f) Auditoria imutável

- `entitlement_events` e `plan_usage_ledger` append-only, com trigger que recusa UPDATE/DELETE e grava `current_user`, `txid_current()` e o motivo.
- `plan_limits_audit` e `plan_pricing_audit` já existem (`072:30-50`, `098:32-56`). Falta protegê-las contra DELETE.

### O que acontece com a separação atual

| Peça atual | Destino |
|---|---|
| `SCHEDULER_ENVIRONMENT` / `current_environment()` na execução | Sai da fila e do claim. Pode continuar só como **rótulo de origem** em log e em configuração de plataforma (`platform_ai_*`, `platform_shopee_*` têm credencial por ambiente, `089:7-25`, `090:7`). Isso é configuração, não autoridade de execução; ver pergunta 7 |
| `schedulers.environment`, `campaign_*_f4e.source_environment` | Param de ser filtro. Ficam como coluna histórica (`created_by_environment`). Remover coluna é destrutivo e exige autorização |
| `apscheduler_jobs` / `apscheduler_jobs_staging` | Esvaziadas conforme cada agenda migra para a fila do banco. A tabela de staging cai quando estiver vazia (com autorização) |
| `claim_campaign_publication_f4e(p_environment, ...)` | Nova versão sem ambiente. A antiga continua como wrapper até que todas as instâncias usem a nova |
| `pause_expired_campaigns_f4e` só na produção (`078:167`) | Passa a ser regra única, independente do ambiente |
| Cron de despertar só da produção | Acorda qualquer worker cadastrado |

---

## 3. Riscos encontrados (priorizados)

Nenhum caminho **CRÍTICO** está confirmado no repositório. Dois são CRÍTICOS **se** o catálogo vivo confirmar a condição indicada.

| # | Nível | Risco | Evidência |
|---|---|---|---|
| A1 | **ALTO** | **Rebaixamento ou vencimento não para a execução.** Recorrências e "Agora" criados num plano maior continuam publicando depois da volta a Free, porque o claim legado não consulta plano nem cota. É exatamente o caso "continuar usando um limite que o plano não cobre" | `database/publish_jobs.py:151-253` (sem plano); `scheduler/*.py` sem referência a plano; compare com a campanha, que checa (`078:23-24`) |
| A2 | **ALTO** | **Cota de recorrência devolvida ao apagar o post.** Publicar, apagar e recriar um horário mais tarde no mesmo dia permite publicações diárias acima do plano (Free: 1/dia) | `073:22-30` (CASCADE `:23`), `073:151-174`; `api/routers/posts.py:2428-2448` |
| A3 | **ALTO** (bloqueia a unificação) | **A chave de idempotência do cron usa o relógio de execução.** Se dois executores pegarem a mesma agenda em minutos diferentes, a publicação sai duplicada. Hoje a separação esconde isso; não dá para unificar sem corrigir | `scheduler/__init__.py:157-167` |
| A4 | **ALTO** | **O restore de backup ignora as cotas de produtos e listas.** Restaurar o mesmo arquivo várias vezes cria listas sem teto. O checksum não amarra a conta, então produtos de um backup de outra conta entram sem limite | `api/routers/users.py:484-584` (inserts diretos em `:549-552`, `:555-563`; payload do checksum sem `user_id` em `:526-535`) |
| A5 | **ALTO** | **Plano gravável por qualquer código com service_role, sem trilha imutável.** Webhook, concessão e expiração são UPDATEs comuns em `users`. A auditoria é gravada pela própria API (`audit_events` sem imutabilidade). Se a chave vazar, dá para obter plano sem pagar | `api/billing_events.py:178-183`; `api/plan_grants.py:74-122`; `072:68-77` (só CHECK); `034_create_audit_events_table.sql` |
| A6 | **ALTO** | **O vencimento depende de job da aplicação.** As cotas leem `plan_tier` sem data. Concessão vencida ou assinatura em atraso continuam valendo até o laço ou o job rodar, e eles não rodam com o Render dormindo | `072:91-92`; `073:64-65`; `api/main.py:154-161`; `scheduler/__init__.py:566-575` |
| A7 | **ALTO** (funcional/comercial) | **Pagamento Asaas não libera campanha.** O webhook grava só `plan_tier`; campanha exige `campaign_paid_through`, que só a concessão ADMIN escreve. Hoje o cliente pagante fica bloqueado; pela lógica, só o ADMIN "vende" campanha | `api/billing_events.py:264-270`; `076:146-150`; `078:24`; escrita só em `api/plan_grants.py:85,98,118` |
| C1 | **CRÍTICO se confirmado** | Tabelas de backup criadas à mão em 12/11 sem RLS/REVOKE ficariam legíveis com a chave publicável (posts, jobs, agendas) | `docs/operations/reset-historico-posts-20261112.md`; `docs/operations/migracao-agendamentos-staging-para-producao-20261112.md`. **Não confirmado** |
| C2 | **CRÍTICO se confirmado** | `users` e `posts` ainda concedem UPDATE a anon/authenticated (`057:4`). Se o RLS de `users` estiver desligado ou com policy aberta, um cliente com JWT do Supabase Auth altera `plan_tier` direto | `057_revoke_table_ddl_grants.sql:1-35`. A varredura de 07/11 achou RLS ativo (`SEGURANCA-AUDITORIA-20261107.md:12`). **Não reconfirmado depois de 07/11** |
| M1 | MÉDIO | **Sandbox altera plano real.** O staging (sandbox Asaas) escreve em `users.plan_tier`, compartilhado. O freio é uma variável de ambiente; a detecção sandbox/produção é por substring da URL | `api/asaas_client.py:30-43`; `api/billing_events.py:178-182` |
| M2 | MÉDIO | O webhook aplica o payload sem reconsultar o Asaas. Quem tiver o token forja `PAYMENT_CONFIRMED` | `api/routers/billing.py:52-75`; `api/billing_events.py:254-270` |
| M3 | MÉDIO | A cota "por hora" e a "por dia" são **por perfil**. Pro com 3 perfis faz 9 imediatas/h e 15 horários/dia. Pode ou não ser a intenção (pergunta 2) | `073:118-121`, `073:152-155` |
| M4 | MÉDIO | Rota Flask legada de listas sempre registrada, sem cota. Produtos legados só com flag | `web/__init__.py:165-169`; `web/routes/product_lists.py:100-116`. Não confirmei se o login legado está alcançável |
| M5 | MÉDIO | O trigger de perfis tem teto fixo 3. Um INSERT fora da RPC daria 3 perfis ao Free | `072:156-169` |
| M6 | MÉDIO | O histórico de consumo some: imediatas são apagadas após 24 h pela própria RPC, e `publish_jobs` e `post_metrics` caem em cascata com o post | `073:103-105`; `053:5-6`; `101:22-23` |
| M7 | MÉDIO | Regra de negócio diferente por ambiente dentro do SQL: o rebaixamento pendente só é aplicado quando `p_environment='production'` | `078:167-173` |
| M8 | MÉDIO | O staging executa publicações de clientes reais (as agendas criadas lá) com código ainda não promovido. Com a unificação, isso vira regra, a menos que haja um portão de versão | `database/schedulers.py:100-123`; pergunta 1 |
| B1 | BAIXO | `plan_grants` é escrita em vários statements sem transação. Uma falha no meio deixa concessão e `users` desalinhados (a compensação é parcial) | `api/plan_grants.py:87-102` |

---

## 4. Fases de implementação (risco/valor), testes e reversão

Regra transversal (`docs/RULES.md:25`): toda migration é aditiva e compatível com o código que estiver rodando nos dois serviços. Main e staging hoje têm o mesmo conteúdo, então cada fase vai primeiro para o banco, depois para staging e depois para main. A função antiga só sai quando nenhuma instância a usar.

### Fase 0: verificação só de leitura (depende de autorização do Rafa)

Consultas a rodar no Supabase (todas `SELECT` em catálogo, sem dados de clientes):
- `SELECT relname, relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE nspname='public' AND relkind='r' AND NOT relrowsecurity;`
- `SELECT * FROM pg_policies WHERE schemaname='public';`
- `SELECT table_name, grantee, privilege_type FROM information_schema.role_table_grants WHERE table_schema='public' AND grantee IN ('anon','authenticated') ORDER BY 1;`
- `SELECT proname, prosecdef, proacl FROM pg_proc WHERE pronamespace='public'::regnamespace;`
- `SELECT jobid, schedule, command, active FROM cron.job;`

**Saída:** confirmar ou descartar C1/C2 e corrigir este documento.

### Fase 1: fechar as burlas sem mudar a arquitetura

**Valor:** alto. **Risco:** baixo; é aditivo.
1. RLS e REVOKE nas tabelas `bkp_*` e `migration_backup_*` se a Fase 0 confirmar C1. REVOKE de SELECT/INSERT/UPDATE/DELETE de anon/authenticated nas tabelas de negócio.
2. `plan_usage_ledger` append-only e trigger anti-UPDATE/DELETE.
3. Triggers `BEFORE INSERT` de capacidade em `products`, `product_lists` e `profiles`, que leem `plan_limits` e `users` sob `FOR UPDATE`, com o mesmo advisory lock de `072:160,185`. Fecham A4, M4 e M5 para qualquer chamador. As RPCs de 072 continuam funcionando, porque a checagem é a mesma e idempotente.
4. **Portão de execução no banco:** trigger `BEFORE UPDATE OF status ON publish_jobs` quando passa de `pending` para `running`. Ele valida plano vigente e consumo do período e grava no livro. Vale para o claim Python atual sem mudar código. Fecha A1 e A2.
   - **Reversão:** `DROP TRIGGER`, sem mexer em dado.

**Testes SQL** (padrão `tests/sql/test_*_postgres.py` com Postgres real):
- INSERT direto como `service_role` acima do limite falha;
- duas sessões concorrentes no limite: só uma passa;
- apagar post não reduz o livro;
- Free com recorrência criada em Pro: o claim é recusado;
- UPDATE/DELETE no livro falham para todos os papéis;
- `SET ROLE anon` e `SET ROLE authenticated` recebem `permission denied` em `users`, `posts`, `schedulers`, `publish_jobs` e `billing_*`.

**Testes de API:**
- restore com listas e produtos acima do teto devolve 409 e não grava;
- restore de backup de outra conta é recusado;
- publicar agora depois de rebaixar devolve 409;
- recorrência não dispara depois de rebaixar.

### Fase 2: plano autoritativo

**Valor:** alto. **Risco:** médio; mexe em cobrança.
1. `account_entitlements`, `entitlement_events` (imutável), `effective_tier()`, `billing_apply_paid_payment()`, `billing_apply_reversal()`, `admin_grant_plan()`, `admin_revoke_plan()`.
2. **Modo sombra:** as funções gravam junto com o código atual, e um relatório SQL compara `effective_tier` com `users.plan_tier`.
3. A API passa a chamar só as funções. Depois do deploy nas duas instâncias, liga o trigger que bloqueia UPDATE direto em `plan_tier` e `campaign_paid_through`.
4. Cotas e claims leem `effective_tier()`. Fecha A5, A6, A7 (o pagamento passa a definir `valid_until`), M1 e M2 (com reconsulta ao Asaas na API).
   - **Reversão:** desligar o trigger de bloqueio. `users.plan_tier` continua sendo cache, então o código antigo volta a funcionar.

**Testes SQL:**
- UPDATE direto de `plan_tier` como service_role falha;
- evento sandbox não gera direito para conta fora de `billing_sandbox_accounts`;
- pagamento repetido é idempotente;
- valor abaixo do preço é recusado;
- concessão vencida vira Free **sem job** (`effective_tier` no instante seguinte);
- estorno rebaixa;
- concessão por não ADMIN falha.

**Testes de API:**
- webhook com token válido e pagamento inexistente no Asaas não libera plano;
- cliente Asaas pagante consegue ativar campanha.

### Fase 3: fila única no banco

**Valor:** médio-alto. **Risco:** alto; mexe em publicação.
1. `materialize_due_publications()` com chave `scheduler_id:scheduled_at_utc` (fecha A3), `claim_publication()` sem ambiente com lease, `finish`, `mark_external_started` e `recover_expired_leases()` em SQL, e `pg_cron`.
2. Isso reaproveita a fundação F0 (`dispatch_mode='central'`, `dispatch_revision`, `dispatch_cancelled_at` de `068`). O worker de qualquer instância passa a fazer `claim → publica → finish`.
3. Começa **só com agendas novas** em `central`. O legado continua como está.
   - **Reversão:** voltar `dispatch_mode` das agendas novas para `legacy` e recriar os jobs APScheduler (precisa de rotina de reidratação testada antes).

**Testes SQL:**
- materializar duas vezes cria as mesmas linhas;
- DST e fuso: horário de parede do usuário;
- 2 a 10 sessões concorrentes chamando `claim_publication` sobre N jobs: cada job é entregue uma única vez;
- lease vencido sem contato externo volta a `pending`;
- lease vencido com contato externo vira `unknown` e não repete;
- janela de 1 h expira sem envio tardio;
- claim recusa conta sem direito.

**Testes de worker:** SIGTERM antes da fronteira externa devolve o job; produção e staging drenando juntas não duplicam (com publicador mockado).

### Fase 4: migrar o legado e as campanhas

**Risco:** alto; precisa de janela acompanhada.
1. Por lotes, numa transação: `dispatch_mode='central'`, `dispatch_revision+1` e `DELETE` da linha correspondente em `apscheduler_jobs*`. Um APScheduler que dispare uma agenda já migrada não encontra nada, porque `get_by_id` filtra `legacy` (`database/schedulers.py:9-19,75-86`). A cópia de segurança segue o formato de 12/11.
2. Campanhas: nova `claim_campaign_publication(p_worker)` sem ambiente. A assinatura antiga vira wrapper. A pausa e o rebaixamento ficam iguais para todos (fecha M7).
3. O despertar passa a acordar os workers cadastrados, sem filtro de ambiente.
   - **Reversão por lote** usando a tabela de backup.

**Testes:**
- uma agenda migrada nunca é executada por APScheduler e fila ao mesmo tempo;
- contagem antes e depois de cada lote;
- agenda `cron` com o próximo horário a menos de 5 min fica fora do lote.

### Fase 5: remover a separação

1. Tirar `current_environment()` de `database/publish_jobs.py`, `database/schedulers.py`, `scheduler/campaign_dispatch.py` e `api/campaign_activation.py:315`, e retirar `apscheduler_jobs_staging` do `init()`.
2. `ORBITAL_CENTRAL_DISPATCH_ENABLED` some, porque o modo central passa a ser o único.
3. `DROP` de `apscheduler_jobs_staging`, wrappers antigos e (se o Rafa quiser) as colunas de ambiente. **Tudo isso é destrutivo e exige autorização expressa.**
4. Papéis `app_api` e `app_worker` no lugar do service_role único.

**Testes:** suíte completa, mais a busca por `environment` nos caminhos de execução retornando vazio.

---

## 5. Perguntas que dependem do Rafa

1. **Staging executando publicação real de cliente.** Com a fila única, qualquer instância pega qualquer job. Pode deixar o staging (código ainda não promovido) publicar para clientes? Ou o banco deve exigir versão mínima do worker no claim (ou dar prioridade à produção)?
2. **Escopo das cotas de consumo:** "publicações por hora" e "por dia" contam por **conta** ou por **perfil**? Hoje é por perfil (Pro = 3×).
3. **Recorrência:** o limite é de **horários configurados** (capacidade) ou de **publicações executadas por dia** (consumo)? E qual dia vale: o calendário BRT ou o fuso do usuário? Pela decisão, apagar post não devolve; confirmar que vale para o "dia".
4. **Sandbox Asaas:** pagamento no sandbox (staging) pode mudar o plano de alguma conta real? Se pode, só para contas marcadas numa tabela do banco?
5. **Excedente depois de rebaixar ou vencer:** agendas acima do novo limite são recusadas uma a uma na hora (viram `failed`), pausadas por inteiro, ou o cliente escolhe quais ficam?
6. **Campanha para cliente pagante pelo Asaas:** o pagamento de Pro/Premium já deve liberar campanha (preencher `valid_until` e `campaign_paid_through`)? Hoje só a concessão ADMIN libera.
7. **Credenciais de plataforma por ambiente** (`platform_ai_*`, `platform_shopee_*`, chave Asaas sandbox/produção): continuam separadas? Elas são configuração, não autoridade de execução.
8. **Redes por plano:** quais redes cada plano libera? (X hoje é bloqueado só no Python, para todos.)
9. **Autorizações operacionais:** rodar a Fase 0 (só leitura) no Supabase compartilhado; e, mais adiante, apagar ou fechar as tabelas `bkp_*`/`migration_backup_*` e remover colunas ou tabelas de ambiente (destrutivo).
