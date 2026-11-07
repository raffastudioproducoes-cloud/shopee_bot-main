# Credenciais compactas e plataformas futuras — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganizar `/credentials` em abas de lojas/redes com cartões compactos e logomarcas reais, preservando todas as integrações existentes.

**Architecture:** Criar manifesto tipado para integrações futuras e componente visual reutilizável de logomarcas. Atualizar os wrappers `CredPanel`, `CredHeader` e `CredentialTrailing`, mantendo cada cartão funcional e os grupos por status; adicionar explicação retrátil independente por card. Persistência e OAuth não mudam.

**Tech Stack:** React/TypeScript, TanStack Query, Zustand, CSS semântico existente, Node `--test`, Vite; imagens SVG/PNG locais.

**Spec:** `docs/CREDENCIAIS-COMPACTAS-LOJAS-REDES-20261107.md`.

## Global Constraints

- `main` e release `3.4.0` protegidas; feature apenas `staging` até aprovação explícita.
- Nenhuma integração fictícia para plataformas futuras; nenhuma migration ou novo cron.
- Source PT-BR, responsivo, teclado/ARIA, contraste suficiente, testes antes de commit.
- CSS CSP estático tem contrato de classes vivas; preservar seletores existentes ainda utilizados.

## Review Focus

- Usuário sem credencial: cartão pendente sem estado falso e ação correta.
- Usuário com credencial de teste vencido: grupo registrado não deve cair no pendente.
- Navegação das abas após retornar do OAuth: o serviço deve aparecer na aba Redes, ainda agrupado por status.
- Ajuda recolhida durante salvamento: não perder valor nem estado do formulário.
- Faixa móvel: logos, nomes extensos e pill não podem gerar overflow horizontal.

---

### Task 1: Catálogo e logos transparentes

**Files:**
- Create: `frontend/src/lib/credentialPlatforms.ts`, `frontend/src/components/credentials/BrandLogo.tsx`, `frontend/public/brand-logos/*`
- Test: `frontend/tests/credentials-platforms.test.mjs`

**Interfaces:** `FuturePlatform { id, title, category, description, logo }`, `FUTURE_PLATFORMS`; `BrandLogo({ name, ... })` lê asset local a partir do manifesto.

- [ ] Criar contrato de integridade/duplicação/ordenação das futuras plataformas e origem dos arquivos.
- [ ] Executar o teste e confirmar falha antes da implementação.
- [ ] Adicionar manifesto, logos transparentes de fontes públicas e renderização acessível.
- [ ] Confirmar teste e inspeção dos logos nas duas abas.
- [ ] Commit independente dos assets e do manifesto.

### Task 2: Card compacto, ajuda e abas

**Files:**
- Modify: `frontend/src/pages/CredentialsPage.tsx`, `frontend/src/index.css`, `frontend/src/styles/mobile.css`
- Test: `frontend/tests/credentials-compact-ui.test.mjs`, contratos existentes de credenciais e rascunhos.

**Interfaces:** `CredPanel`, `CredHeader`, `CredentialHelp` e grupos de `groupCredentialCards` preservados; categorias `stores/social` determinam filtragem.

- [ ] Escrever contratos para abas, status fechado, default recolhido, ajuda independente e ocultação de teste USER.
- [ ] Executar e observar falha inicial.
- [ ] Implementar abas e cabeçalhos compactos, incluindo ajuda retrátil nos cards funcionais/futuros.
- [ ] Verificar que Shopee salva ID e OAuth das redes permanece intacto; marcar futuro como indisponível.
- [ ] Rodar `node --test` das credenciais e `npm run build`.
- [ ] Commit do layout/contratos.

### Task 3: Validação, documentação e staging

**Files:**
- Modify: `docs/CREDENCIAIS-COMPACTAS-LOJAS-REDES-20261107.md`, `docs/TASK.md`, `CHANGELOG.md`, `AGENTS.md`.
- Test: seleções frontend de `.github/workflows/ci.yml`, web/CSP quando aplicável, `git diff --check`.

**Interfaces:** Sem novas APIs; documentação registra status real, PR, CI e SHA.

- [ ] Verificar responsividade e expansão no navegador; registrar `design-qa.md` (ou bloqueio justificável).
- [ ] Rodar todas as seleções de CI frontend e build, corrigir falhas.
- [ ] Atualizar CHANGELOG sob `Não lançado` e status de rollout na documentação.
- [ ] Commit, publicar branch via GitHub, abrir PR para `staging`.
- [ ] CI verde, merge **somente staging** e Render LIVE/health; registrar QA autenticado ainda não comprovado.
