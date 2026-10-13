# Auto Orbital - Plano Mestre de Rebranding

> Documento canonico local para planejar o rebranding de **Shopee Auto Vendas** para **AUTO ORBITAL**.
> O numero 31 ja existe no Vault como `31-Contrato-OAuth-e-Publicacao`; 32 e 33 tambem existem. Por isso este plano usa o numero **34**.
> Estado deste arquivo: planejamento e documentacao somente. Nenhuma implementacao de produto foi feita nesta tarefa.

## 1 Status da decisao

| Item | Status |
| --- | --- |
| Decisao de marca | **APROVADA** |
| Nova marca | **AUTO ORBITAL** |
| Tagline | **Seus posts a um clique.** |
| Implementacao no produto | **PENDENTE / NOT STARTED** |
| Estado atual | **Shopee Auto Vendas** ainda aparece no runtime, codigo, frontend, documentacao, infra, assets e metadados. |
| Estado alvo | **Auto Orbital** aparece como marca do produto apos execucao futura deste plano; Shopee permanece como integracao/fonte/ecossistema. |

## 2 O que muda

- A marca do produto passa a ser **AUTO ORBITAL**.
- A comunicacao de produto passa a enfatizar automacao continua, orbita, distribuicao, centralizacao, escala, fluxo e publicacao com baixo atrito.
- A identidade visual futura usa direcao **Cosmic Tech + Dark Premium + Event Horizon + Orbital Motion + SaaS profissional**.
- A paleta aprovada substitui gradualmente a paleta atual por tokens de marca, sem quebrar layout, hierarquia, acessibilidade ou componentes existentes.
- O logo oficial futuro sera a imagem aprovada pelo usuario: buraco negro/horizonte de eventos, centro escuro, anel luminoso, orbitas e cards de foto/video/texto orbitando; wordmark Auto Orbital com o `O` como anel orbital em ciano/azul e `rbital` em gradiente azul para violeta.

## 3 O que NAO muda ainda

- Nenhum arquivo de runtime foi alterado nesta tarefa.
- Nenhum `.ts`, `.tsx`, `.js`, `.jsx`, `.py`, `.css`, `.json`, `.yml`, `.yaml`, `Dockerfile`, asset, token, componente, banco, env, OAuth, Render, GitHub, favicon, manifest ou package metadata foi editado.
- Nenhuma pasta, repositorio, servico, branch, callback, webhook, dominio ou variavel foi renomeada.
- Nenhum deploy, commit, push, PR ou migracao foi feito.
- Referencias tecnicas legitimas a Shopee continuam validas: Shopee API, Shopee Open API, Shopee Affiliate, credenciais Shopee, catalogo Shopee, produto Shopee, integracao Shopee.

## 4 Nova marca

**AUTO ORBITAL** e a marca do produto.

Nome recomendado em texto corrido: **Auto Orbital**. Em contextos de identidade, splash, logo, material comercial e headings de marca, pode usar **AUTO ORBITAL**.

Regra de produto: Auto Orbital e o produto; Shopee e integracao/fonte/ecossistema. Exemplo correto: **Auto Orbital integra-se a Shopee Open API**.

## 5 Tagline

**Seus posts a um clique.**

Uso futuro recomendado: login, landing/marketing, OpenGraph, social preview, logo full quando houver espaco, materiais institucionais e docs de apresentacao. Evitar repetir a tagline em telas operacionais densas onde o usuario ja esta trabalhando.

## 6 Conceito

```text
conteudo -> Auto Orbital -> automacao -> organizacao -> agendamento -> distribuicao
```

Ideias associadas: automacao continua, publicacao, distribuicao, orbita, fluxo, escala, centralizacao e gravidade. O produto atua como centro operacional que atrai conteudo, organiza cadencia e distribui posts nos canais conectados.

## 7 Logo

Logo oficial aprovado: imagem anexada na conversa pelo usuario, ainda **nao existente no repositorio**. Registrar como ativo visual oficial a ser usado na implementacao futura. Nao copiar, gerar, redesenhar ou substituir nesta etapa.

