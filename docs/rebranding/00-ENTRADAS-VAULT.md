# Entradas para o Vault - Auto Orbital

> Texto pronto para atualizacao futura do Vault GitHub `raffastudioproducoes-cloud/RaffaStudio-Vault`, pasta `Projetos/ShopeeAutoVendas`.
> O Vault nao esta clonado neste repositorio e nao foi acessado nesta tarefa. Estas entradas devem ser aplicadas depois por outro passo.

## 00-INDICE-Estado-Atual.md

```md
## Atualizacao 2026-10-13 - Rebranding aprovado: Auto Orbital

- Decisao de marca aprovada: o produto deixara de se chamar "Shopee Auto Vendas" e passara a se chamar **Auto Orbital**.
- Implementacao no produto: **pendente / not started**. O runtime, frontend, infra, OAuth, assets, metadados e identificadores tecnicos ainda nao foram convertidos.
- Tagline aprovada: **Seus posts a um clique.**
- Logo oficial: imagem aprovada pelo usuario na conversa (buraco negro/horizonte de eventos, anel luminoso, orbitas e cards de conteudo orbitando; wordmark Auto Orbital com `O` orbital em ciano/azul e `rbital` em gradiente azul->violeta). O arquivo ainda nao esta no repo.
- Documento canonico local: `docs/rebranding/34-Rebranding-Auto-Orbital-Plano-Mestre.md`.
- Regra: Auto Orbital e a marca do produto; Shopee permanece como integracao/fonte/ecossistema. Exemplo correto: "Auto Orbital integra-se a Shopee Open API".
```

## 04-Backlog.md

```md
## Rebranding Auto Orbital - planejamento aprovado, implementacao pendente

- [ ] Gate 0 Baseline: inventario visual e screenshots.
- [ ] Gate 1 Documentacao: sincronizar docs e Vault.
- [ ] Gate 2 Brand Tokens: criar tokens Auto Orbital.
- [ ] Gate 3 Foundations: atualizar fundos, superficies, foco, motion e semantica visual.
- [ ] Gate 4 Assets: inserir logo oficial, favicon, PWA/app icons e social preview.
- [ ] Gate 5 App Shell: login, navegacao, TopBar e rodape.
- [ ] Gate 6 Core Screens: dashboard, products, posts, lists.
- [ ] Gate 7 Supporting Screens: credentials, profiles, settings, notifications, modals.
- [ ] Gate 8 Metadata: title, description, manifest, theme colors, OpenGraph.
- [ ] Gate 9 Responsive QA: desktop/tablet/mobile.
- [ ] Gate 10 Accessibility: contraste AA, foco visivel, reduced motion, estados nao so por cor.
- [ ] Gate 11 Functional Tests: typecheck, lint, build, testes.
- [ ] Gate 12 Legacy Name Audit: busca por nome antigo, hardcoded colors, assets e compatibilidade.
- [ ] Gate 13 Final Approval: aprovacao explicita do usuario antes de promover.
```

## 02-Arquitetura.md

```md
## Nota arquitetural - Auto Orbital vs Shopee

Auto Orbital sera a marca do produto. Shopee deve continuar aparecendo quando for integracao tecnica ou dominio de negocio legitimo: Shopee Open API, Shopee Affiliate, credenciais Shopee, catalogo Shopee, produtos Shopee e variaveis/tabelas relacionadas a integracao.

Renomes de identificadores internos (`shopee_bot`, `shopee-bot`, `shopee_bot-main`, package names, service names Render, callbacks OAuth, Docker WORKDIR, env vars e cache PWA) exigem plano proprio de migracao e compatibilidade. Nao renomear junto com a troca visual sem aprovacao explicita.

Documento canonico local do plano: `docs/rebranding/34-Rebranding-Auto-Orbital-Plano-Mestre.md`.
```
