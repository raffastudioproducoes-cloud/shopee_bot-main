# Release Auto Orbital 3.4.0 — IA fornecida pela plataforma

**Data:** 07/11/2026  
**Classificação:** MINOR compatível de `3.3.0` para `3.4.0`.  
**Autorização:** Rafa determinou promover toda a mudança para `main` e produção.

## Alterações

1. `/credentials`: removido card de configuração de IA para USER e ADMIN, preservados cards sociais, ordenação e agrupamento.
2. `/admin/credentials`: administração exclusiva da IA — Gemini/OpenAI/Anthropic, segredo cifrado, seleção de modelo, status, salvar/trocar, ativar, testar e desconectar.
3. Geração de texto em Posts/Produtos usa exclusivamente credencial global e provedor ativo da plataforma; clientes não cadastram chave.
4. Migração 089 aditiva com configuração independente para `staging` e `production`, RLS de negação para `anon`/`authenticated`, serviço backend `service_role` e importação cifrada da chave ADMIN antiga. Tabela legada preservada para rollback.

## Evidências antes da promoção

- PR [#311](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/311), [CI #1043](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42351613224) SUCCESS nos 3 jobs; merge em staging `c352fb841ac45b56d86aefc3947c375a1c01cd8a`.
- PR [#312](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/312) documentação, CI #1045 SUCCESS, merge `a4f0aaa7e83d8358e3fc7d2282c987135e1685be`.
- Render staging `dep-dbndau5g1s2s73fegi0g` LIVE, endpoints `/health` e `/api/health/ready` responderam `{"status":"ok"}` após o último deploy documental.
- Migração 089 aplicada no Supabase compartilhado, registrada em `public.migrations`; RLS, privilégios e presença da configuração Gemini para ambos ambientes verificados sem leitura de segredos.
- Testes locais: API 1.258, scheduler 208 + 1 xfail, frontend 76, DB 6 e web/CSP 27; Vite/TypeScript e lint crítico aprovados.
- Exatamente dois `pg_cron` confirmados: `auto-orbital-wake-v1` a cada 2 min e `auto-orbital-uptime-sample-v1` a cada 12 min. Nenhuma alteração de cron/pg_net.

## Gate de promoção autorizado

**Concluído em 07/11/2026:** PR [#313](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/313) passou CI #1047 e foi mesclada na staging SHA `b5bcbc0760af579dc24cd50f9508202e21b92b8b`; Render `dep-dbndesfb9u1s73cinq4g` LIVE e saúde OK. PR de promoção [#314](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/314) passou [CI #1049](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42352814892) e [SemVer #4](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42352814886), merge normal `main` `4ca125faf72f58c7d5c7623fc7b2a8bbb215f1b0`. Render produção `dep-dbndgcnb9u1s73cip6mg` **LIVE** com `/health` e `/api/health/ready` OK, logs error vazios pós-deploy. Banco confirmou Gemini global em ambos ambientes, sem leitura de segredos; dois cron jobs preservados. `VERSION=3.4.0` em `staging`/`main`, diferenças de arquivos zero após promoção. Vault PR #75 integrou o estado técnico anterior à produção; fechamento documental final desta release deve ser espelhado.

**Checklist histórico utilizado antes da conclusão:**

1. PR de release 3.4.0 para `staging` com `VERSION`, `CHANGELOG` e documentação; aguardar CI e Render LIVE.
2. Comparar `staging` com `main`; PR de promoção para `main` com gate SemVer 3.3.0→3.4.0 e CI.
3. Merge e deploy em Render produção `srv-da6vrla6iojc7380a13g`; verificar SHA LIVE, `/health`, `/api/health/ready`, logs e dois crons.
4. Registrar evidências reais e atualizar Vault. **Não confundir gates HTTP com QA autenticado de ADMIN ou geração real com Gemini**, ainda não comprovados.

## Segurança e custo

- Nunca copiar valores de chave, cookies ou segredos para documentação/logs. Não enviar posts externos nem mexer em cobrança sem autorização própria.
- Google AI Pro não cobre automaticamente a Gemini API; o proprietário deve definir teto de gastos e acompanhar consumo antes de liberar uso amplo.
- Staging e produção compartilham schema, mas selecionam configurações separadas pela origem do deploy. Rollback do app para 3.3.0 continua possível sem apagar a migração aditiva 089.
