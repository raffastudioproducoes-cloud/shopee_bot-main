# 02/11/2026 — INSERÇÃO DO PILOTO V3.2 NA LANDING (SOMENTE STAGING)

> **Nova autorização de Rafa:** mostrar a animação já existente no contexto real da página, na seção `#virada`, mantendo seu caráter provisório. Esta autorização substitui apenas o bloqueio anterior de integração na landing **de staging**; não autoriza promoção à `main`, à produção ou finalização estética.

- **Posição:** seção 03, “A virada”, entre o texto de transição e o fluxo Produto → Conteúdo → Agenda → Acompanhamento. Preservam-se as demais seções, copy, rotas, login e experiência do produto.
- **Reuso:** o player `OrbitalMotionPlayer` é compartilhado entre `/presentation/pilot` e a landing, sem duplicar cenas. Mantém seis atos/10 s, física 3D dos cards, Canvas, câmera, quadro final e ausência de som.
- **Comportamento contextual:** carregamento sob demanda próximo da seção, reprodução automática única quando a cena fica visível, pausa ao sair de quadro, botões para controlar/reiniciar e scrub. `prefers-reduced-motion` mostra o final estático. O módulo não altera o título/metadados da landing.
- **Transparência:** legenda “Prévia visual em avaliação”; as peças são ilustrativas, a automação integral com IA continua em desenvolvimento, e a marca procedural final não é o arquivo oficial.
- **Escopo de publicação:** somente branch de trabalho com destino `staging`. `main` e Render produção permanecem fora do escopo; QA móvel e aceite estético de Rafa continuam pendentes.

---

# V3.2 — PROFUNDIDADE 3D SOMENTE NOS CARDS (01/11/2026)

> **Decisão de Rafa:** a V3.1 é provisória, mas a única alteração agora é nos cards de produto/propaganda da cena procedural. Eles não devem parecer cartões estáticos sobre um plano. **Não alterar** a assinatura final/logo, horizonte de eventos, câmera global, texto, cenas, ritmo, storyboard de 10s, controles, som ou landing principal.

## Ajuste autorizado e isolado

