# Roadmap do MVP — Auto Orbital

> **Plano Estratégico e Técnico de Lançamento**  
> **Data:** 15 de outubro de 2026  
> **Branch de Documentação:** `docs/handoff-2026-10-15` (worktree `_tmp/wt-docs`)  
> **Fontes Consultadas:** Planos prévios em `_tmp/prep/` (`admin-panel.md`, `meta-texts.md`, `metrics-page.md`, `payments.md`, `scale-free-to-paid.md`), histórico em `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/TASK.md` e `docs/superpowers/plans/2026-10-13-escalabilidade-futura.md`.  
> **Diretriz:** Factualidade estrita — distinção explícita entre fatos verificados no repositório e hipóteses de evolução.

---

## 1. Visão Geral do MVP

O **Auto Orbital** (evolução do *Shopee Auto Vendas*) é um SaaS de automação que agenda e publica postagens para afiliados da Shopee nas principais redes sociais (Facebook, Instagram, Threads, TikTok e X/Twitter).

O objetivo do MVP é alcançar estabilidade operacional, conformidade rigorosa com as plataformas (aprovação do Meta App Review), transparência visual e base técnica sólida para monetização no Brasil, operando de forma enxuta na infraestrutura existente (Render + Supabase).

---

## 2. Pilares do Roadmap (Status, Dependências e Entregas)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FLUXO DE EVOLUÇÃO DO MVP                           │
├─────────────────┬───────────────────────────────────────────────────────────┤
│ FASE 1          │ • Estabilização Staging (Esqueleto + Splash + Segurança)  │
│ (Imediata)      │ • Submissão do Meta App Review (Vídeos PROD + Justif.)    │
│                 │ • Alinhamento Jurídico dos Termos e Privacidade           │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ FASE 2          │ • Ativação do Painel Administrativo (/admin isolado)      │
│ (Curto Prazo)   │ • Landing Page Pública de Apresentação (Rota /)           │
│                 │ • Painel de Métricas de Catálogo e Publicações            │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ FASE 3          │ • Camada Segura de Pagamentos no Brasil (Pix + Cartão)    │
│ (Monetização)   │ • Tabela de Planos (Free vs Pro) e Idempotência           │
│                 │ • Avaliação de Novas Redes e Afiliados (Amazon, ML)       │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ FASE 4          │ • Escala Horizontal (Fila Postgres FOR UPDATE SKIP LOCKED)│
│ (Infra Pro)     │ • Migração Render/Supabase Free -> Pago                   │
│                 │ • Workers Separados para o Scheduler                      │
└─────────────────┴───────────────────────────────────────────────────────────┘
```

---

### Pilar A: Página de Apresentação (Landing Page Pública `/`)

- **Objetivo:** Fornecer uma vitrine pública de conversão e explicação do produto na raiz do domínio (`/`), sem exigir autenticação prévia, apresentando a marca Auto Orbital, funcionalidades, recursos de IA, redes suportadas e chamada para cadastro.
- **Status Atual:** **Planejada (Pendente de Implementação)**.
- **Dependências:**
  - Desacoplamento da rota `/` no TanStack Router (`frontend/src/router.tsx`), diferenciando a home pública da dashboard interna (`/dashboard` ou `/panel`).
  - Biblioteca de componentes e tokens visuais (`frontend/src/components/ui/`, `frontend/src/styles/tokens/`).
  - Ativos de marca consolidados (`feat/brand-assets`).
- **Fato Verificado:** O frontend atual trata `/` como rota restrita com redirecionamento para login/painel quando desautenticado. Não existe layout de marketing ou landing page estática implementada em `frontend/src/pages/`.
- **Hipótese:** A introdução de uma landing page com prévias visuais em SVG/CSS aumentará a taxa de cadastros orgânicos sem impactar a performance do bundle principal.

---

### Pilar B: Shopee Vídeo e Expansão de Afiliações

- **Objetivo:** Explorar novos canais de monetização de afiliados, em especial postagens de vídeo na Shopee e programas concorrentes (Amazon Associados, Mercado Livre Afiliados).
- **Status Atual:**
  - **Shopee Vídeo:** **Bloqueado / Inviável** (conforme relatório oficial em `_tmp/reports/shopee-video-viabilidade.md`).
  - **Outras Afiliações:** **Planejamento Conceitual**.
- **Dependências:**
  - **Shopee Vídeo:** Disponibilização pública de endpoints de postagem de vídeo no feed social por parte da Shopee Brasil.
  - **Outras Afiliações:** Implementação de nova camada em `apis/` abstraindo busca de catálogo e conversão de deep links com tag de afiliado (Amazon Creator API / Mercado Livre Developers).
- **Fato Verificado:** A Open API de Afiliados da Shopee no Brasil (`media_space`) oferece unicamente endpoints para upload e conversão técnica de vídeo de catálogo de produtos. Não existe endpoint oficial para publicação no feed social do Shopee Vídeo, nem programa de afiliados aberto para publicação via API no Brasil. Nenhum adaptador `apis/shopee_video.py` foi criado.
- **Hipótese:** Programas de afiliados como Amazon e Mercado Livre possuem APIs estruturadas que permitirão reusar mais de 80% da lógica existente de produtos e listas.

---

### Pilar C: Políticas de Privacidade, Termos de Uso e FAQ

- **Objetivo:** Assegurar conformidade total com a LGPD e com os termos para desenvolvedores da Meta, eliminando discrepâncias entre o texto legal e o comportamento real do software.
- **Status Atual:** **Implementado, mas requer ajustes pontuais de redação** (`frontend/src/pages/legal/`).
- **Dependências:** Ajustes em `PrivacyPolicyPage.tsx` e `TermsPage.tsx` conforme o checklist em `_tmp/prep/meta-texts.md`.
- **Fato Verificado:**
  1. A política de privacidade ativa declara que a desautorização pelo usuário na rede social acarreta a exclusão imediata de todos os dados. No código real (`api/routers/meta_callbacks.py`), a desautorização zera os tokens OAuth e marca a credencial como inativa (`status=False`), preservando o registro para fins de auditoria. A exclusão de dados exige solicitação formal ou chamada ao endpoint `/meta/data-deletion`.
  2. O código armazena mídias de rascunho de forma efêmera no disco local do container em `web/media/<post_id>/` (ou `temporary_media_uploads`), enquanto a política mencionava URL assinada de 1 hora do Supabase Storage.
- **Hipótese:** O alinhamento transparente do texto (esclarecendo que a remoção do app revoga o acesso imediatamente e que a exclusão definitiva ocorre via `/meta/data-deletion` ou solicitação) mitiga o risco de rejeição no App Review da Meta.

---

### Pilar D: Página de Métricas por Rede Social e Afiliados

- **Objetivo:** Apresentar ao usuário métricas honestas, comparáveis e factuais sobre o desempenho de suas automações.
- **Status Atual:** **Planejada em `_tmp/prep/metrics-page.md`**.
- **Dependências:**
  - Criação da tela `MetricsPage.tsx` no frontend utilizando `PageSkeleton variant="table"`.
  - Endpoint de agregação na API (`GET /metrics`).
- **Fato Verificado:** Nenhuma das APIs oficiais consumidas no repositório fornece métricas de engajamento em tempo real (views, cliques, curtidas, compras ou conversão):
  - *Shopee Affiliate GraphQL:* Fornece apenas catálogo, preços e comissão estimada.
  - *Threads API / X API / TikTok API:* Wrappers implementados apenas com métodos de publicação e validação de token.
  - *Meta Graph API (Facebook/Instagram):* A Meta possui a API de Insights, mas o código atual não a consome.
  - **Métricas possíveis e reais:** Volume de postagens por rede, frequência de publicações por dia da semana, total de produtos vinculados e valor financeiro agregado do catálogo.
- **Hipótese:** Apresentar claramente o que a API entrega versus o que é impossível gerará credibilidade superior junto aos afiliados, diferenciando o produto de soluções que prometem métricas fictícias.

---

### Pilar E: Camada Segura de Pagamentos e Planos (Brasil)

- **Objetivo:** Habilitar monetização do SaaS no mercado brasileiro com suporte nativo a Pix (pagamento instantâneo) e Cartão de Crédito (assinaturas recorrentes), com verificação criptográfica de webhooks e proteção contra fraudes.
- **Status Atual:** **Planejado em `_tmp/prep/payments.md` (Código Inexistente no Momento)**.
- **Dependências:**
  - Definição do gateway (Mercado Pago ou Asaas como recomendados para o cenário brasileiro).
  - Migração de banco criando a coluna `plan_tier` na tabela `users` (atualmente presente apenas em `profiles`).
  - Criação do router `api/routers/payments.py` com webhook idempotente baseado em `payment_id`.
  - Salvaguarda PCI: NUNCA armazenar dados de cartão de crédito no banco de dados.
- **Fato Verificado:** O repositório atual opera em modelo 100% gratuito. Não há tabelas de cobrança, nem chaves de gateways em `.env-example`.
- **Hipótese:** A implementação baseada no Mercado Pago fornecerá o menor atrito de aprovação cadastral e suporte nativo ao Pix via QR Code e Copia-e-Cola no checkout.

---

### Pilar F: Painel Administrativo (`/admin`)

- **Objetivo:** Isolar o gerenciamento de usuários, logs de sistema e monitoramento de infraestrutura em uma rota exclusiva e restrita a administradores.
- **Status Atual:** **Implementado localmente em `feat/admin-panel` (commit `70805cd`), com refinamentos de segurança sintetizados em `_tmp/admin-refinement-local`**.
- **Dependências:**
  - Merge controlado para `staging`.
  - Salvaguarda da migração 051 (mover para aplicação manual para evitar execução automática contra o Supabase compartilhado).
  - Configuração de chave de API do Render restrita ao backend para métricas contínuas.
- **Fato Verificado:** A rota `/admin` está funcionalmente separada da navegação de usuários comuns; testes de role garantem HTTP 403 para usuários comuns; métricas reais de CPU, memória e requisições foram validadas com sucesso em servidor local (127.0.0.1:18765).
- **Hipótese:** Manter o monitoramento de recursos no painel reduzirá o tempo de diagnóstico de incidentes sem custo de ferramentas externas de APM.

---

### Pilar G: Escalabilidade Free -> Pago (Render + Supabase)

- **Objetivo:** Garantir a continuidade do serviço à medida que a base de usuários e o volume de posts agendados aumentarem, superando os limites estritos do tier gratuito.
- **Status Atual:**
  - **Fase 3 P0:** **Concluída e Mergeada em Staging (`b860aff`)**.
  - **Fases 4 a 7:** **Planejadas e Documentadas (`docs/superpowers/plans/2026-10-13-escalabilidade-futura.md`)**.
- **Dependências:**
  - Contratação de plano pago no Render (para habilitar múltiplos workers e evitar suspensão após 750h/mês).
  - Contratação de plano Pro no Supabase (quando o storage exceder 400 MB ou o pool de conexões exceder 15 simultâneas).
  - Implementação da fila `publish_jobs` com trava transacional no Postgres (`FOR UPDATE SKIP LOCKED`).
- **Fato Verificado:**
  - *Render Free:* Limita a 1 container único com 512 MB de RAM e 750h de uso mensal; suspende o container após inatividade (cold start de ~50s).
  - *Supabase Free:* Limita a 500 MB de banco, 1 GB de storage e ~20 conexões ativas no PostgreSQL.
  - *Concorrência:* O scheduler atual (`APScheduler`) roda in-process dentro do gunicorn do Flask (`workers=1`). Aumentar o número de workers hoje geraria postagens duplicadas nas redes sociais.
- **Hipótese:** A arquitetura de fila transacional no próprio Postgres permitirá escalar horizontalmente até 200 usuários ativos sem a necessidade de provisionar instâncias de Redis ou serviços externos de fila.

---

## 3. Matriz de Dependências e Cronograma Sugerido

| Marco | Entregas Principais | Depende de | Impacto no Usuário |
|---|---|---|---|
| **M1: Estabilização & Submissão Meta** | • Merge `feat/splash-orbital-v2` em staging<br>• Submissão dos 3 vídeos do App Review no portal Meta<br>• Ajuste dos textos legais (`PrivacyPolicyPage`) | Revisão do Rafa e credenciais da Meta | Permite que contas de terceiros conectem Facebook e Instagram em modo Live |
| **M2: Gestão & Marca** | • Merge `feat/admin-panel` (com migração manual)<br>• Publicação da Landing Page na rota pública `/`<br>• Correções restantes de segurança (`fix/security`) | M1 concluído e validação visual de layout | Separação profissional da administração e atração de novos usuários |
| **M3: Métricas & Transparência** | • Implementação de `MetricsPage.tsx`<br>• Agregador de volume e catálogo por rede | M1 e M2 | Fornece visibilidade operacional ao afiliado |
| **M4: Monetização** | • Camada de pagamentos (Mercado Pago / Pix)<br>• Tabela de planos e webhook idempotente | M2 e M3 | Permite cobrança de planos pagos e sustentabilidade financeira |
| **M5: Escala Pro** | • Fases 4 e 5 de Escalabilidade (Fila Postgres)<br>• Upgrade Render Pro + Supabase Pro<br>• Separação de worker de scheduler | Receita gerada no M4 | Elimina risco de cold starts, amplia conexões e garante alta disponibilidade |

---

## 4. Fatos Verificados vs Hipóteses (Resumo de Riscos)

| Área | Fato Verificado (Evidência no Código) | Hipótese (Necessita Validação / Decisão) |
|---|---|---|
| **Meta Review** | Os 3 vídeos em produção comprovam Login for Business e publicação/deleção real. O código NÃO usa `business_management`. | A exclusão da permissão `business_management` evitará a rejeição do revisor da Meta. |
| **Redes Sociais** | Shopee Vídeo não tem API pública de publicação para afiliados. | O feed do Shopee Vídeo permanecerá fechado para APIs externas no curto prazo. |
| **Infraestrutura** | 1 container no Render Free suporta a carga de teste atual. O banco Supabase é compartilhado entre staging e produção. | O tier gratuito suportará até ~10 usuários com posts diários antes de atingir limites de conexões. |
| **Segurança** | Tokens de acesso OAuth são cifrados com Fernet antes de persistir no banco. Replay de callbacks bloqueado com janela temporal. | A chave de criptografia de 32 bytes está segura e devidamente configurada em produção. |
