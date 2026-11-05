> **05/11/2026 — cota compacta em Listas (somente staging):** a página `/lists` deixa de mostrar `PlanSummary` no conteúdo. Reutiliza a barra compacta de cota (`ResourceQuotaBar`, recurso `lists`) com rótulo “Cota de listas”, quantidade consumida e limite, ou “sem cota comercial” no caso administrativo. Não replica a etiqueta de plano já presente no cabeçalho nem exibe avisos/explicação de planos. Free/Pro exibem CTA “Melhorar plano” para `/settings#planos`; Premium/administrador não. Bloqueio de criar ao atingir limite permanece ligado a `resourceAtLimit`; sem mudança de API, banco, cron ou regra de autorização. PATCH absorvido na candidata 3.3.0, `VERSION` inalterada.

> **05/11/2026 — pesquisa de Produtos contextual (somente staging):** TopBar mantém o campo único de busca em `Meus Produtos` e oculta apenas durante `Pesquisa Avançada`, pois esta já tem seu próprio formulário de catálogo. A aba `mine`/`catalog` vira estado compartilhado no `productsSearchStore` (em vez de estado local da página), mantendo a restauração de filtros e o texto da busca intactos. `/posts` e demais rotas conservam o comportamento anterior. PATCH sem impacto em API/dados, incorporado à candidata 3.3.0, `VERSION` inalterada.

> **05/11/2026 — ordem do card expandido de Produtos (staging):** manter intacto o cabeçalho (miniatura Shopee, nome e ID). Depois da divisória: carrossel de mídias extras salvas (setas anterior/próxima, até 3 mídias visíveis, adaptável a 2/1 por largura), descrição curta, links originais/afiliado e, por último, os 5 indicadores ID/preço/comissão/ganho/cadastro. Galeria continua privada, somente leitura, com prévia de imagens/vídeos; carregamento apenas ao expandir. A nova posição de indicadores é opt-in do card de Produtos; Listas/Usuários mantêm layout antigo. PATCH incluído na candidata 3.3.0, sem bump de VERSION, backend ou serviço.

> **05/11/2026 — Card de Produtos sem informações repetidas (somente staging):** ao expandir, os cinco indicadores comerciais superiores (ID Shopee, Preço, Comissão, Ganho/venda, Cadastrado) são a única apresentação desses dados; a timeline inferior mostra exclusivamente os links original e afiliado. Nome permanece no cabeçalho e a seção em largura total “Personalização salva” continua após os links. Sem mudança em dados, cálculo ou API; PATCH visual absorvido na candidata MINOR 3.3.0, VERSION 3.2.0 até release.\n\n> **05/11/2026 — Produtos: personalização no card expandido (somente staging):** o cartão detalhado agora inclui uma área de largura total “Personalização salva”, somente leitura, com descrição persistida, contagem e miniaturas da galeria privada (até 5 imagens e 2 vídeos). A imagem Shopee original permanece no cabeçalho. Tocar/clicar em uma miniatura abre modal de imagem ampliada ou player de vídeo; estados de vazio, carregamento e erro ficam no bloco, sem duplicar botões de edição. A galeria carrega sob demanda somente após expandir, respeitando o layout responsivo e os tokens existentes. Mudança compatível MINOR candidata 3.3.0; sem alteração de API ou VERSION.\n\n> **05/11/2026 — skeleton de Produtos (staging):** o carregamento de `/products` não deve apresentar bloco de ação no canto direito abaixo do cabeçalho: a página não possui botão nessa posição. Usar `PageSkeleton` sem a opção `action`, preservando título, filtros e conteúdo provisórios e o perfil independente da TopBar. Ajuste PATCH sem impacto em serviços ou dados.

> **05/11/2026 — correção de loading na TopBar (staging):** o chip frontal de perfil usa um skeleton com a mesma geometria do cartão final (70 px no desktop, 47 px no mobile), reserva a largura e permanece no fluxo do cabeçalho; a etiqueta traseira do plano não renderiza até existirem perfil ativo e plano válido. Falha/indefinição de plano não imprime placeholder visível nem invade os botões de Sair/Notificações. Mudança PATCH compatível acumulada na candidata MINOR 3.3.0; sem criar ambiente separado.

