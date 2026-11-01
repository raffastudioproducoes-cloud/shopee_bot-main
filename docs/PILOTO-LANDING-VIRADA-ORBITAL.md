# Landing Auto Orbital — piloto isolado “Do caos à órbita” (v0)

> **Estado:** proposta de implementação em branch, sem integração na apresentação aprovada, sem publicação em produção. Rafa havia autorizado storyboard e piloto da transformação orbital, visual e silencioso, com logo fiel. Ver [Vault 34](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/34-Planejamento-Landing-Publica-Auto-Orbital.md), [guia 42](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/42-Guia-Motion-3D-Remotion-ThreeJS-Landing-Auto-Orbital.md) e [storyboard 43 no PR #29](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/pull/29).

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