| Variacao | Uso futuro | Observacao |
| --- | --- | --- |
| LOGO FULL | Simbolo + Auto Orbital + tagline | Login, marketing, docs, OpenGraph quando houver espaco. |
| WORDMARK | Auto Orbital | Navegacao, TopBar, rodape, headers compactos. |
| SYMBOL | Buraco negro/anel orbital | Favicon, PWA/app icon, loading, avatar de app, rail compacto. |
| MONOCHROME | Uso restrito | So se necessario para fundos complexos, impressao, email ou integracoes que nao aceitem gradiente. |

Caminhos atuais identificados apenas como informacao: `frontend/index.html` referencia `/favicon.svg` e `/manifest.webmanifest`; `web/static/manifest.json` define `name`, `short_name`, cores PWA e icones; `web/static/icons/icon-192.png` e `web/static/icons/icon-512.png` existem; `web/static/sw.js` usa cache `shopee-autovendas-static-v1`; `frontend/public/videos/login-bg.mp4` existe e e usado no login.

## 8 Paleta

| Nome | Hex | Papel futuro |
| --- | --- | --- |
| Event Horizon | `#010719` | Fundo profundo, hero, areas de marca. |
| Deep Orbit Navy | `#091959` | Base de superficies escuras e navegacao. |
| Deep Blue | `#102B9B` | Profundidade, graficos, estados selecionados controlados. |
| Electric Blue | `#1A5BE1` | Acao, links importantes, destaque funcional. |
| Orbit Blue | `#279CF5` | Marca, highlights, dados principais. |
| Electric Cyan | `#1FD3FD` | Ponto focal, foco, assinatura orbital. |
| Ice Blue | `#5D99F8` | Informacao, linhas auxiliares, graficos. |
| Indigo | `#6160E8` | Transicao de marca, selecao especial. |
| Orbital Violet | `#936CF2` | Fechamento do gradiente, acentos premium. |
| Soft Lilac | `#D4ABE9` | Apoio suave, detalhes e estados de baixa frequencia. |
| Horizon Warm Light | `#FAD2AD` | Highlights pontuais da luz quente do horizonte; nunca cor principal. |
| Texto principal | `#EEEAF2` | Texto principal no tema escuro. |

## 9 Grafites

| Token futuro | Hex | Uso |
| --- | --- | --- |
| Graphite 950 | `#080C16` | Fundo de app/shell quando nao for hero. |
| Graphite 900 | `#0D1320` | Superficies principais. |
| Graphite 850 | `#121927` | Paineis e cards densos. |
| Graphite 800 | `#192130` | Cards, inputs, listas. |
| Graphite 700 | `#222B3A` | Bordas preenchidas, hover, areas elevadas. |

## 10 Gradiente

Assinatura orbital principal:

```css
linear-gradient(90deg, #1FD3FD 0%, #279CF5 30%, #6160E8 65%, #936CF2 100%)
```

Uso restrito: identidade, hero, CTA principal quando apropriado, estado selecionado especial, graficos principais, highlights, marketing e motion. Nunca usar indiscriminadamente.

## 11 Tipografia

Fonte ativa verificada em `frontend/src/styles/tokens/fonts.css`: **Mona Sans**, com pesos variaveis `200 900`, servida via CDN Fontsource/jsDelivr, com fallback `SF Pro Display`, `-apple-system`, `Segoe UI`, `system-ui`, `sans-serif`.

Recomendacao: **preservar Mona Sans**. Ela ja cobre UI operacional, display, numeros e labels por tokens.

| Role atual | Uso | Destino futuro |
| --- | --- | --- |
| `--font-sans` | UI geral | Preservar. |
| `--font-display` | Headings/heros | Preservar; aplicar a Auto Orbital sem nova fonte. |
| `--font-numeric` | Metricas e valores | Preservar para tabelas, dashboards e stats. |
| `--text-role-hero` | Titulos de pagina/login | Preservar escala; ajustar cor, nao estrutura. |
| `--text-role-title` | Cards/paineis | Preservar. |
| `--text-role-body` | Texto padrao | Preservar. |
| `--text-role-label` | Labels uppercase | Preservar; revisar tracking so se a nova marca exigir. |

