# F0 — Piloto compatível do despacho central (staging; 02/11/2026)

> **Escopo isolado:** este PR de homologação transporta exclusivamente o núcleo F0 do PR de desenvolvimento [#198](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/198), sem antecipar as telas de criação de Posts, campanhas, galeria Shopee ou planejamento de 30 dias.

## Contrato autorizado por Rafa

- Staging é exclusivo do desenvolvedor. O Supabase é compartilhado.
- **Opção 3:** preservar as cinco agendas `cron` atuais de staging, sem migrar, pausar nem cancelar.
- Novas intenções centrais serão publicadas somente pela produção no rollout posterior. **Nesta implantação de staging a flag permanece DESLIGADA**.
- Não disparar publicações de teste em redes sociais, não alterar produção, não alterar versão `3.0.0`.

## Alteração de código nesta etapa

- `database/migrations/068_central_dispatch_compatibility.sql` adiciona três colunas a `schedulers`: `dispatch_mode` com `DEFAULT 'legacy'`, `dispatch_revision` e `dispatch_cancelled_at`, com constraints e índice parcial. Não atualiza linhas existentes e não altera jobstores/filas.
- O runner `database/migrations/__init__.py` executa migrações no boot com advisory lock e registra cada nome em `public.migrations`. **O deploy inicial de staging aplicará este DDL ao Supabase compartilhado**. O schema é compatível com a main antiga, que continua a inserir linhas `legacy` por default.
- `ORBITAL_CENTRAL_DISPATCH_ENABLED` é `false` por default; nenhuma configuração Render foi solicitada para ligá-la. Sem gate, os dois executores e suas tabelas atuais continuam separados. O `unknown` permanece terminal.
- O código central opt-in já prepara: novos agendamentos persistidos como `central`, espelho somente em produção com prefixo `central:`, cancelamento lógico, `Agora` idempotente, `date` expirada terminal `failed`; **essas rotas não serão acionadas durante o piloto com gate false**.

## Preflight e rollback

1. Registrar `staging` HEAD, deploy live anterior, CI e contagens read-only: 5 agendamentos `staging` e 5 IDs presentes no jobstore; nenhuma coluna `dispatch_mode` antes do deploy.
2. Mesclar somente este PR após testes verdes. O Render do staging está configurado em auto deploy por commit; **não disparar manualmente em duplicidade**.
3. Acompanhar o deploy até `live`, confirmar o novo commit, health API e logs do boot/migration.
4. Consultar read-only `information_schema`, `public.migrations`, contagens de `schedulers` e jobstores após deploy, e checar que o staging continua inicializando o executor local normal.
5. Se falhar, preservar dados e diagnosticar; rollback do código **não reverte DDL**, mas a migration 068 é aditiva, com defaults compatíveis. Nunca apagar registro de migration nem as colunas para forçar rollback.
6. Não publicar em rede social. Não promover `staging` a `main` e não ativar `ORBITAL_CENTRAL_DISPATCH_ENABLED` sem nova autorização e E2E controlado.

## Verificação automatizada

O código F0 foi testado no branch de desenvolvimento em [CI #41534333686](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41534333686) (API/scheduler e frontend aprovados). Este PR isolado precisa de CI independente e de confirmação do Render/Supabase após deploy.

> Se o estado de migração ou contagem divergir do preflight, **parar** e não executar tentativa destrutiva de correção.
