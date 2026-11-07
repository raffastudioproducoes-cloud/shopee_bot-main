# Design QA — Diagnóstico ADMIN compacto (07/11/2026)

> **QA autenticado da atualização de catálogo (07/11/2026):** [PR #324](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/324), CI #1071 SUCCESS, Render `dep-dbng4t7avr4c73adujfg` LIVE. Desktop real em `/admin/credentials`: dois painéis globais recolhíveis; seção **Lojas — 12 integrações planejadas** e seção **Redes sociais — 9 plataformas**, todas em ordem alfabética, com estados `Em breve` nos 15 placeholders. Os seis indicadores sociais existentes continuam exibindo estados reais. Detectado problema leve de contraste em três logos, corrigido na revisão visual posterior. O botão de teste não foi acionado com chaves reais. Evidência abaixo é do layout **anterior** ao catálogo expandido.

Escopo: `/admin/credentials` em `staging`, Render `dep-dbnfq30473hc739jbs30` LIVE, app commit `8345cc74c2ba31f58e70fd0a074ef77485aa5f2b`.

| Critério | Evidência | Resultado |
|---|---|---|
| IA e Shopee, alfabéticos e lado a lado no desktop | Browser autenticado: dois cards compactos com logos, títulos e badges | PASS |
| Cada painel recolhe e expande | Cliques no cabeçalho dos dois acordeões; formulários ocultos quando fechados, controles existentes preservados ao abrir | PASS |
| Status sociais compactos, logos, nomes e sem token/API inputs | Browser autenticado: Facebook, Instagram, Kwai, Threads, TikTok, X | PASS |
| Um único botão para teste do conjunto | Visível e habilitado após carregamento; nenhum botão individual de teste | PASS visual |
| Estados reais de redes | Exibidos a partir da consulta autenticada, com último teste quando existente; não inferir sucesso pelo cadastro | PASS visual |
| Mobile, cards globais empilhados | `@media (max-width: 1200px)` e `@media (max-width: 650px)` em CSS, build Vite PASS | PASS técnico; captura mobile pendente |
| Autorização e segurança de logs | 1.271 testes API PASS; evento `force=True` sem logging global e whitelist de rótulos | PASS automatizado |

**Não executado com credenciais reais:** o botão `Testar todas as conexões`, por acionar fornecedores e eventualmente consumir cota. A persistência dos logs foi verificada via teste automatizado, não por observação do lote real. Não alterar `main`, tokens, Supabase, cron ou `pg_net` sem nova autorização.

Contrato completo: [`ADMIN-DIAGNOSTICO-CONEXOES-20261107.md`](ADMIN-DIAGNOSTICO-CONEXOES-20261107.md). CI: [#1067](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42363907682).