Nao introduzir fonte nova sem justificativa visual e tecnica, porque isso aumentaria risco de performance, inconsistencia e regressao.

## 12 Motion

Motion atual verificado: `frontend/src/styles/tokens/motion.css` define duracoes, easing e transicoes; `frontend/src/index.css` respeita `prefers-reduced-motion` na gaveta mobile; `LoginPage.tsx` consulta `prefers-reduced-motion` e nao toca o video de fundo quando o usuario prefere menos movimento; componentes usam transicoes discretas de hover, press, brilho, shadow e transform.

Linguagem orbital futura: glow discreto em foco/selecionado, progresso orbital para loading/publicacao/sincronizacao, highlights em arco, movimentos circulares sutis quando comunicarem estado, logo reveal controlado, micro-parallax so em hero/marketing, particulas somente em superficies de marca. Nao animar tudo. Respeitar `prefers-reduced-motion` e performance.

## 13 Design System atual

Fonte de verdade lida: `frontend/src/styles/tokens/*`, `frontend/src/index.css`, `frontend/src/components/ui/*`, `frontend/src/pages/*`, `frontend/index.html`, `web/static/manifest.json`, `web/static/sw.js`, docs canonicos e planos em `docs/superpowers/plans`.

Resumo atual: tema escuro unico; fundo global por `--bg-app-gradient`; superficies por `Panel`; navegacao por `SideRail`, `TopBar`, `NotificationsBell`, `ActiveProfileChip`; componentes base `Button`, `IconButton`, `TextInput`, `Textarea`, `Select`, `Modal`, `Badge`, `StatusBadge`, `SegmentedToggle`, `SearchField`, `Sparkline`, `TimelineListCard`, `StatCard`; icones em Lucide React; layout responsivo com rail fixo no desktop e drawer no mobile; rodape comum em `AppFooter`.

| Token atual | Funcao | Valor atual | Destino futuro | Observacao |
| --- | --- | --- | --- | --- |
| `--bg-app` | Fundo do app | `#1E2A38` | `Graphite 950` / `Event Horizon` | Planejar sem troca 1:1. |
| `--bg-app-gradient` | Fundo global | `linear-gradient(150deg,#26364A,#1E2A38,#182430)` | Gradiente escuro orbital discreto | Manter legibilidade antes de ornamentacao. |
| `--bg-rail` | SideRail | `#28364A` | `Deep Orbit Navy` / `Graphite 900` | Preservar largura e responsividade. |
| `--surface-card` | Cards | `#2B3949` | `Graphite 850` | Evitar preto puro. |
| `--surface-elevated` | Superficie elevada | `#35465B` | `Graphite 800/700` | Recalibrar contraste. |
| `--panel-glass` | Painel glass | gradiente steel/navy | Glass orbital controlado | Pode receber luz ciano/violeta sutil. |
| `--text-body` | Texto principal | `rgba(255,255,255,.88)` | `#EEEAF2` | Verificar AA em superficies novas. |
| `--accent` | Accent | `#81BDFA` | `Orbit Blue` / `Electric Cyan` | Substituir por token semantico. |
| `--focus-ring` | Foco | `rgba(129,189,250,.55)` | `Electric Cyan` com alpha | Foco visivel obrigatorio. |
| `--positive` | Sucesso | `#82DBA3` | Manter semantico | Nao trocar sucesso por azul. |
| `--negative` | Erro | `#F1948A` | Manter semantico | Nao usar gradiente em erro. |
| `--amber-300` | Alerta | `#F3C97D` | Pode alinhar a `Horizon Warm Light` | Uso pontual. |
| `--r-md` | Radius botoes/cards | `12px` | Preservar | Continuidade do sistema. |
| `--shadow-panel` | Elevacao | sombras pretas suaves | Preservar logica | Ajustar so se superficies mudarem. |
| `--dur-fast` | Motion | `140ms` | Preservar | Base para microinteracoes. |
| `--font-sans` | Fonte | Mona Sans | Preservar | Fonte ativa confirmada. |

