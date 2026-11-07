# Protocolo temporário — GitHub Actions indisponível (07/11/2026)

**Rastreamento central:** [issue #305 — HOLD do Actions](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/issues/305) (aberta; os gates ainda não foram restabelecidos).

**Decisão do proprietário:** Rafa autorizou continuar implementando, corrigindo e atualizando o Auto Orbital em **branches isoladas**, com versionamento e registro de cada tarefa, enquanto o GitHub Actions não estiver disponível. **Nenhum merge em `staging`/`main` nem promoção/deploy de código ficará autorizado pela simples existência de testes locais.** A validação pendente será concluída quando o Actions voltar a executar os gates.

## 1. Fotografia verificável, não suposição de saúde atual

| Item | Estado constatado em 07/11/2026 |
| --- | --- |
| Produção / `main` | `VERSION=3.2.0`; HEAD `561345b102f95979eb979167ec52e9d823681768` |
| Integração / `staging` | `VERSION=3.2.0`; HEAD `9eede9d79db65263094c27c43f25a022f9e83ec2` |
| Release candidata | PR [#303](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/303), `release/3.3.0-20261105` → `staging`, **aberta e não mesclada**; versão 3.3.0 preparada somente nessa branch |
| Credenciais / Shopee Vídeo | PR [#304](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/304), `feat/credenciais-alfabeticas-shopee-video-staging-20261105` → `staging`, **aberta e não mesclada**; teste local 2/2 PASS, CI/build/QA staging pendentes |
| GitHub Actions | [Run #42068760376](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42068760376): `completed/failure`, 2 tentativas; jobs barrados antes de executar os testes. Captura fornecida por Rafa em 05/11 informa problema de pagamentos recentes **ou** limite de gastos, sem discriminar qual |
| Render/Supabase | Última evidência documental em 05/11: produção 3.2.0 e staging em 9eede9d; **não foram revalidados neste registro**. Banco é único e compartilhado; os dois pg_cron existentes permanecem intocáveis |
| Custos | Nenhuma alteração de cobrança, orçamento, método de pagamento, plano ou contratação autorizada |

Este registro afirma **indisponibilidade do gate de CI para a release**, não indisponibilidade do GitHub inteiro, do Render ou do produto. Não interpretar a falha de provisionamento de runner como falha dos testes de código; tampouco declarar CI verde. A situação da conta e o restabelecimento devem ser **reverificados** antes da retomada.

## 2. Operação autorizada enquanto o gate estiver bloqueado

1. **Uma branch de tarefa por mudança coesa**, originada da `staging` no SHA identificado; evitar alterações diretas em `staging` ou `main`. Se houver dependência real entre branches, declarar base, cadeia e plano de integração explicitamente.
2. Trabalhar e realizar **commit/push somente na branch de tarefa**. PRs de acompanhamento para `staging` podem ser abertos em **draft**, com etiqueta textual `AGUARDANDO ACTIONS`, sem merge nem auto-merge; verificar que workflows podem falhar antes do início.
3. **Testes locais proporcionais à mudança** continuam obrigatórios quando viáveis: unitários/contratos, TypeScript/build, linters, testes Python/SQL isolados e revisão de segurança. Registrar comandos, quantidades, PASS/FAIL/SKIPPED e limitações. Se não for possível testar, marcar **NÃO EXECUTADO** e não afirmar entrega homologada.
4. **Sem deploy de mudanças pendentes** em staging ou produção, sem aplicar migrações SQL, alterar flags, scheduler, OAuth, webhooks, crons, fila ou serviços compartilhados por conta deste protocolo. Qualquer operação externa com risco requer decisão própria e compatibilidade com produção.
5. **Sem bypass** de branch protection, workflows, gate SemVer ou revisão; sem merge direto, force push, tornar o repositório público, ampliar limite de gastos ou cadastrar pagamento para liberar CI.
6. Cada tarefa deve atualizar **`CHANGELOG.md` em `[Não lançado]`**, a documentação do módulo e o **TASK.md vivo do Vault** (ou registrar branch documental pendente de integração). Atualizações de contrato/arquitetura/segurança exigem atualização do Guia Mestre e do espelho no Vault. Reabrir os arquivos escritos, conferir coerência e referências.
7. Preservar os PRs #303 e #304 com o status **AGUARDANDO ACTIONS**; não declarar integração da #304 nem lançamento da 3.3.0. Ao entrar uma nova tarefa, revisar conflitos/dependências com ambos.

## 3. SemVer durante a suspensão

- A fonte oficial é o arquivo `VERSION`; `main` e `staging` permanecem em **3.2.0** enquanto não houver release validada. Não fazer bump a cada tarefa por conveniência.
- **Classificar antes de editar:** `docs/sem bump` para documentação isolada, `PATCH` para correção retrocompatível, `MINOR` para recurso novo compatível, `MAJOR` para mudança incompatível. Registrar a classificação **candidata**, seus motivos e o impacto acumulado no changelog.
- A PR #303 já contém **candidata 3.3.0** somente na branch de release. Ela **não** representa os trabalhos futuros automaticamente. Ao reabrir o gate, decidir quais branches aprovadas pertencem a essa release, recalcular o incremento SemVer conforme o diff final, atualizar `VERSION`, changelog datado e notas de release na branch adequada, sem salto arbitrário. Não promover uma release cujo conteúdo e documentação estejam defasados.
- Não presumir que todos os trabalhos acumulados caibam em 3.3.0; alterações incompatíveis ou separadas exigem decisão de release independente.

## 4. Registro obrigatório por tarefa

Adicionar uma entrada datada em `TASK.md` no Vault e uma nota `[Não lançado]` no changelog. Modelo:

| Campo | Preencher |
| --- | --- |
| Tarefa e decisão de Rafa | Pedido, escopo autorizado e critérios de aceite |
| Branch, base e PR | Branch de trabalho, SHA-base, SHA(s) de commit, link do PR/draft |
| Versão | `VERSION` observado, tipo candidato (docs/PATCH/MINOR/MAJOR), justificativa e release alvo se conhecida |
| Alterações | Arquivos, módulos, APIs, migrations, flags, impacto nos ambientes/dados e eventuais dependências |
| Evidências locais | Comandos de teste, resultado real e restrições do ambiente; segurança/ownership quando aplicável |
| Gates pendentes | `ACTIONS_INDISPONÍVEL`; CI completo, build, QA autenticado, staging/live, produção/externo, conforme o caso |
| Estado | `EM_DESENVOLVIMENTO` → `IMPLEMENTADO_EM_BRANCH` → `TESTADO_LOCAL` → `AGUARDANDO_ACTIONS` → `CI_APROVADO` → `STAGING_HOMOLOGADO` → `PRODUÇÃO_VERIFICADA` |
| Próximo passo / responsável | Verificação exata, eventual aprovação necessária, prazo só se confirmado |

Não marcar etapas seguintes como concluídas por consequência automática das anteriores. Distinguir código escrito, teste local, merge, deploy LIVE, funcionamento autenticado e publicação externa de fato.

## 5. Fila existente e ordem de retomada

| Item | Branch/PR | Prova existente | Falta quando CI voltar |
| --- | --- | --- | --- |
| Shopee Vídeo/card de Credenciais | PR #304 → staging | 2/2 testes Node locais; card deliberadamente sem conexão/API | Build TS/frontend, CI, revisão/QA visual; merge autorizado na staging; validar que aprovação externa não existe |
| Release 3.3.0 (candidata) | PR #303 → staging | Notas de release/CHANGELOG/VERSION na branch; staging pré-release 9eede9d historicamente LIVE | Incorporar apenas mudanças aprovadas, revisar diff e versão, rodar suite completa e SemVer; integrar staging, conferir deploy e saúde, PR staging→main, CI e deploy de produção |
| Novas tarefas | Branch isolada por tarefa | A registrar por trabalho | Manter pendências explícitas, revalidar tudo sobre o SHA final aprovado |

O PR #198 é WIP histórico e **não** deve ser incorporado por inferência. Nenhum PR deverá ser integrado apenas por estar `mergeable=true`.

## 6. Checklist para declarar que o Actions voltou

1. Rafa confirma que a restrição da conta foi esclarecida, ou uma tentativa autorizada demonstra jobs realmente iniciando. **Não** presumir reset automático nem cobrar/alterar orçamento.
2. Confirmar que os jobs obrigatórios executam **steps reais**, terminam verdes no **SHA exato** a integrar e incluem testes API/Python, frontend/TypeScript, PostgreSQL/SQL e gates SemVer pertinentes. `failure` anterior aos steps continua bloqueio, não teste aprovado.
3. Reconciliar branches/PRs, revisar diffs e conflitos, regressões cruzadas e changelog. Reexecutar testes locais se o código/base mudou; registrar evidências.
4. PR de cada tarefa para `staging` com revisão e CI; homologar Render staging no SHA esperado, health/logs e fluxos afetados, sem emitir publicações externas não autorizadas.
5. Preparar e validar release SemVer final; somente então PR `staging` → `main`, CI verde e deploy sem interrupção; verificar SHA, readiness, logs, segurança e **exatamente os dois cron jobs já existentes** (`auto-orbital-wake-v1` `*/2` e `auto-orbital-uptime-sample-v1` `*/12`).
6. Atualizar aplicativo e Vault com PRs, SHAs, versão, data, testes, ambiente e pendências; deixar este protocolo como histórico e encerrar o estado `ACTIONS_INDISPONÍVEL` apenas após evidência.

## 7. Guardrails permanentes, inalterados

Supabase/Postgres único entre os ambientes; migrações apenas aditivas/retrocompatíveis mediante autorização própria; sem pausar produção. Preservar `pg_cron` + `pg_net` do mecanismo de wake. Não reenviar jobs `unknown` sem conciliação. Não habilitar Shopee Vídeo antes de aprovação específica de Video Management. Não alegar testes reais de postagem/pagamento ou capacidade de produção sem evidência. Condição de SMTP/domínio próprio continua sujeita à verificação documental do `TASK.md`.

**Referências:** [AGENTS](../AGENTS.md), [RULES](RULES.md), [Guia Mestre](GUIA-MESTRE-IA.md), [CHANGELOG](../CHANGELOG.md), [release candidata](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/blob/release/3.3.0-20261105/docs/RELEASE-3.3.0-20261105.md) (ainda somente na branch do PR #303), [Vault TASK](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/docs/auto-orbital-ci-indisponivel-20261107/Projetos/ShopeeAutoVendas/TASK.md).
