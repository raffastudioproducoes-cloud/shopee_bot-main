# Roadmap de animações e UX — Auto Orbital (lista futura, nada implementado)

> Criado em 09/11/2026 a pedido de Rafa, a partir de 18 prints e 4 vídeos de referência. **Somente planejamento:** nenhuma linha de código foi alterada. Cada item entra em PR próprio para a staging, é homologado por Rafa e só depois vai para a `main`, como nas demais releases.
> Fontes: os vídeos foram analisados por quadros amostrados (não pelo áudio); tempos abaixo são **estimativas** a confirmar na implementação.

## 1. Princípios (valem para todos os itens)

1. **Pouco e com propósito:** no máximo um efeito de destaque por tela; nada em tabelas, listas de trabalho e métricas de uso.
2. **Sem biblioteca nova:** CSS + React, como a confetti da campanha. Nenhum peso relevante no bundle (hoje só React, TanStack, Zustand e lucide).
3. **Acessível:** tudo respeita `prefers-reduced-motion` (sem movimento, só troca de estado) e nunca bloqueia a ação do usuário.
4. **Rápido:** 150–400 ms por micro-efeito; a entrada pós-login até ~2,5 s e **nunca atrasa o carregamento real**.
5. **Design system:** só os tokens/cores já existentes (violeta/azul/ciano da marca).
6. **Testar no celular fraco** na staging antes de promover; medir tamanho do bundle antes/depois.

## 2. Lista priorizada

| ID | Onde | Efeito | Referência | Esforço | Risco |
|---|---|---|---|---|---|
| A1 | Depois do login → dashboard | Splash com a logo, círculo que abre e revela o dashboard, cards em cascata, números contando, barras enchendo (ver seção 3) | Vídeo "Dashboard V22" | M | Médio (percepção de lentidão) |
| A2 | Troca de página | Esmaecer a página, esqueleto, entrada em cascata do conteúdo | Vídeo "Dashboard V22" | M | Baixo |
| A3 | Números do dashboard | Contagem de 0 até o valor (só na 1ª carga) | Vídeo "Dashboard V22" | P | Baixo |
| B1 | Login | Rótulo flutuante e brilho na borda do campo ao focar | Text Field 1 | P | Baixo (vídeo de fundo ao lado: manter discreto) |
| B2 | Login (erro) | Dica vermelha enquanto digita e aviso que balança de leve | Text Field 4 | P | Baixo |
| B3 | Login (sucesso) | Botão "Entrar" vira ✓ antes da splash | Button 2 | P | Baixo |
| C1 | Apagar produto, post, campanha | Segurar para confirmar (anel enche, vira ✓) | Button 2 / 1 | M | Baixo; protege contra clique acidental |
| C2 | Ativar campanha | Já existe confetti; somar "deslizar para confirmar" | Button 2 / 6 | M | Baixo |
| C3 | Copiar link afiliado | Ícone vira ✓ com balão "Copiado!" | Button 2 / 4 | P | Baixo |
| D1 | Mensagens (toasts) | Entrada suave, saída suave, agrupar iguais com "×3" | Notifications 2 | P | Baixo |
| D2 | Excluir com "Desfazer" | Barra que sobe com "Desfazer" | Notifications 2 / 4 | M | Médio (exige desfazer real) |
| E1 | Menu lateral | Pílula deslizante marcando a página atual | Tab Bar 1 | P | Baixo |
| E2 | Etapas da campanha | Linha que enche, passos viram ✓, "faltam N passos" | Progress Steps 1 | M | Baixo |
| E3 | Botão de plano/upgrade | Brilho que passa na diagonal | Button 2 / 5 | P | Baixo (1 só por tela) |
| E4 | Campos com limite (texto da postagem) | Anel contador que fica rosa ao passar do limite | Text Field 6 | P | Baixo |
| E5 | Senha | Mostrar/ocultar com troca suave | Text Field 5 | P | Baixo |

Ordem sugerida: **1)** A1+A3 (entrada pós-login), **2)** B1–B3, C1, C3, D1, **3)** A2, E1, E2, **4)** demais.