Contagem de hex hardcoded no frontend: fora de `frontend/src/styles/tokens/*`, **7 ocorrencias** (`frontend/src/index.css` 3, `IconButton.tsx` 1, `Button.tsx` 1, `MediaTray.tsx` 1, `HelpPage.tsx` 1). Dentro de `colors.css`, **41 ocorrencias**, esperadas por serem tokens.

## 14 Principios de continuidade

- Evolucao de identidade, nao redesign funcional.
- Preservar arquitetura de componentes, grids, spacing, radius, estados, elevacao, acessibilidade, responsividade, UX e estrutura de paginas.
- Trocar tokens e fundacoes antes de telas.
- Nao alterar regras de negocio, OAuth, scheduler, banco ou integracoes durante o rebranding visual.
- Nao usar o gradiente orbital como solucao universal.
- Evitar cyberpunk exagerado, game UI, neon em tudo, espacial caricato, painel generico roxo ou template de IA.
- Priorizar SaaS premium, sofisticado, legivel, preciso, confiavel, profundo e controlado.

## 15 Auto Orbital vs Shopee

| Contexto | Tratamento futuro |
| --- | --- |
| Nome do produto | Auto Orbital |
| Marca em UI, login, footer, metadata, PWA | Auto Orbital |
| Integracao de catalogo/produtos | Shopee Open API / Shopee Affiliate |
| Credenciais da loja/fonte | Credencial Shopee |
| Modelos, tabelas, modulos tecnicos existentes | Caso a caso, com compatibilidade |
| Documentacao historica | Manter historico datado, adicionando nota de contexto quando util |

Exemplo correto: **Auto Orbital integra-se a Shopee Open API para buscar produtos e preparar posts.**

## 16 Inventario do nome antigo

Busca global somente leitura com `rg`, excluindo `.claude`, `.agents`, `agents`, `.git`, `.venv`, `.tmp`, `__pycache__` e binarios comuns:

| Padrao buscado | Ocorrencias |
| --- | ---: |
| `Shopee Auto Vendas` | 24 |
| `ShopeeAutoVendas` | 53 |
| `Shopee AutoVendas` | 0 |
| `shopee_bot` | 292 |
| `shopee-bot` | 29 |
| `shopee_bot-main` | 12 |
| `Shopee` total, incluindo integracoes legitimas | 371 |

Distribuicao por superficie: UI/branding visivel 19; documentacao 70; metadados 6; codigo interno 191; infra/deploy 15; historico/design legado 23; testes 86.

## 17 Matriz de impacto

