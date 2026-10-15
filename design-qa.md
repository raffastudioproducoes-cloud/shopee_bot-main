# QA visual — administração Auto Orbital

Resultado local: aprovado para revisão. Ativação contínua dos provedores permanece pendente; nenhum deploy ou DDL executado.

## Referências e fidelidade

Comparação visual lado a lado do frame do vídeo e da tela de usuários em 1360 px: cabeçalho horizontal com ícone e rótulo ativo, trilho lateral estreito, quatro indicadores, filtros, três colunas de cards, coluna de atividade e dock inferior. Mantidos os tokens de cores e fonte Mona Sans do produto. Ícones de navegação 16 px; controles acessíveis de 44 px; formulário de usuário com largura de 400 px. O vídeo não mostra um diálogo aberto; sua largura não foi medida na referência.

O GIF orientou a visão geral: curvas ciano com preenchimento gradual, grade discreta, eixos com zero, anéis por plano e módulos compactos. Não há globo fictício: localização não é coletada. Curvas preservam as amostras e o eixo temporal; dados ausentes não viram séries inventadas.

## Verificação no navegador

- Desktop 1360×760 e mobile 320×740 sem overflow horizontal. Menu com quatro seções cabe em 320 px; rótulos inativos recolhem mantendo nomes acessíveis.
- Todos os links de navegação da área levam a funções `/admin`.
- Busca por Beta retorna um card; filtro ADMIN retorna dois na fixture de gestão.
- Diálogo nativo modal, largura 400 px; Tab permanece dentro dele, Escape fecha e devolve foco ao botão de edição.
- Dock: hover aplica escala 1,16 e deslocamento vertical de -8 px; Escape descarta tooltip. Indicador do menu com transição de 320 ms. Movimento reduzido elimina transições; desenho dos gráficos também respeita essa preferência.
- Gráficos e anéis com nomes acessíveis; tabelas expansíveis fornecem valores e horários das amostras.
- Períodos reais de 7/30/90 dias consultados por SELECT somente leitura; troca para 7 dias conferida na interface. Render usa o serviço de produção confirmado pelo responsável.

## Evidências locais

Pasta: `C:\Users\rafae\Documents\Projetos\_tmp\prep\admin-video-frames`.

- `reference-desktop.jpg`: referência extraída do vídeo.
- `admin-users-final.jpg`: comparação da gestão de contas.
- `admin-metrics-real-final.jpg`: métricas reais agregadas capturadas dos plugins.
- `admin-metrics-real-mobile.jpg`: mobile.

## Limites materiais

A prévia contém snapshots reais das métricas, sem atualização automática dos provedores; contas e atividade de gestão são fictícias e sinalizadas. Para operação contínua, revisar/aplicar a migração051 e configurar o acesso Render no backend conforme `docs/ADMIN-METRICS.md`. Uso de CPU e HTTP não retornaram amostras na consulta real; não foram preenchidos artificialmente. Não foi executada a função RPC com `service_role` após instalação, pois ela ainda não foi instalada.

Verificação: 733 testes API isolados, 52 frontend, build TypeScript/Vite e npm audit sem vulnerabilidades. Aviso de bundle principal acima de 500 kB permanece. `pip_audit` não está instalado no ambiente; nenhuma dependência Python foi adicionada.
