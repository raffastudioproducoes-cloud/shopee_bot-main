# Diagnóstico ADMIN compacto — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exibir IA e Shopee em cards recolhíveis lado a lado no desktop, e substituir os formulários de override por estado compacto com teste global auditável.

**Architecture:** Manter as operações administrativas existentes para salvar/ativar/remover chaves globais, ocultando apenas overrides manuais sociais na UI (sem apagar dados ou rotas). Criar uma ação de diagnóstico ADMIN isolada, que aciona os validadores existentes uma vez por plataforma configurada e grava eventos sanitizados em `request_logs` sob `force=True`, sem habilitar logging geral.

**Tech Stack:** FastAPI/Python, Supabase existente, React/TypeScript, TanStack Query, CSS tokens do projeto.

**Spec:** Pedido do Rafa de 07/11/2026 nesta conversa, screenshots de `/admin/credentials` staging.

## Global Constraints

- `main`/produção intocada até autorização; integrar apenas em `staging` após CI verde.
- `VERSION=3.4.0` permanece; melhoria compatível candidata MINOR `3.5.0`, `CHANGELOG.md` em Não lançado.
- Sem DDL/migrations, mudanças em `pg_cron`, `pg_net`, scheduler, publicações ou credenciais reais.
- Não registrar segredos, texto bruto de fornecedores ou IDs de clientes nos logs e na resposta.

## Review Focus

- ADMIN com redes desconectadas: nenhum teste externo nelas, estado honesto na UI.
- Ausência de chave global IA/Shopee: registrar não configurado, sem erro fatal no lote.
- Teste parcial com timeout/erro de rede: demais plataformas continuam e resultado não revela segredo.
- Limite de requisições: uma ação ADMIN conta uma tentativa, não N tentativas.
- Desktop/mobile e teclado: acordeões acessíveis e conteúdo sem estouro em viewport estreita.

---

### Task 1: Endpoint de verificação consolidada

**Files:** `api/routers/credentials.py`, `api/routers/platform_ai.py`, `api/routers/platform_shopee.py`, `api/routers/admin.py`; teste `tests/api/test_admin_credential_batch.py`.

**Interfaces:** `POST /admin/credentials/test-all` retorna `{tested: number, skipped: number, results: Record<string,{state,status_text,checked_at}>}`. Reutiliza validação/atualização de estado dos endpoints atuais, sem N rate limits. Gera `log_action` com ação e estado sanitizados.

- [x] Escrever testes de autorização, exclusão de desconectadas, sucesso/erro parcial, rate limit único e logs sanitizados; conferir falha inicial.
- [x] Extrair helpers de teste dos endpoints existentes e implementar agregador ADMIN.
- [x] Executar testes API focados e compilar módulos Python; API integral 1.271/1.271 PASS.

### Task 2: Interface ADMIN de diagnóstico compacto

**Files:** `frontend/src/pages/AdminCredentialsPage.tsx`, `frontend/src/components/credentials/AdminAiCredentialCard.tsx`, `frontend/src/components/credentials/AdminShopeeCredentialCard.tsx`, `frontend/src/api/credentials.ts`, `frontend/src/styles/admin.css`, ícone `frontend/public/brand-logos/gemini.svg`, testes `frontend/tests/*.test.mjs`.

**Interfaces:** dois cards globais em grid responsivo; cada card com logo, resumo, expansão independente, mantendo salvar/ativar/desconectar. Grade de status das redes com logo/nome/estado/última checagem. Um único botão `Testar todas as conexões` invoca a API acima e atualiza estados/resultado visual.

- [x] Ajustar/introduzir testes de estrutura, responsividade, ausência de overrides e acionamento único.
- [x] Implementar JSX/CSS respeitando design tokens, mantendo estados e falhas.
- [x] Executar testes Node (86/86 PASS) e `npm run build` PASS; QA visual autenticado após deploy staging.

### Task 3: Documentação, integração e homologação

**Files:** `docs/TASK.md`, `CHANGELOG.md`, `docs/ADMIN-DIAGNOSTICO-CONEXOES-20261107.md`, fontes das logos, workflow CI se necessário.

- [x] Documentar contrato, segurança, exceção auditada ao logging geral e limites de teste autenticado.
- [x] Reler documentação editada e reavaliar gatilhos de TASK.
- [x] Commit em branch isolada, PR #322 para staging, CI #1067 SUCCESS, merge staging `8345cc7`, Render `dep-dbnfq30473hc739jbs30` LIVE e health/readiness OK; não promover main.
- [x] QA visual desktop autenticado: ambos os acordeões, logos, salvamento global preservado e seis status compactos observados em staging LIVE.
- [ ] Homologação funcional externa do botão em uma conta ADMIN, com custos/cotas de fornecedores autorizados; confirmar logs reais após executar. QA visual de viewport mobile permanece manual.