> **05/11/2026 — Personalizar produto (somente staging):** o seletor de mídia do navegador é acionado por botão visível “Selecionar imagens ou vídeos”, acessível no celular e desktop. Sob “Descrição curta”, reutiliza-se exatamente o controle do Criar Post (estilo Casual/Profissional/Divertido/Persuasivo, botão Gerar texto com IA, carregamento e atalho a Credenciais para ausência de chave Gemini). Resultado proposto preenche o textarea para revisão; limite 280 ponderado, sem URL, e Salvar continua separado. A barra de busca única, cards e topbar não mudam.

> **04/11/2026 — CORREÇÃO DEFINITIVA DA ORIENTAÇÃO VISUAL (staging):** referência "X.jpg" enviada por Rafa: **dois cartões empilhados verticalmente**. Cartão cinza com avatar/nome inteiro na frente; cartão do plano atrás, de mesma largura, parcialmente exposto **ABAIXO** como aba inferior. Não é lado a lado, nem o plano saindo pela direita. O texto do plano fica exclusivamente na faixa inferior visível. As notas anteriores sobre "à direita" representam interpretações rejeitadas e foram substituídas. Aguardar aprovação visual antes de promover para main. Nenhum serviço, banco ou agendamento será alterado.

> **04/11/2026 — REFINO DO DESENHO DE REFERÊNCIA (somente staging):** o cartão cinza com avatar/nome fica inteiro à frente, opaco e mais alto (70 px, avatar de 48 px), e a etiqueta dinâmica do plano nasce por trás, 26 px abaixo do topo, mostrando-se pela lateral direita como aba colada, com bases alinhadas. Em telas pequenas, mantêm-se dimensões compactas responsivas. Não mexer no fluxo ou nos serviços; main depende de aprovação de Rafa.

> **04/11/2026 — AJUSTE VISUAL SOLICITADO, SOMENTE PARA STAGING:** na Dashboard (`/app`), ocultar o campo de pesquisa do `TopBar` sem remover a pesquisa funcional de Posts. Reunir avatar/nome (cartão cinza à frente) e plano da conta (etiqueta contextual atrás, mais baixa e à direita, com a mesma base) em composição de abas sobrepostas inspirada **somente no formato** da terceira referência fornecida por Rafa; preservar foto, nome, rótulos dinâmicos, acesso a Perfis, acessibilidade e layout responsivo. Mudança visual PATCH planejada 3.2.1; `VERSION=3.2.0` até aprovação da promoção. Não inclui mudanças de backend, Supabase ou produção. Validação por CI/deploy staging pendente neste snapshot.

> **04/11/2026 — DASHBOARD POR CONTA EM PRODUÇÃO (release 3.2.0 em regularização):** quatro indicadores somam dados de todos os perfis da conta e os painéis exibem até cinco registros recentes reais, inclusive de perfis arquivados. Atalhos levam à criação de produto, post e lista, com perfil ativo preservado nas operações. Erros de leitura não devem parecer zero; textos em PT-BR e feedback acessível. CI/frontend validado na PR #269; verificação manual autenticada de navegação não foi declarada. As notas abaixo sobre funcionalidades ainda em PR são históricas.