| Categoria | Quantidade aproximada por `rg` | Risco | Acao futura recomendada | Exige migracao? | Exige compatibilidade? |
| --- | ---: | --- | --- | --- | --- |
| A Branding visivel | 19 | Medio | Renomear textos visiveis, login, legal, help e shell. | Nao | Sim. |
| B Documentacao | 70 | Baixo | Atualizar docs vivos e preservar historico datado. | Nao | Sim. |
| C UI | 19 | Medio | Trocar marca nas telas apos tokens/foundation. | Nao | Sim. |
| D Metadados | 6 | Alto | Planejar `package`, title, description, PWA metadata sem quebrar build. | Possivel | Sim. |
| E Codigo interno | 191 | Alto | Manter temporariamente; renomear so com plano tecnico. | Sim | Sim. |
| F Integracao Shopee legitima | 371 mencoes totais a `Shopee` | Alto se renomear errado | Manter Shopee quando for API, Affiliate, produto, catalogo, credencial e integracao. | Nao | Sim. |
| G Banco | Indireto, tabelas `shopee_credentials` etc. | Alto | Manter por padrao; renomear so com migracao formal. | Sim | Sim. |
| H Infra | 15 com infra/deploy | Alto | Avaliar Render, Docker, URLs, cache PWA, service names separadamente. | Possivel | Sim. |
| I OAuth/callback | Varias referencias em docs/testes/env | Critico | Nao alterar ate cadastrar callbacks novos e manter antigos. | Sim | Sim. |
| J Deploy | Incluido em infra | Alto | Planejar staging, producao, health checks, rollback por fase. | Possivel | Sim. |
| K Repo/Git | `shopee_bot-main` 12 | Alto | So renomear repo para `auto-orbital` com aprovacao explicita. | Sim | Sim. |
| L Historico | 23 | Baixo | Manter historico; adicionar nota de marca futura. | Nao | Sim. |
| M Compatibilidade | Transversal | Alto | Aliases, redirects e nomes tecnicos antigos enquanto necessario. | Sim | Sim. |
| N Testes | 86 | Medio | Atualizar asserts somente quando runtime mudar. | Nao | Sim. |
| O Assets | Icones atuais e video de login | Medio | Substituir por assets oficiais depois de preparados. | Nao | Sim, cache/favicons/PWA. |

## 18 Mapa visual

| Item | Estado atual | Mudanca futura | Risco | Dependencias | Criterio de aceite |
| --- | --- | --- | --- | --- | --- |
| App background | `--bg-app-gradient` steel/navy | Event Horizon + grafites | Contraste | Tokens | AA preservado. |
| Navigation | `SideRail`, brand `SV` | Simbolo/wordmark Auto Orbital | Quebra mobile | Assets + shell | Rail desktop/mobile ok. |
| SideRail | `--bg-rail`, labels uppercase | Deep Orbit Navy/grafite | Legibilidade | Tokens | Estado ativo claro. |
| TopBar | Busca, bell, perfil, logout | Highlights orbitais sutis | Poluicao visual | Tokens | Sem mudanca funcional. |
| Panels | `Panel` glass/dark | Glass orbital controlado | Neon excessivo | Tokens/elevation | Texto legivel. |
| Cards | `TimelineListCard`, `StatCard`, `ProfileCard` | Grafites + acentos | Densidade | Foundation | Layout nao muda. |
| Buttons | Variantes atuais | Primary alinhado a marca | Semantica de estados | Button tokens | Foco/disabled/loading ok. |
| Inputs | `TextInput`, `Select`, `Textarea` | Superficie graphite | Autofill/select | Tokens | Dark native ok. |
| Modals | `Modal` dark + scrim | Dark premium | Contraste | Panel | Formularios legiveis. |
| Dropdowns | Select nativo dark | Graphite + focus cyan | Browser native | Tokens | Opcoes legiveis. |
| Tables | Cards/list rows | Bordas e highlights orbitais | Scanning pior | Components | Leitura rapida preservada. |
| Status | `StatusBadge`, `ConnectionLight` | Semanticos preservados | Cor de marca confundindo estado | Semantica | Estado nao depende so de cor. |
| Charts | `Sparkline` | Linhas Orbit/Ice/Cyan | Excesso de gradiente | Charts tokens | Dados claros. |
| Empty states | Texto + CTA | Simbolo/linguagem Auto Orbital discreta | Marketing demais | Copy | CTA claro. |
| Notifications | `Toaster`, `NotificationsBell` | Cores semanticas preservadas | Alertas parecerem branding | Tokens | `role`/aria mantidos. |
| Login | Video + titulo Shopee Auto Vendas | Logo/tagline/visual oficial | Primeiro impacto | Logo + tokens | Sem motion se reduced. |
| Dashboard | Stats e visao geral | Acentos orbitais em metricas | Distracao | Tokens | Metricas escaneaveis. |
| Products | Catalogo Shopee | Copy: Auto Orbital + integracao Shopee | Renomear Shopee errado | Copy | Integracao Shopee clara. |
| Posts | Compositor multi-rede | Linguagem de orbita/distribuicao | Quebra fluxo | Copy + status | Criacao continua igual. |
| Lists | Listas de produtos | Ajuste visual | Baixo | Tokens | CRUD intacto. |
| Credentials | Cards por rede | Marca Auto Orbital; Shopee como credencial | OAuth copy | Legal/OAuth | Consentimento correto. |
| Profiles | Perfis de uso | Acentos premium | Baixo | Tokens | Avatares/actions ok. |
| Settings | Conta/senha | Ajuste visual minimo | Baixo | Tokens | Seguranca intacta. |
| Marketing surfaces | README, OG, hero futuro | Logo full + tagline | Assets/cache | Logo | Marca consistente. |