## 3. Entrada pós-login (vídeo principal) — como aplicar

**O que o vídeo mostra (≈ 5 s):**
1. Tela verde-escura, logo pequena com brilho suave e partículas (~1,2 s).
2. A logo sobe para o canto onde ficará o menu; um círculo claro cresce e **revela o dashboard** (círculo expandindo, ~0,8 s).
3. Entrada em cascata: menu lateral, cabeçalho com texto digitado, cards e avatares.
4. Números **contam** (00,0 h → 10,4 h; 00:00 → 49:83), barras e medidores enchem.
5. Troca de página: a página esmaece, aparece o esqueleto neutro e o conteúdo novo entra em cascata, de novo com contagem e barras.

**Mapa para o nosso site (já existe a base):**
- Já temos `OrbitalLoader` (loading do router), `Skeleton/SkeletonCard/SkeletonRegion`, `StatCard` e o `DashboardPage` com 4 cards de contagem; o login navega para `/app` (ou `/admin/overview`).
- Novos componentes pequenos: `PostLoginSplash` (logo + círculo via `clip-path`), `useCountUp` (contagem com `requestAnimationFrame`), `Reveal/Stagger` (entrada em cascata por CSS com `--i`), `PageTransition` (esmaecer + esqueleto).
- Conectar em: `LoginPage` (navegação após sucesso), `DashboardPage` e `StatCard` (contagem), troca de rota.

**Regras de segurança da experiência:**
- Mostrar a splash **no máximo 1 vez por sessão** (`sessionStorage`), e só se os dados ainda estão carregando; se já estão em cache, pular.
- Nunca esperar a animação para liberar cliques; toque ou tecla encerra a splash.
- `prefers-reduced-motion`: sem splash nem contagem, só o dashboard.
- Duração total alvo ≤ 2,5 s no celular; se passar disso, reduzir.
- Admin (`/admin/overview`) pode ficar sem splash.
- Cores: fundo escuro da marca (o vídeo usa verde; usaremos o azul/violeta do design system).

## 4. Aprendizados dos outros três vídeos (UX, não animação)

**"Pricing — 3 planos iguais, feito por IA" (inglês):** destacar só **um** plano; só um selo "Mais popular"; listar **o que muda** entre planos, não o que se repete; **um** botão primário forte por tela; no alternador mensal/anual mostrar a economia **em dinheiro**, não em %. → Aplicar na página de Planos (Free/Pro/Premium).

**"Leis de UX" (português):** Fitts (botão grande e perto de onde o usuário está), Hick (menos opções; recomendar uma), Zeigarnik / gradiente de meta (mostrar o cadastro incompleto e **quantos passos faltam**), Von Restorff (o diferente é lembrado: destacar a ação principal), Miller (agrupar menus longos). → Candidatos: agrupar menu de configurações, destacar a ação principal por tela, progresso nas etapas da campanha e nos cadastros de credenciais.

**"Testes de carga" (espanhol):** testar com muitos usuários ao mesmo tempo (ferramentas k6, Locust, Artillery), olhar o p95, não a média. → Tarefa separada de infraestrutura (item 5).

## 5. Tarefas futuras relacionadas (fora das animações)

- **UX-1:** Página de Planos: um plano destacado, selo único, diferenças em lista, economia em R$.
- **UX-2:** Agrupar o menu de configurações e destacar a ação principal por tela.
- **UX-3:** Indicador de progresso e "faltam N passos" nos fluxos longos.
- **INFRA-1:** Teste de carga na **staging** (por exemplo k6) para saber o limite real no plano gratuito do Render; medir p95. Depende do upgrade de plano para virar meta. Ligado aos itens S-04/S-05 da auditoria, que aguardam o upgrade.

## 6. Decisão pendente de Rafa

Escolher o primeiro lote (sugestão: A1+A3, B1–B3, C1, C3, D1) e aprovar a ideia da splash apenas na primeira entrada da sessão.
