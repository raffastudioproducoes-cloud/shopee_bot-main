# Campanhas: redes globais, descrições por rede e paginação

Versão-alvo: 3.8.0
Data: 08/11/2026

> Complemento 09/11/2026: consumo de dias efetivos por weekdays, limite dinâmico e ativação sem salvamento manual estão documentados em [CAMPANHA-DIAS-EFETIVOS-E-ATIVACAO-20261109.md](CAMPANHA-DIAS-EFETIVOS-E-ATIVACAO-20261109.md). Migration 095 autorizada para staging, ainda não aplicada; implantação depende de CI e revisão final.
Branch: feat/campaign-global-networks-paged-adaptation
Base: staging 3.7.0

## Interface

A seleção das redes fica uma única vez, como a lista de checkboxes já existente (NetworkPicker), imediatamente abaixo do nome da campanha e antes da seleção/lista de produtos. Sem modal, ícones ou seletor de lojas. Preservar os canais de postagem já existentes.

## Compatibilidade

O contrato atual guarda networks em cada item. Para evitar migração de banco e preservar compatibilidade com o worker, a interface mantém a seleção em CampaignDraft.networks e serializa o mesmo conjunto em todos os itens ao salvar. network_copies continua por produto/rede.

Rascunhos legados com conjuntos divergentes são carregados com a interseção dos conjuntos antigos. Isso evita ativar uma rede que não estava marcada para todos os produtos. A interface apresenta aviso para revisão antes de salvar. Não executar união automática nem ativar destinos novos silenciosamente.

## Descrições

Uma única área visual contém abas textuais das redes selecionadas. Cada aba mostra network_copies[network] e, quando ausente, usa copy como descrição padrão. Editar uma aba altera somente a variante daquela rede. O botão de IA preenche a variante ativa. O texto-base do produto permanece no snapshot da campanha; nada grava em Produtos.

## Paginação

Renderizar no máximo 10 produtos por vez. O total de produtos e a ordem permanecem intactos. Navegação por números e setas anterior/próxima. O estado de edição permanece em itemSnapshots, independente da página exibida.

## Regras e validação

A publicação única já utiliza planMediaComposition no frontend e plan_network_composition no backend. O plano por rede mantém somente mídia compatível, preserva a ordem, reporta cada arquivo descartado, bloqueia texto acima do limite em vez de truncar, bloqueia rede que exige mídia quando não há mídia aceita e executa validação autoritativa no servidor antes do envio.

Não alterar arquivos originais de Produtos. Não comprimir, cortar ou reescrever mídia/texto automaticamente sem autorização. A composição por campanha continua respeitando network_copies e copy como fallback.

## Shopee Vídeo e TikTok

Shopee Vídeo: duração oficial de 3 a 60 s; até 6 produtos vinculados diretamente ao vídeo; publicação pelo app Shopee. O Auto Orbital ainda não tem motor de upload/publicação para esse destino. Não listar como opção ativa nem inferir limite não publicado.

TikTok: API oficial suporta PHOTO, mas o fluxo do Auto Orbital permanece somente vídeo até implementar Creator Info/privacidade, consentimento e domínio/prefixo verificado para PULL_FROM_URL. A ajuda separa limites oficiais da API e capacidade efetiva do aplicativo.

## Testes de aceitação

1. 22 produtos em páginas 10 + 10 + 2.
2. Navegação sem perder edição, descrição, mídia ou ordem.
3. Seleção de redes uma vez, antes dos produtos, sem modal e sem lojas.
4. Seleção global refletida no payload salvo.
5. Abas usam a descrição padrão como fallback inicial.
6. Edição e IA alteram apenas a variante ativa.
7. Produtos cadastrados permanecem intactos.
8. Rascunho antigo com redes divergentes mostra aviso e usa interseção conservadora.
9. Publicação única mantém composição por rede e validação no backend.
10. Nenhum teste dispara publicação real.

CI e testes do projeto devem validar o branch antes de merge. QA visual/autenticada em staging permanece necessária. Não houve promoção para produção.

## Complemento 09/11/2026 — auditoria e correção do publicador TikTok

A inspeção do publicador antigo encontrou dois problemas: o upload enviava o arquivo inteiro em um único bloco, embora a API exija chunking para arquivos maiores; e o publicador não consultava o limite individual de duração da conta.

Correção preparada em branch separada:
- consulta Creator Info antes de iniciar o upload;
- exige que SELF_ONLY esteja entre as opções de privacidade da conta;
- mede a duração real com ffprobe e bloqueia vídeo acima de max_video_post_duration_sec;
- divide o arquivo em chunks sequenciais de até 64 MB, com Content-Range e resposta 206 para blocos intermediários, aceitando até 4 GB;
- não envia o arquivo inteiro para memória.

A capacidade PHOTO permanece fora do escopo ativo: API oferece PHOTO, mas o aplicativo ainda não implementa o fluxo de consentimento/privacidade e URL verificada.