## 19 Mapa tecnico

| Nivel | Escopo | Direcao |
| --- | --- | --- |
| 1 Branding | Textos visiveis, titulos, login, footer, legal | Renomear futuramente para Auto Orbital. |
| 2 Documentacao | Docs vivos | Atualizar com nota de estado atual vs alvo. |
| 3 Frontend visivel | Headers, navigation, metadata, manifest, favicon | Renomear apos tokens e assets. |
| 4 Identificadores internos | Imports, pacote, slugs, package names | Caso a caso; nao fazer junto com visual. |
| 5 Infra separada | Render, GitHub, Supabase, OAuth URLs, dominio | So com aprovacao explicita e plano de compatibilidade. |

| Identificador | Classificacao | Observacao |
| --- | --- | --- |
| `shopee_bot` | MANTER TEMPORARIAMENTE / EXIGE MIGRACAO / EXIGE COMPATIBILIDADE | Import Python e WORKDIR Docker dependem disso. |
| `shopee-bot` | MANTER TEMPORARIAMENTE / EXIGE DECISAO DO USUARIO | Servicos Render, URLs e cache. |
| `shopee_bot-main` | EXIGE DECISAO DO USUARIO | Slug de repo atual; alvo desejado futuro: `auto-orbital`. |
| `ShopeeAutoVendas` | RENOMEAR FUTURAMENTE quando visivel | PWA, historico, legal, docs. |
| Slugs/URLs atuais | MANTER TEMPORARIAMENTE | OAuth e callbacks podem depender. |
| Package names | EXIGE MIGRACAO | Alterar package metadata pode afetar lockfiles/build. |
| Pacotes Python/imports | MANTER TEMPORARIAMENTE | Alto risco de quebra. |
| Env vars `SHOPEE_*` | MANTER DEFINITIVAMENTE quando integracao Shopee | Sao variaveis de integracao, nao marca do produto. |
| Service names Render | EXIGE DECISAO DO USUARIO | Renomear pode afetar URLs, callbacks, monitoramento. |

## 20 Infraestrutura afetada

| Area | Dependencia de string antiga | Acao futura |
| --- | --- | --- |
| GitHub repo | `shopee_bot-main` | Decidir se renomeia para `auto-orbital`; nao executar sem aprovacao. |
| Branches/CI | Docs citam servicos e repo | Atualizar docs apos mudanca real. |
| Render producao | `shopee-bot-fj0w.onrender.com`, servico `shopee-bot` | Manter ate dominio/callbacks novos. |
| Render staging | `shopee-bot-staging.onrender.com` | Manter para OAuth/staging. |
| Supabase | Tabelas e credenciais Shopee | Manter nomes tecnicos se forem integracao. |
| OAuth redirects | URLs `shopee-bot-*` | Critico: cadastrar novos antes de trocar. |
| Webhooks/callbacks | Dependem de dominio | Compatibilidade obrigatoria. |
| Env vars | `SHOPEE_PG_*`, callbacks | Nao renomear sem migracao. |
| Docker | `WORKDIR /shopee_bot` | Manter temporariamente. |
| Package metadata | `shopee_bot-main` | Planejar em fase interna. |
| PWA metadata | `ShopeeAutoVendas`, cache antigo | Atualizar junto com assets e cache versionado. |

