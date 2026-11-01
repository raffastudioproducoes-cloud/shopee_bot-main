# Login Auto Orbital — animação cinematográfica de apresentação (PLANEJAMENTO FUTURO)

> **Decisão de Rafa em 01/11/2026: APROVADA COMO DIREÇÃO CRIATIVA, NÃO COMO IMPLEMENTAÇÃO.** O vídeo do login atual **não deve ser substituído nesta fase**. A solicitação atual autoriza **somente documentar no Vault e no projeto**; código, assets, dependências, autenticação, ambiente e deploy permanecem intactos.
>
> **Fonte canônica de direção:** [Vault 44 — Direção da animação cinematográfica do login](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/44-Planejamento-Animacao-Cinematografica-Login-Auto-Orbital.md) (será publicada na main do Vault **apenas depois da aprovação/merge do PR documental**). Ler também o [escopo imutável da landing](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/34-Planejamento-Landing-Publica-Auto-Orbital.md) e o [guia de motion](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/42-Guia-Motion-3D-Remotion-ThreeJS-Landing-Auto-Orbital.md).

## Contrato de produto

A página `/login` terá **futuramente** no espaço audiovisual esquerdo uma **microapresentação cinematográfica original** do Auto Orbital, com o **logotipo oficial sem qualquer modificação** e uma sequência visual que explique, brevemente, o valor do produto para afiliados: oportunidades, produtos/listas, preparação dos conteúdos, agendamento/destinos autorizados e acompanhamento.

**Não** transformar a apresentação em uma caixa, card ou compilação genérica de partículas. O vídeo de **caixa de papelão** atualmente exibido é um placeholder, **não a direção artística final**. A animação será sofisticada, leve, integrada à linguagem orbital da aplicação e discreta o suficiente para não competir com login/CTA.

### Regras obrigatórias

1. **Marca:** obter os assets diretamente de `frontend/src/assets/brand/logo-full.png` (matriz oficial) e dos exports `frontend/public/brand/`; a fonte da verdade da logo é `frontend/public/brand/README.md`. **Não redesenhar, distorcer, estilizar ou improvisar a marca.**
2. **Design system:** respeitar `frontend/src/styles/tokens/`, Mona Sans, azul escuro/grafite, ciano/azul e violeta/lilás sutis, composição premium. Ver [DESIGN.md](DESIGN.md) e o CSS implantado.
3. **Persuasão:** consultar skill `vender-com-valor` e traduzir *dor real → função comprovada → benefício plausível*. Sem promessas de vendas, métricas inventadas, rede desabilitada como ativa ou automação 100% futura tratada como entregue.
4. **Separação:** a animação **não é o piloto Scroll World nem o vídeo da landing**. Deve ter storyboard, QA e aprovação próprios. Reutilizar apenas a identidade e a coerência editorial aprovadas.
5. **Autorização e custo:** sem nova dependência/serviço pago, sem render definitivo ou alteração de código antes de aprovação explícita de Rafa. Som/sincronia sonora **não aprovado**; planejar a primeira versão para funcionar completamente no silêncio.

## Ponto exato no código (fotografia de staging em 01/11/2026)

| Elemento | Local / comportamento atual |
| --- | --- |
| Página de login | `frontend/src/pages/LoginPage.tsx` |
| Arquivo do vídeo existente | `frontend/public/videos/login-bg.mp4`, servido como `/videos/login-bg.mp4` |
| Elemento de vídeo | `video` com `autoPlay`, `loop`, `muted`, `playsInline`, dentro de `login-split__image` |
| Gradiente/encobrimento | `login-split__fade` e `frontend/src/pages/LoginPage.css` |
| Área de login | `login-split__form` — preservar integralmente UI e comportamento auth |
| Desktop | Divisão aproximada 45% apresentação / 55% formulário; o vídeo usa elemento amplo com `object-fit: cover` sob gradiente |
| Celular | Mídia em seção própria de cerca de 38vh, acima do formulário |
| Acessibilidade já existente | Quando `prefersReducedMotion` é verdadeiro, React **não monta** o elemento de vídeo |
| Assets oficiais em uso | `/brand/wordmark.png` no formulário; `/brand/symbol.png` disponível |
| Fonte de verdade para o roteiro | Guia Mestre [GUIA-MESTRE-IA.md](GUIA-MESTRE-IA.md), [TASK.md](TASK.md) e documentos do Vault |

Esses pontos exigem nova inspeção no SHA específico quando a implementação for aprovada. **Não inferir que testar o vídeo por screenshot prova sua qualidade técnica ou ritmo.**

## Etapas futuras, somente após autorização

- [ ] **LG.1 — Briefing visual:** roteiro curto, duração e copy propostos; mapear funções ativas e cenários desktop/mobile. Aprovação de Rafa antes de render final.
- [ ] **LG.2 — Storyboard:** quadros-chave, temporização, brand asset original, poster/fallback e prévia em baixa resolução. Revisão de identidade e verdade do produto.
- [ ] **LG.3 — Protótipo silencioso:** considerar animação produzida offline com Three.js/Remotion **somente se apropriado**; export leve, compressão, poster e sequência de loop. Sem WebGL obrigatório no dispositivo de quem acessa.
- [ ] **LG.4 — Integração em branch isolada de staging:** substituir somente a mídia e dependências justificadas, preservando os campos/ações de Supabase, Google e nome de usuário temporário de suporte da Shopee. Plano de reversão para vídeo atual.
- [ ] **LG.5 — Homologação:** mobile e desktop reais, posters e crop seguros, vídeo sem autoplay por redução de movimento, ausência de flash/jank/layout shift, replay sem corte, load em rede lenta e fluxos de autenticação. CI + navegador + aceite visual de Rafa.
- [ ] **LG.6 — Produção:** nova autorização expressa de promoção para `main`; deploy/monitoramento somente depois dos gates anteriores.

### Critérios de aceite do trabalho futuro

- Logo/id visual **reconhecivelmente idênticas** à marca matriz, sem redesenho por geração de imagens.
- Sequência **cinematográfica e autoral**, compreensível sem som, não uma caixa/card com ícones.
- Microapresentação mostra capacidades verificadas sem funcionalidades inventadas.
- O formulário permanece prioritário: campos, Google, recuperação, signup e suporte Shopee disponíveis, sem clique bloqueado.
- Mobile e `prefers-reduced-motion` têm alternativa estática bonita e legível; falha do MP4 não degrada a autenticação.
- Arquivo e carregamento não criam regressões relevantes de desempenho, especialmente no celular.

## Estado desta tarefa documental

- **Em andamento agora:** registrar no Vault e no repositório em **PRs de documentação**.
- **Aguardando decisão futura:** roteiro final, duração, custos, direção de arte, storyboard, mídia e implementação.
- **Nada entregue no produto agora:** `LoginPage.tsx`, `LoginPage.css` e `login-bg.mp4` continuam como estavam.
- **Não confundir com a Fase 2 da landing**, que possui autorização, branch e QA independentes.

**Gatilho para próxima IA:** antes de qualquer alteração na tela de login, ler **este arquivo inteiro**, os documentos canônicos do Vault (incluindo o 44), `AGENTS.md`, `GUIA-MESTRE-IA.md`, `DESIGN.md` e a skill de sites premium e de venda com valor. Ao concluir um documento, reabrir e reler as duas fontes, conferir links e pendências condicionais do `TASK.md` do Vault.