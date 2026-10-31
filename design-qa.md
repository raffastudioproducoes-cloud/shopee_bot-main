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

## Refinamentos locais sem commit — etapa adicional

Cópia isolada `admin-refinement-local`, sem `.git`. A versão70805cd e seu servidor18765 permanecem preservados; refinamentos em18766.

Verificados no navegador: falha de atualização preserva3/0/2/1 dos cards; falha inicial oferece nova tentativa; provedores indisponíveis exibem quatro “Indisponível” e nenhum gráfico; comparação sintética mostra4cards e aviso de hoje incompleto. Em320×740, sem overflow horizontal, inclusive com comparação aberta. As evidências sintéticas são explicitamente sinalizadas.

Históricos de gráfico usam Brasília, assim como as tabelas. A projeção de logs remove identidades e texto livre; o novo status de conexões omite mensagens de provedores e usa cache próprio.

Banco descartável: teste com PostgreSQL/PGlite0.5.10 passou migração/reaplicação, ACL/RLS, agregados, fronteiras7/30/90, exclusão de amostras futuras e rollback. Suite API737passou; após ajuste final da projeção,3testes focados de privacidade passaram. Frontend54passou, build e npm audit0. Nenhuma ativação de rastreamento nem alteração de produção.

## Correção solicitada pelo usuário: navegação única
Removidos trilho lateral, dock inferior e atalhos/tabs repetidos da central. Navegação mantida somente no cabeçalho, com os quatro destinos e indicador animado. Grade ajustada para conteúdo+central no desktop e uma coluna em telas menores. Sem commit/push.
# Controle de escala — revisão local 15/10/2026

Novos widgets em grade dupla no desktop e coluna única no celular: anéis CPU/RAM, indicadores de qualidade, saúde do Postgres, eventos de publicação, retorno semanal, consumo e evolução do banco. Referências do GIF/vídeo mantidas no shell superior, anéis e curvas; cores e fontes vêm dos tokens existentes. Nenhum menu duplicado.

Contraste dos números SVG corrigido para --text-display; animação usa keyframe existente/próprio e respeita prefers-reduced-motion. Dados sem fonte aparecem indisponíveis, Render antigo permanece marcado como antigo, e snapshot de banco/clientes informa horário próprio.

Conferência em 1360x900 e 390x844: grade responsiva, navs=1, scrollWidth=clientWidth=375 no conteúdo móvel. Provas .tmp/proofs/scale-desktop.jpg e .tmp/proofs/scale-mobile.jpg. Não foi acrescentado mapa ou dado geográfico fictício.

# Globo — referências HUD/Seedtag

Globo esférico rotacionável, continentes reais amostrados em pontos, aro atmosférico ciano e linhas de latitude/longitude. Sem textura externa, nova fonte ou mudança de paleta. As luzes ciano/cinza/vermelhas têm rótulos textuais correspondentes. Zoom regional e foco em RJ funcionam por controles acessíveis e seleção equivalente fora do SVG. Labels de região aparecem apenas na seleção para não sobrepor RJ/SP/MG.

Modo real vazio e demonstração opt-in verificados. Botões de zoom anunciam nomes completos e toggle anuncia estado pressionado após correção no componente Button. Movimento reduzido desativa pulsação. Arraste e teclado alteram a geometria observada; zoom e seleção atualizam as contagens e centralização. Celular: scrollWidth=clientWidth=375.



---

# QA visual — criação de posts com IA e threads (2026-10-31)

- Referência: imagem do usuário `image(20261031-051311).png`, 1023 × 684 px (área do modal de posts).
- Implementação: `https://shopee-bot-staging.onrender.com/posts`, commit de homologação `c7498f14d96533f90963cb93ef58c6b0c5650c6e`.
- Estado de comparação: modal Novo post com 3+ partes, seletor de redes e prévia aberta.
- Captura do modal implementado: **indisponível** — navegação redireciona a `/login` sem sessão autenticada.
- Viewport/densidade da implementação no estado alvo: não obtidos. Comparação lado a lado e recortes focados: não realizados.

**[P1] Bloqueio de QA visual:** a autenticação impede verificar, no navegador, os botões compactos, a sequência de textos por IA, o overflow, a responsividade e a navegação por teclado. As cinco superfícies obrigatórias — tipografia, espaçamento, cores, logos/imagens e textos — permanecem não comparadas no estado necessário. Não há base para afirmar equivalência visual.

**Verificações independentes realizadas:** TypeScript/Vite passou no CI; testes Python cobrem geração de 1–10 partes, extensão com contexto, conservação de texto manual, limite de API e filtragem por rede; `staging` fez build e entrou em produção de homologação. Nenhuma publicação real foi disparada nas contas sociais.

**Pendente para aprovar:** sessão autenticada em `staging`, capturas 360/768/1280 px do modal, teste de criar e expandir partes, inspeção do console, comparação com a referência e novo registro dos resultados.

**final result: blocked**