## 21 Plano de implementacao

Ordem obrigatoria:

```text
DECISAO -> TOKENS -> FOUNDATION -> ASSETS -> APP SHELL -> SCREENS -> TEXTOS -> QA -> AUDITORIA
```

Telas nunca antes da fundacao.

## 22 Fases

| Fase | Nome | Conteudo | Saida |
| --- | --- | --- | --- |
| A | Baseline | Screenshots, inventario, branch dedicada | Estado comparavel. |
| B | Brand Tokens | Tokens Auto Orbital | Paleta controlada. |
| C | Foundation | Background, surfaces, focus, typography, motion | Base visual pronta. |
| D | Brand Assets | Logo, favicon, PWA icons, OG | Assets oficiais versionados. |
| E | App Shell | Login, SideRail, TopBar, Footer | Marca aparece sem alterar fluxo. |
| F | Core Screens | Dashboard, Products, Posts, Lists | Telas principais coerentes. |
| G | Support Screens | Credentials, Profiles, Settings, Notifications, Modals | Apoio consistente. |
| H | Brand Text | Copy visivel e legal | Shopee como integracao. |
| I | Internal Renaming | So aprovados | Compatibilidade garantida. |
| J | QA Visual | Desktop/tablet/mobile/a11y | Evidencias visuais. |
| K | Testes | typecheck/lint/build/tests | Regressao funcional coberta. |
| L | Auditoria Final | Nome antigo, hardcoded colors, assets, metadata | Aprovacao final. |

## 23 Gates

| Gate | Entrada | Tarefas | Criterios | Evidencias | Rollback | Condicao de pass |
| --- | --- | --- | --- | --- | --- | --- |
| 0 Baseline | Repo limpo | Inventario e screenshots | Nada alterado | `git status`, screenshots | Descartar branch | Baseline arquivado. |
| 1 Documentacao | Marca aprovada | Docs e plano | Estado atual/alvo claros | Este plano | Reverter docs | Sem afirmar implementacao feita. |
| 2 Brand Tokens | Paleta aprovada | Tokens CSS | AA preliminar | Diff tokens | Reverter tokens | Tokens centralizados. |
| 3 Foundations | Tokens | Fundo/surface/focus/motion | Layout estavel | Screenshots | Reverter foundation | Componentes base ok. |
| 4 Assets | Logo oficial | Favicons/PWA/OG/logo | Assets carregam | Arquivos + preview | Voltar assets antigos | Logo oficial presente. |
| 5 App Shell | Foundation+assets | Login/nav/topbar/footer | Responsivo | Desktop/mobile | Reverter shell | Fluxo intacto. |
| 6 Core Screens | Shell | Dashboard/products/posts/lists | Sem regressao | Screens/testes | Reverter grupo | Core aprovado. |
| 7 Supporting Screens | Core | Credentials/profiles/settings/modals | OAuth copy correta | Screens/testes | Reverter grupo | Apoio aprovado. |
| 8 Metadata | Assets | Title/manifest/theme/OG | PWA ok | Lighthouse/manual | Reverter metadata | Sem cache antigo. |
| 9 Responsive QA | Build | Desktop/tablet/mobile | Sem overlap | Screens | Reverter ultimo grupo | Layout ok. |
| 10 Accessibility | QA visual | Foco/reduced motion/contraste | AA e estados claros | Checklist | Reverter tokens/estado | A11y ok. |
| 11 Functional Tests | Codigo pronto | typecheck/lint/build/tests | Verde | Logs locais/CI | Reverter fase | Funcional ok. |
| 12 Legacy Name Audit | Tudo pronto | `rg` nome antigo | So legado legitimo | Relatorio `rg` | Corrigir/reverter | Sem marca antiga visivel indevida. |
| 13 Final Approval | Evidencias | Revisao do usuario | Aprovacao explicita | Checklist final | Nao promover | Aprovado pelo usuario. |

## 24 Criterios de aceite