- **Geometria espacial:** cada uma das oito fichas passa a usar um `translateZ` independente, leve flutuação, inclinações `rotateX/rotateY` e ordenação visual por profundidade; as mesmas posições X/Y e janelas de entrada/saída são preservadas.
- **Virada física:** no intervalo de transformação já existente, o antigo achatamento em `scaleX` é substituído por meia-volta em `rotateY`, com duas faces em planos opostos, ocultação da frente ao virar e face de anúncio renderizável no verso. A progressão de produto → propaganda e os textos continuam idênticos.
- **Material:** espessura sutil da ficha com placa central entre faces, reflexo e sombra próprios, sem WebGL, Three.js, bibliotecas, vídeos, imagens ou áudio adicionais.
- **Restrições:** sem alteração de `drawSpace`, `ProceduralUniverse`, `KineticType`, `DashboardReveal`, `OrbitalSignature`, `chapters`, `DURATION_MS` ou `ao3-camera`. Apenas `Sheet`, CSS `ao3-sheet*`, teste de contrato e documentação.
- **Referências consultadas:** [Impeccable](https://github.com/pbakaus/impeccable) para profundidade funcional e animação com propósito; [Taste Skill](https://github.com/Leonxlnx/taste-skill) para hierarquia, verificação visual e evitar excesso de efeitos. A URL [Christonit/emil-kowalski-animation-course](https://github.com/Christonit/emil-kowalski-animation-course) contém um README genérico React/Shadcn/Tailwind V4, sem guia específico de animação na raiz; nenhuma técnica foi importada dele.
- **Estado em 02/11/2026:** [PR #174](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/174) integrado a **staging**; correções pontuais [#175](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/175), [#176](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/176) e [#177](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/177) após inspeção visual. CI e deploy Render verdes. Verificados quadros 3.0s (profundidade), 5.6s (conversão), 6.1s (verso com anúncio efetivamente visível) e 9.0s (marca intacta). **QA móvel e aceite estético de Rafa pendentes; produção e landing publicada intocadas.**
- **Cuidado técnico aprendido:** para a virada de 180° com faces de produto/anúncio, a placa de espessura deve ficar entre as faces, não pode aparecer do verso, e o fade deve ser aplicado a cada superfície. Usar `backface-visibility:hidden` na frente e placa, mas permitir renderizar a face publicitária traseira para evitar verso vazio em composição 3D do navegador.

---

# V3.1 — REFINO SOMENTE DA ASSINATURA FINAL (01/11/2026)

> **REVISÃO DE RAFA:** O estudo V3 ficou razoável e poderá servir como base, mas **não está aprovado como definitivo**. O proprietário pediu exclusivamente corrigir a marca e o nome no último quadro; mais velocidade e dinamismo ficam como observações para uma iteração futura, **sem alterar agora** tempo, cenas, câmera, transições, texto ou som.

- **Versão preservada:** branch de arquivo [archive/landing-motion-v3-before-logo-2026-11-01](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/tree/archive/landing-motion-v3-before-logo-2026-11-01), apontando ao estado original da V3 (commit `ad3762e0979d70f8df3fcfb5cdf51804fd67a032`). É possível rever exatamente a animação anterior.
- **Única alteração visual autorizada:** assinatura final `OrbitalSignature` e seus estilos: remover a elipse secundária sobre o buraco negro; reconstruir em SVG inline o “O” inclinado do wordmark conforme a matriz `/brand/wordmark.png` (núcleo escuro, horizonte ciano-azul-violeta, anel diagonal), mantendo “Auto” claro e “rbital” em degradê. É uma interpretação por código, não uma substituição do arquivo oficial.
- **Imutável nesta etapa:** `drawSpace`, universo Canvas, produtos, cards, câmera, texto cinético, painel, 10 segundos, momentos de entrada/saída, conteúdo do subtítulo, aviso “EM DESENVOLVIMENTO”, controles e ausência de áudio. Nenhum PNG é usado dentro da animação.
- **Preservação do “vídeo”:** o protótipo é uma animação procedural React/Canvas reprodutível em `/presentation/pilot`, **não um MP4 renderizado**. A branch de arquivo congela a versão anterior; a próxima revisão deve continuar separada e não deve alterar a produção.
- **Validação pendente:** comparar o quadro final em staging, desktop e celular com o master da marca; aprovação visual explícita de Rafa antes de integração na landing principal. Feedback atual: melhora perceptível em relação à V2, porém ainda não definitiva.

---

# V3 — MOTION INTEGRALMENTE PROCEDURAL (01/11/2026)

> **DECISÃO MAIS RECENTE DE RAFA:** V2 descartada como direção visual: cartões/postagens grudados, imagem PNG do buraco negro e movimentos que não representam o texto. **Não reutilizar a cena V2 nem descrever V1 ou V2 como aprovadas.** O código V3 substitui apenas a prévia isolada /presentation/pilot. Sem áudio, sem imagens coladas, sem alteração da landing ou produção.

## Storyboard silencioso — seis atos, dez segundos

| Tempo | Mensagem | Movimento programado | Aceite |
| --- | --- | --- | --- |
| 0–2,4 s | Um produto vira várias obrigações | Produto vetorial no centro gera fichas independentes de tarefas e redes, texto cinético | Relação causa → rotina legível |
| 2,4–3,7 s | Acúmulo | Fichas com posições, velocidades, ângulos e profundidades diferentes, câmera atravessa o cenário | Sensação de carga, sem cartões colados |
| 3,7–4,3 s | Pausa | Desaceleração perceptível, letras “PARE.” surgem no centro | Mudança de ritmo sem som |
| 4,3–6,1 s | Transformação | Horizonte de eventos, lente, disco de acreção, plasma e partículas desenhados por Canvas 2D, anúncios convergem por órbitas distintas | Buraco negro programado e protagonista, produto → propaganda visível |
| 6,1–7,6 s | Organização | O espaço revela composição HTML/CSS inspirada na interface do Auto Orbital: produto, destinos, agendamento | Painel reconhecível, sem recursos fictícios |
| 7,6–10 s | Identidade | O buraco negro procedural permanece; assinatura vetorial CSS e mensagem final | Ciclo orbital e mensagem memoráveis |

### Diretrizes técnicas obrigatórias

- Nenhum arquivo de imagem, GIF, screenshot, sprite, vídeo ou áudio é usado na cena. A marca canônica de produção **não é modificada**. A assinatura CSS final é **interpretação procedural provisória**, não reprodução certificada/pixel-a-pixel do master; antes de substituir a landing, Rafa precisará avaliar fidelidade e, se necessário, fornecer ou aprovar curvas vetoriais da marca.
- Canvas 2D com gradientes radiais, círculos, elipses, partículas, camadas luminosas e composição aditiva gera o buraco negro e o horizonte de eventos; DOM/CSS para produtos, anúncios, tipografia e interface. Relógio único de requestAnimationFrame com scrub, pausas e reinício. Nenhum serviço nem biblioteca externa.
- Performance: DPR limitado, ResizeObserver, preferência de redução de movimento e versão mobile. Sem sons até nova instrução.
- Mensagem comercial: dor → consequências → interrupção → solução → demonstração → visão. Coleta e postagem 100% com IA continuam **em desenvolvimento**; não afirmar disponibilidade ou vendas garantidas.
- Não integrar na landing aprovada sem CI, QA real desktop/mobile, reprodução completa, sem erros, e aprovação de Rafa. Não fazer merge para main/produção nesta etapa.
- Referências: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation ; https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Media_queries/Using_for_accessibility ; https://web.dev/articles/animations-and-performance

---

# Revisão V2 — resposta à reprovação expressa de Rafa (01/11/2026)

> **DECISÃO MAIS RECENTE / OBRIGATÓRIA:** Rafa reprovou e **descartou a direção visual V1** por falta de vida, excesso de zoom/transição simples, tipografia sem animação, câmera estática e conceito de marca equivocado. **Não voltar à V1 nem descrevê-la como aprovada.** A marca é um **buraco negro com horizonte de eventos**, com **papéis = produtos** que se transformam em **propagandas** ao entrar em órbita, representando um **ciclo de divulgação automático como visão futura**.

## Contrato do novo piloto V2

- Rota de laboratório preservada: `/presentation/pilot`, **somente staging**, sem modificar a landing, o login ou a produção.
- **Marca inviolável:** usar PNG oficial `/brand/symbol.png` no centro e na assinatura final; wordmark oficial apenas como complemento. Não modificar pixels, paleta ou desenho originais. Horizonte de eventos deve ter protagonismo.
- **Movimento com propósito:** câmera virtual em múltiplos ângulos (`rotateX/Y/Z`, deslocamento e dolly), perspectiva 3D e sobreposição de profundidade; tipos grandes com letras individuais em sequência e cortes mais rápidos.
- **Metáfora compreensível:** folhas inicialmente com produto e informações, multiplicação por tarefas, atração gravitacional, rotação no horizonte, virada de face de cada folha para uma peça visual de propaganda, ciclo orbital estável; encerramento com o símbolo oficial.
- **Tempo e controles:** 9,6s para experimento; play/pause/restart/scrub; sem áudio por decisão do proprietário. A velocidade, câmera e ritmo ainda dependem de avaliação visual de Rafa.
- **Verdade funcional:** a automação ponta a ponta com IA ainda está **em desenvolvimento**. Não sugerir que já é serviço disponível; peças simuladas são identificadas como conceito artístico.
- **Acessibilidade/performance:** versão estática em `prefers-reduced-motion`, layouts mobile, sem libs terceiras, assets PNG já servidos pelo produto, sem requisições de usuários.
- **Aprovação:** V2 é apenas tentativa de correção; CI verde e QA de navegadores **não equivalem a aceite** do proprietário. Nenhuma integração em `#virada` sem decisão posterior.

---

# Landing Auto Orbital — piloto isolado “Do caos à órbita” (v0)

> **Estado:** proposta de implementação em branch, sem integração na apresentação aprovada, sem publicação em produção. Rafa havia autorizado storyboard e piloto da transformação orbital, visual e silencioso, com logo fiel. Ver [Vault 34](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/34-Planejamento-Landing-Publica-Auto-Orbital.md), [guia 42](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/42-Guia-Motion-3D-Remotion-ThreeJS-Landing-Auto-Orbital.md) e [storyboard 43 no Vault](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/43-Storyboard-Piloto-Shorts-Audio-Transformacao-Orbital-2026-11-01.md).

## Propósito e limites

Testar apenas a **segunda cena** da narrativa, **a transformação orbital**: um produto se dispersa em atividades repetidas, essas tarefas recuam/convergem e um fluxo organizado toma a cena. Ao fim, o **wordmark oficial** aparece sem transformação da sua arte.

**Esta é uma prévia visual em código React/CSS** para validar composição e tempo antes do render de vídeo definitivo, não um arquivo Remotion/Three.js exportado. A prévia foi deliberadamente separada em `/presentation/pilot`, sem link comercial na landing, e não altera `/presentation`, `/`, `/login` ou `/app`. Não requer biblioteca ou serviço novo.

## Contrato técnico

- **Arquivos:** `frontend/src/pages/OrbitalPilotPage.tsx` e `OrbitalPilotPage.css`; rota adicional em `frontend/src/router.tsx`; teste de contrato `frontend/tests/landing-orbital-pilot.test.mjs`.
- **Arte:** `/brand/wordmark.png` e `/brand/symbol.png`; ambos exports da matriz aprovada. Não aplicar distorção, recoloração ou shader à marca; apenas transparência/escala de entrada com pixels intactos.
- **Tempo:** 10 s de prévia, com botão Reproduzir/Pausar/Reiniciar e range de avanço manual para inspeção do beat. A duração ainda é uma proposta de piloto, não decisão para a peça final.
- **Fases:** tarefa manual → multiplicação de ações → pausa → convergência/luz ciano → fluxo ilustrativo (Produto, Conteúdo, Agenda, Histórico) → logo oficial.
- **Áudio:** nenhum. Não tenta sincronizar música de Shorts sem áudio original nem direitos.
- **Responsividade:** layout de cena de tamanho limitado, adaptação de rótulos e painéis no celular, controles tocáveis.
- **Acessibilidade:** `prefers-reduced-motion` mostra assinatura final estática, cancela reprodução; documento `noindex`; instruções e captions em DOM; foco visível.
- **Segurança/verdade:** cenas explicitamente ilustrativas, sem dados de clientes, sem suposta conexão universal ou automação integral. Nada é enviado a rede/API.

## Portões para homologação

1. [ ] CI executa TypeScript/Vite e os testes de contrato.
2. [ ] Inspecionar a URL da branch homologada em desktop e celular, incluindo reduzir movimento, timeline manual e captura de quadros inicial, intermediário e final.
3. [ ] Conferir a legibilidade da logo oficial no frame final **visualmente**, e não apenas por checagem de `src`.
4. [ ] Rafa aprova ou pede alterações na cena antes de incorporar o resultado à seção `#virada`.
5. [ ] Só depois pesquisar/exportar mídia final e realizar QA de desempenho, versões mobile, poster, Scroll World real e eventual integração em `staging`. A produção requer autorização distinta.

**Não considerar finalizada a animação** apenas porque o código compila. O componente é uma ferramenta de revisão de arte e timing; não altera o protótipo aprovado.