> **03/11/2026 — F4D em PR, ainda sem merge/deploy:** interface de plano canônico da conta, badges Free/Pro/Premium/Administrador e consumo exato de produtos/conta, listas/perfil e perfis/conta via `GET /profiles/usage` autenticado/read-only. Conta/papel e limites são relidos no servidor; `profiles.plan_tier` não decide assinatura. Consumo de Agora/recorrência permanece indisponível (`null`), não zero fictício. Campanha respeita caps do servidor (Pro 15/3, Premium 30/15, ADMIN limites físicos), Free não cria/edita/upload/prévia, preservando leitura/exclusão do legado. Automação é vitrine, mesmo Premium/ADMIN: direito não significa executor. CTA informacional, sem preços, checkout ou alteração de plano. Nenhuma migration/SQL, scheduler, ativação, job, postagem ou mudança de main. `VERSION=3.0.0`. CI/QA/deploy não confirmados nesta nota. Ver [contrato F4, seção 10](PLANOS-F4-POLITICAS-E-FASES-20261103.md#10-f4d--interface-de-plano-consumo-e-acesso).

> **03/11/2026 — rótulos de planos F4A:** no card de perfis, mostrar `Pro` tanto para `pro` futuro quanto `plus` legado; usuário ADMIN com papel **confirmado** pelo servidor vê etiqueta “Administrador” em vez de etiqueta Free histórica. Estados bloqueados e CTA de upgrade na mesma linguagem visual são fase F4D, dependente de guardas de backend. Ver [contrato F4](PLANOS-F4-POLITICAS-E-FASES-20261103.md).

> **02/11/2026 — Correção dos posts em desenvolvimento (staging, ainda não publicada):** seleção de um produto, retirada de agendamento avulso, seletor desktop em 24h, histórico do estado de cada ocorrência, última postagem confirmada e erro simplificado para usuário. Supabase compartilhado impede apagar esquema/legado; erro HTTP 403 do Threads precisa de código Meta e autorização antes de declarar publicação funcionando. Detalhes e QA: [POSTS-AJUSTES-RECORRENCIA-20261102.md](POSTS-AJUSTES-RECORRENCIA-20261102.md). **Não alterar main/produção.**

> **Animação futura do login — decisão de 01/11/2026 (somente documentação, sem implementação):** Rafa definiu que o vídeo provisório de caixa do lado esquerdo de `/login` será substituído, em fase posterior e mediante aprovação, por **microapresentação cinematográfica premium do Auto Orbital** com a logo oficial preservada sem alterações. O roteiro/QA estão em [LOGIN-ANIMACAO-CINEMATOGRAFICA.md](LOGIN-ANIMACAO-CINEMATOGRAFICA.md) e no Vault documento 44. Preservar tokens, auth e `prefers-reduced-motion`. **Não modificar a mídia atual nesta tarefa.**

> **Design atual de 31/10/2026:** preservar tokens e componentes de `frontend/src/`, mas validar o CSS da branch e o Guia Mestre; fotografias anteriores à identidade Auto Orbital podem estar desatualizadas. **Primeira leitura obrigatória:** [AGENTS.md](../AGENTS.md) e [docs/GUIA-MESTRE-IA.md](GUIA-MESTRE-IA.md).

# DESIGN — Shopee Auto Vendas (frontend novo, React)

> Sistema visual real do frontend novo (`frontend/src/`). Extraído dos tokens CSS em
> `frontend/src/styles/tokens/` e dos componentes em `frontend/src/components/ui/`. O painel
> Flask legado (`web/templates/`, Tailwind + Alpine.js) **não** foi auditado neste documento
> — ver nota no final.

## 1. Paleta

Fonte: `frontend/src/styles/tokens/colors.css`. O comentário no topo do arquivo identifica a
origem: *"The seven hexes published on the MiT brand sheet, verbatim."* — ou seja, a paleta
base não foi gerada por este projeto, vem de uma referência de marca externa ("MiT"), com
degraus derivados medidos das telas entregues.

### Base (as 7 hexes da referência de marca)

| Token | Hex | Uso |
| --- | --- | --- |
| `--sky-400` | `#81BDFA` | Accent primário / azul de dado |
| `--steel-600` | `#405D7A` | Navy médio, base do gradiente de painel |
| `--navy-800` | `#303F54` | Navy profundo, chrome |
| `--black` | `#000000` | Tiles de token, fundo de marketing |
| `--green-600` | `#58956E` | Mint profundo, positivo discreto |
| `--mint-400` | `#82DBA3` | Mint de sinal / destaque de marca |
| `--white` | `#FFFFFF` | — |

### Semântico (aliases usados pelos componentes)

| Papel | Token | Valor |
| --- | --- | --- |
| Fundo do app | `--bg-app` | `#1E2A38` (gradiente `--bg-app-gradient`, 150deg) |
| Fundo do rail lateral | `--bg-rail` | `#28364A` |
| Superfície de card | `--surface-card` | `var(--navy-850)` = `#2B3949` |
| Painel "glass" (assinatura visual) | `--panel-glass` | gradiente 45deg, `rgba(71,99,132,.92)` → `rgba(58,80,102,.90)` |
| Texto principal | `--text-display` / `--text-body` | branco / `rgba(255,255,255,.88)` |
| Positivo | `--positive` | `var(--mint-400)` |
| Negativo | `--negative` | `#F1948A` (red-300) |
| Foco (outline) | `--focus-ring` | `rgba(129,189,250,.55)` |

Tema é **escuro por padrão e único** — não há tokens de light mode nos arquivos lidos.
**[A CONFIRMAR COM O USUÁRIO]** se existe intenção de suporte a tema claro.

## 2. Tipografia

Fonte: `frontend/src/styles/tokens/typography.css` + `fonts.css`.

- **Fonte única**: Mona Sans (peso variável 200–900), servida via CDN Fontsource
  (`jsdelivr`), com fallback `SF Pro Display, system-ui, sans-serif`.
- Escala nomeada por uso real (não t-shirt genérico): `--fs-micro` (9px, labels de rail) até
  `--fs-slide-hero` (80px, hero de case-study). Escala do painel principal:
  `--fs-body` (14px, texto padrão de UI) → `--fs-hero` (34px, saldo total).
- Pesos: `--fw-light` (300) a `--fw-black` (800).
- Papéis compostos (`--text-role-*`) combinam peso+tamanho+altura de linha+família em um só
  token — ex.: `--text-role-hero`, `--text-role-title`, `--text-role-body`, `--text-role-label`.

## 3. Espaçamento e raio

Fonte: `spacing.css`, `radius.css`.

- Base de 4px (`--sp-1:4px` até `--sp-12:80px`), com dois valores fora da progressão
  (6px, 10px) porque "the source uses them" (comentário no arquivo — medido de telas
  entregues, não gerado por regra).
- Componentes de layout com token próprio: `--rail-w:72px` (rail lateral desktop),
  `--topbar-h:56px`, `--tabbar-h:64px` (tab bar flutuante mobile), `--hit-min:44px` (alvo de
  toque mínimo).
- Raio: `--r-md:12px` (stat cards, botões, tiles de ícone) até `--r-2xl:28px` (shell do
  app/canvas de device); `--r-pill:999px` para pills; `--r-token:50%` para badges circulares
  de moeda/coin.

## 4. Elevação e movimento

Fonte: `elevation.css`. Sombras descritas no próprio arquivo como "soft, wide e quase
pretas — a UI vive num quarto escuro" — `--shadow-card`, `--shadow-panel`, `--shadow-float`,
`--shadow-shell` (a mais forte, `0 40px 120px rgba(0,0,0,.55)`), mais um par de "inner lit"
(`--inner-lit`, `--inner-lit-strong`) que dá a borda superior "iluminada" característica dos
painéis de vidro (`--panel-glass`). Blur em 3 intensidades (`--blur-glass`, `--blur-chrome`,
`--blur-scrim`). Tokens de `motion.css` não foram lidos em detalhe nesta verificação —
**[A CONFIRMAR COM O USUÁRIO]** se há convenção de duração/curva de easing documentada além
do arquivo.

## 5. Componentes reais (`frontend/src/components/ui/`)

Inventário direto do diretório (22 arquivos, sem duplicata por rede social — cada rede tem
seu card montado em `CredentialsPage.tsx` a partir destes primitivos):

`Badge`, `Button`, `ConnectionLight` (luz verde/amarelo/vermelho de status de conexão),
`DeltaChip`, `Icon`, `IconButton`, `InfoStat`, `Modal`, `NotificationsBell`, `Panel`,
`SearchField`, `SegmentedToggle`, `Select`, `SideRail`, `Sparkline`, `StatCard`,
`StatusBadge`, `TextInput` (com toggle de mostrar/ocultar senha embutido — reutilizado por
login, cadastro, troca de senha, credenciais e usuários, confirmado no vault), `Textarea`,
`TimelineListCard`, `TokenBadge`, `TopBar`.

Ícones: **Lucide React** em todo o app — decisão documentada no `README.md` como
substituição de Material Symbols via Google Fonts, que falhava no Render.

## 6. Nota sobre o painel legado (Flask)

O painel em produção hoje (`web/templates/`, Tailwind CSS + Alpine.js) **não foi auditado**
neste levantamento — os tokens acima descrevem só o frontend React novo. Se as duas
interfaces devem convergir visualmente antes de aposentar o Flask, isso é uma decisão de
produto ainda não registrada no código nem no vault consultado.
**[A CONFIRMAR COM O USUÁRIO]**.

## Carregamento em esqueleto: como usar em páginas novas

Páginas e rotas novas devem usar `PageState` para estados de dados e `PageSkeleton` como fallback:

```tsx
import { PageSkeleton, PageState } from "../components/ui/Skeleton"

export function NewPage() {
  const { data, isLoading } = useQuery({ queryKey: ["new"], queryFn: loadData })
  return (
    <PageState loading={isLoading} skeleton={<PageSkeleton variant="table" />}>
      <RealContent data={data} />
    </PageState>
  )
}
```

Use a variante cuja geometria corresponda ao conteúdo real (`cards`, `table`, `form`, `detail` ou `list`). Nunca use spinner ou o texto “Carregando” como estado de página; spinners pequenos permanecem permitidos em botões de ação. O esqueleto deve reservar as mesmas alturas e regiões do conteúdo final, usar somente tokens existentes e respeitar `prefers-reduced-motion`.

## Referências

- `frontend/src/styles/tokens/*.css`
- `frontend/src/components/ui/*.tsx`
- `README.md` (seção Tecnologias)
- Design system export local em `design-system-export/` e `design/stitch-redesign-2026-08-19/`
  (não auditado em detalhe nesta verificação — conteúdo de redesign histórico, ver
  `05-PRD-Redesign-Frontend-Stitch.md` no vault) **[A CONFIRMAR COM O USUÁRIO — se este
  redesign já foi incorporado ou é referência descartada]**

## Atualização 2026-10-13 - decisão de marca futura

Decisão aprovada em 2026-10-13: a marca futura do produto será **Auto Orbital**. Implementação ainda pendente. A fonte ativa verificada segue sendo **Mona Sans** e a recomendação do plano é preservá-la. Ver `docs/rebranding/34-Rebranding-Auto-Orbital-Plano-Mestre.md`.

## Atualização 2026-10-14 - identidade AUTO ORBITAL aplicada (versão 2.4.0)

A identidade **AUTO ORBITAL** foi aplicada ao app: paleta e grafites nos tokens de cor, logos, favicon, PWA instalável (manifest e service worker) e nome visível trocado. Layout e fonte **Mona Sans** foram preservados. Telas ainda não migradas em grupos seguem pendentes; ver checklist em `docs/TASK.md`.

## F4D — apresentação de planos e bloqueios (PR, 03/11/2026)

Reusa Badge/Panel/Button/Skeleton e tokens existentes. Badge da conta na TopBar e cards de perfil, não o espelho legado do perfil. Resumos por contexto em Produtos, Listas, Perfis e Criar POST distinguem conta/perfil e janela. Não apresenta ausência como zero, erro como Free ou direito Premium como automação operacional.

CTA “Conhecer planos e upgrade” expande informação local com aria-expanded/aria-controls, sem rota fictícia ou cobrança. Contratação/alteração ainda indisponível. Grade fluida, texto quebrável, foco visível, alvo mínimo e mensagens textuais (não somente cor/hover). Vitrine de automação permanece visível em Free/Pro. ADMIN não bloqueia telas comuns e mantém segurança/regras externas.

Campanha limita seletor/datas por política; frequência legada acima da nova cota não é truncada silenciosamente e não pode salvar agenda inválida como null. Leitura/exclusão de rascunhos/anexos existentes permanecem; somente novas mutações de campanha são bloqueadas. Automatizados SSR/contratos cobrem estados; inspeção visual real desktop/mobile com sessão fica pendente até deploy autorizado.