- Branding: Auto Orbital aparece nas superficies visiveis aprovadas; Shopee permanece como integracao.
- Paleta: contraste AA para texto normal onde aplicavel; foco visivel; warm light so pontual.
- Design System: tokens centralizados; sem espalhar hex; gradiente usado com restricao.
- Responsividade: desktop, tablet e mobile sem overlap, sem texto cortado em botoes/cards.
- Acessibilidade: `prefers-reduced-motion`, foco visivel, roles/aria preservados, estados nao dependem so de cor.
- Funcional: build, typecheck, lint e testes verdes.
- OAuth: callbacks e consentimento nao quebrados.
- Scheduler: publicacao/agendamento intactos.
- Integracao Shopee: catalogo, credenciais e APIs mantem nomenclatura tecnica quando legitima.

## 25 Riscos

Strings espalhadas; identificadores internos; OAuth callbacks; URLs externas; service names; cache PWA; favicon; manifest; screenshots antigas; doc historica; contraste; excesso de neon; uso excessivo do gradiente; alteracao acidental de cores semanticas; hardcoded colors; mobile/desktop; branding antigo em email/mensagem; regressoes visuais; breaking changes por renome tecnico.

## 26 Rollback

Baseline visual, branch dedicada, commits pequenos, tokens primeiro, assets depois, telas por grupos, testes entre fases, rollback por fase e nada destrutivo irreversivel. Manter URLs/callbacks antigos ate os novos estarem cadastrados e validados.

## 27 Pendencias

- Confirmar se o repo GitHub sera renomeado para `auto-orbital`.
- Confirmar se a pasta local sera renomeada.
- Confirmar se a pasta do Vault sera renomeada.
- Confirmar se identificadores Python/imports serao migrados ou mantidos.
- Confirmar se servicos Render serao renomeados.
- Confirmar dominio publico futuro.
- Preparar favicon definitivo a partir do logo oficial.
- Preparar versao horizontal e monocromatica da logo se necessarias.
- Definir quais plataformas aparecem em marketing.

## 28 Decisoes que exigem aprovacao do usuario

1. Renomear ou manter o repositorio GitHub.
2. Renomear ou manter a pasta local.
3. Renomear ou manter a pasta do Vault.
4. Migrar ou manter `shopee_bot` como pacote tecnico.
5. Renomear ou manter servicos Render.
6. Criar dominio Auto Orbital e quando trocar callbacks.
7. Aprovar favicon/app icon derivados do logo oficial.
8. Aprovar versao horizontal/monocromatica da logo.
9. Aprovar plataformas citadas em marketing.

## 29 Checklist futuro

- [ ] Criar branch dedicada de implementacao.
- [ ] Capturar baseline visual.
- [ ] Implementar tokens Auto Orbital.
- [ ] Atualizar foundation visual.
- [ ] Adicionar logo oficial e variacoes aprovadas.
- [ ] Atualizar login, shell, footer e metadata.
- [ ] Atualizar telas core.
- [ ] Atualizar telas de apoio.
- [ ] Atualizar copy visivel.
- [ ] Validar OAuth/callbacks.
- [ ] Rodar typecheck/lint/build/tests.
- [ ] Rodar auditoria `rg` para nomes antigos.
- [ ] Rodar auditoria de hex hardcoded.
- [ ] Validar desktop/tablet/mobile.
- [ ] Validar acessibilidade.
- [ ] Obter aprovacao final do usuario.

## 30 Estado final desta tarefa

Tarefa concluida como **PLANEJAMENTO + DOCUMENTACAO SOMENTE**.

Estado atual documentado: Shopee Auto Vendas ainda aparece no runtime/codigo/infra/frontend.

Estado alvo documentado: Auto Orbital sera a marca futura apos execucao aprovada do plano.

Implementacao no produto: **NOT STARTED**.

Frontend alterado: **nao**.

Backend alterado: **nao**.

Infra alterada: **nao**.

Assets alterados: **nao**.

Deploy, commit, push, PR: **nao**.