## Complemento 09/11/2026 — prévia de composição por rede

A edição da campanha agora apresenta, dentro do seletor de mídias de cada produto, uma prévia para cada rede selecionada. Ela usa o mesmo planejador de composição da publicação única e mostra o modo de envio, mídias descartadas e o motivo (formato, tipo, quantidade ou tamanho), além de bloquear textos acima do limite sem truncá-los. O link afiliado entra na contagem.

A prévia inclui mídias salvas em Produtos e anexos legados do rascunho. O navegador lê dimensões de imagens e duração/dimensões de vídeos pelos URLs assinados da galeria; quando não consegue ler, sinaliza que esses metadados não entraram na prévia. A foto Shopee é baixada pela rota autenticada já existente para obter o tamanho sanitizado real. Na ativação, o backend também baixa/sanitiza a imagem uma única vez e usa os bytes reais na validação por destino antes de reter a cópia privada. O original do Produto não é alterado.

A validação de duração individual do TikTok continua sendo dinâmica: Creator Info é consultado antes do upload externo e o vídeo é bloqueado se exceder o limite retornado para a conta. Nenhum teste dispara publicação externa.

## Fechamento técnico em staging — 08/11/2026 BRT

PR #378, #379 e #381 integradas em `staging`; PR #380 foi fechada sem merge e substituída pela #381 para obter uma execução independente da CI. SHA final `393494720f3d1469838c3384d3677d5810129ca4`; `VERSION=3.8.0`.

A PR #381 completa o preflight do editor de campanhas:
- preview por rede com o mesmo planejador de composição da publicação única;
- lista mídias aceitas, descartadas e seus motivos; bloqueia texto fora do limite;
- inclui link afiliado na contagem;
- lê dimensões de imagens e duração/dimensões de vídeos salvos;
- obtém o tamanho sanitizado da foto Shopee pela rota autenticada e o backend reutiliza a mesma cópia sanitizada na validação por destino;
- mantém os arquivos originais de Produtos intactos;
- posiciona as abas abaixo da caixa de descrição e antes dos controles de IA.

Validação: CI da PR #381 #42552686633 SUCCESS; CI push staging #42552858249 SUCCESS (1.323 API, 208 scheduler, 9 SemVer, frontend build/tsc, F4E/SQL e segurança). Render staging `dep-dboj8gq9lscs73d3if60` **LIVE** no SHA final. Smoke pós-deploy #42552858259 SUCCESS: health e security headers, CSP estrita, sessão anônima negada e login legado 410; teste autenticado foi SKIP por ausência de credenciais. ZAP #42552858557 SUCCESS: 63 PASS, 0 FAIL e 5 WARN de baixa prioridade para revisão (cache-control, non-storable content, CSP wildcard, modern web app e COEP).

O workflow CD #42552858268 ignorou o hook do GitHub por ausência de `RENDER_STAGING_DEPLOY_HOOK_URL`, mas o Render fez deploy automático (`autoDeploy=yes`). Produção segue 3.7.0; sem merge em `main`, sem publicação externa real e sem alterações de schema/crons/gateway. QA visual/autenticada por Rafa ainda pendente.

## Promoção da 3.8.0 para produção — 09/11/2026 BRT

Rafa aprovou a promoção após homologação em staging. PR [#382](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/382) integrada por squash em main, SHA `5a283baf8aafb843cdb6b576836c0b73ae682784`. VERSION=3.8.0, classificação MINOR 3.7.0→3.8.0. CI da PR #42554019553 e SemVer #42554019572 SUCCESS; CI push main #42554207935 SUCCESS: 1.323 API, 208 scheduler (1 xfailed), 9 SemVer, 34 web/proxy, frontend TypeScript/build e F4E/PostgreSQL.

Render produção shopee-bot (srv-da6vrla6iojc7380a13g) deploy `dep-dbojfpcs728c73a9lufg` **LIVE no SHA de merge**. O serviço tem autoDeploy=yes; CD GitHub #42554322842 terminou SUCCESS, mas ignorou o hook `RENDER_DEPLOY_HOOK_URL` ausente. O deploy foi confirmado diretamente no Render. Logs indicam aplicação e scheduler iniciados e migrações 001–094 já aplicadas; nenhuma migration nova, mudança de schema, cron, gateway, segredo ou postagem real.

**Limites de verificação:** não foi possível executar smoke HTTP externo health/readiness/login nesta sessão; não afirmar 200 nem ausência de 5xx. O intervalo consultado não retornou registros de request. QA autenticada/visual e publicação social real permanecem pendentes. CI registrou warning Pydantic de `CampaignDraftItem.copy` sombreando `BaseModel`, além de warnings de chave JWT usada nos testes e depreciações; manter follow-up técnico.

Registro consolidado: [RELEASE-3.8.0-20261109.md](RELEASE-3.8.0-20261109.md).
