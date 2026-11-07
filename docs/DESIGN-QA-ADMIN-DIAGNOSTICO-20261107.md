# Design QA — Diagnóstico ADMIN compacto (07/11/2026)

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
