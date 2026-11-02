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
