# Shopee Vídeo para afiliados — contrato de mídia, produtos e análises

**Apuração:** 07/11/2026. **Base:** `staging` SHA `5c238f3d3920f408ae0236fae7829d57bd267a39`. **Situação:** descoberta/documentação; gate SV.0 **não concluído**. Nenhum OAuth, endpoint, post ou leitura autenticada Shopee foi acionado.

## 1. Decisão que bloqueia a integração automática

O Auto Orbital é direcionado a **criadores e afiliados**. A Shopee Brasil documenta o feed **Shopee Vídeo no aplicativo móvel**. O console `open.shopee.com` é a **Shopee Open Platform**, que expõe uma família de APIs `v2.video.*` para *Video Management*. A mera presença no console e o uso de **Shopee Affiliate Open API GraphQL** **não comprovam** que este serviço esteja aprovado para publicar no feed de **criadores afiliados brasileiros**, em vez de vídeos geridos por **vendedores**. A API candidata é distinta da Affiliate GraphQL.

A captura de Rafa mostra um **lembrete genérico de ativação** da conta de desenvolvedor; não prova que existe App com Video Management, escopo concedido, OAuth autorizado ou elegibilidade do feed afiliado. As páginas Open Platform de referência retornaram **403 sem acesso** nesta apuração. O cliente `apis/shopee_video.py` permanece **isolado e bloqueado**; seus parâmetros ainda precisam de confirmação na documentação autorizada.

**Pergunta necessária:** o destino é o feed de **criador/afiliado** (com comissão) ou a área de **vídeos de uma loja vendedora**? Para desbloquear SV.0, verificar **App List → aplicativo → Serviços/Permissões**, categoria, região, status do serviço Video Management e se ele contempla **afiliados**. Encaminhar somente tela com nomes/estados, **ocultando Partner Key, token e dados pessoais**, ou resposta do suporte Shopee. Sem atalho por sessão pessoal, scraping ou falsa declaração empresarial.

## 2. Regras públicas para afiliados

| Elemento | Contrato confirmado e consequência no Auto Orbital |
| --- | --- |
| Vídeo | **3 a 60 segundos** segundo a ajuda Shopee Brasil; 30 segundos é recomendação. Codec, FPS, resolução, proporção, limite de bytes e upload de API exigem confirmação no serviço autorizado; validar mídia com o `ffprobe` existente. |
| Produtos | Até **seis produtos** associados **ao próprio vídeo**, não seis URLs de afiliado na descrição. O comprador escolhe os produtos vinculados pela função de produto no app. Associar depois de publicar não é permitido segundo a FAQ. |
| Descrição | Legenda/hashtags são texto editorial; URL de afiliado na legenda/comentários **não gera, por si só, atribuição de comissão no Shopee Vídeo**. O limite de legenda de 150 caracteres no cliente preliminar é hipótese de **um endpoint**, não regra universal do feed afiliado. |
| IDs | `products.id` é **ID interno** do Auto Orbital; `products.product_id` contém `itemId` **externo Shopee**; `commission_link` contém URL de afiliado. Nunca intercambiar. Caso a API exija `shop_id`/variação, consultar o contrato concedido. |
| Multiseleção | Hoje o `PostComposer` admite **um produto** nas redes existentes. A futura associação de até seis deve ser **exclusiva de Shopee Vídeo**, sem quebrar payload/IA/seleção dos demais. Reutilizar compositor, catálogo, mídia, scheduler e fila — sem criar um segundo motor. |
| Relevância | Somente produtos realmente mostrados, falados ou descritos. A Shopee pode remover vínculos irrelevantes; mais de **50%** deles pode excluir o vídeo e aplicar ponto na Saúde da Conta. Exigir revisão explícita de cada associação. |
| IA e direitos | Marcar conteúdo assistido por IA conforme regra da Shopee e `aigc_label` **quando disponível e aprovado**; licenças de música, imagens e vídeos pertencem ao usuário. |
| Comissão | Comunicado Shopee Brasil de **01/07/2026** reduziu a comissão padrão de Shopee Vídeo de **3% para 1,5%**; páginas antigas ainda citam 3%. Nunca fixar taxa ou inferir faturamento com base em visualizações. |

## 3. Implementação após o gate comercial/técnico

1. **SV.0 — permissão:** confirmar com Shopee que a conta/aplicativo tem serviço e escopo **para o feed afiliado brasileiro**, não só vendedor. Documentar categoria, país, sandbox e endpoints/limites **efetivamente disponíveis** no console autenticado.
2. **SV.1 — OAuth:** credencial de App/Partner ID/Key global **separada da Affiliate GraphQL**, cifrada e isolada por ambiente; cada criador autoriza seu próprio `user_id`, access/refresh token por `user_id + profile_id`. Validar `state`, callback, renovação, revogação e dois perfis/contas sem IDOR.
3. **SV.2 — mídia:** passar por sanitizador, `ffprobe` e transcodificação atuais. O pipeline global aceita **até 50 MiB**, inferior ao teto preliminar de 1 GiB do cliente Shopee. Não ampliá-lo arbitrariamente sobre Supabase Free. Se a API permitir: `init_video_upload` → partes/checksum → `complete_video_upload` → processamento → capas. Armazenar upload ID/estado por perfil de forma durável.
4. **SV.3 — edição:** usar associação estruturada de **1–6 `itemId`**, não `commission_link` na descrição; revisão de relevância antes de confirmar. Metadados, capa, agendamento e indicador de IA conforme contrato aprovado. O produto associado não será editável após publicação.
5. **SV.4 — publicação:** integrar `edit_video_info`/`post_video` somente com OAuth e filas persistentes atuais. Gravar `video_upload_id`, eventual `post_id`, estado, timestamps, conta/perfil e chave de idempotência. Resultado incerto → **unknown sem retry automático**; reconciliar individualmente antes de repetir. Primeiro post real apenas em conta de homologação com autorização de Rafa.
6. **SV.5 — análises:** investigar `get_video_list`, `get_video_detail`, `get_video_detail_performance` e tendências por vídeo **após** liberar documentação e validar retorno real. `get_overview_performance` é agregado: **não atribuir views de perfil a posts**. Reusar `publication_insights` e refresh 24h/5 min quando existir ID externo confirmado e dono validado; nenhuma consulta em outras contas.

## 4. Campos e origem para `/analytics`

| Indicador | Critério antes de mostrar valor |
| --- | --- |
| Envios concluídos, erros e incertos | `publish_jobs` confirmado **da rede Shopee Vídeo**, nunca apenas upload/transcodificação. |
| Visualizações, curtidas, comentários, compartilhamentos | Somente campo oficial **do vídeo individual** com `post_id` confirmado, unidade e autorização validadas. Até lá `—`, não `0`. |
| Cliques em produtos e associação | Se API de **vídeo individual** fornecer métricas e produtos reais com identidade; vínculo sem contagem não cria cliques fictícios. |
| Conversões, vendas e comissões | `conversionReport`/`validatedReport` da **Affiliate API** são outra origem, exigem conta/ID e acesso próprios. Mesmo conversão do canal “Shopee Vídeo” **não identifica automaticamente qual vídeo**. Exigir atribuição oficial por vídeo antes de somar receita a um post; comissão estimada não é liquidada. |
| Overview/demografia | Nunca somar dados gerais como se pertencessem a posts individuais. |

Regras existentes em `docs/ANALISE-REDES-COBERTURA-20261107.md`: guardar somente campos validados, fonte e timestamp, deduplicar IDs, separar `user_id/profile_id`, ausência `null`/traço e não executar refresh sem permissão. A rede segue **informativa** no filtro atual.

## 5. Lista de aceite

- [x] Ler código/contratos/estado do projeto e fontes Shopee Brasil.
- [x] Confirmar duração, associação de até seis produtos, relevância, comissão e bloqueios de analytics.
- [ ] SV.0: identificar se a conta é **afiliado ou vendedor** e validar serviço/API/escopo específico da Shopee em app autorizado.
- [ ] SV.1–SV.4: OAuth/segurança, mídia compatível, UI de até seis itens, fila idempotente, testes offline e homologação real consentida em staging.
- [ ] SV.5: leitura de resposta real de vídeo por ID, contrato de métricas, ownership, testes e integração ao filtro.
- [ ] CI, Render staging LIVE, QA desktop/mobile e autorização separada para `main`.

**SemVer:** apenas pesquisa e documentos; `VERSION=3.4.0` continua vigente. Sem mudanças no Supabase compartilhado, nos dois `pg_cron`, `pg_net`, filas, credenciais, publicações e produção.

## Fontes oficiais consultadas em 07/11/2026

- [Como criar e editar Shopee Vídeo](https://help.shopee.com.br/portal/10/article/165030) — vínculo em vídeo, até seis produtos e link de descrição sem atribuição.
- [Principais dúvidas Shopee Vídeo](https://help.shopee.com.br/portal/10/article/171162) — 3–60s, imutabilidade de produtos e fluxo no aplicativo.
- [Política de relevância](https://help.shopee.com.br/portal/10/article/191825) — correspondência de produto, links e penalidades.
- [Comissão Shopee Vídeo atualizada](https://help.shopee.com.br/portal/10/article/223989) — 1,5% desde 01/07/2026.
- [Como identificar o canal de pedidos](https://help.shopee.com.br/portal/10/article/163053) — canal no relatório, não ID inequívoco de vídeo.
- [Video Management — Open Platform](https://open.shopee.com/documents/v2/v2.video.post_video?module=129&type=1) — acesso 403 nesta pesquisa; conferir com permissão.
- [Shopee Affiliate Open API](https://affiliate.shopee.com.br/open_api/home) — catálogo/relatórios, **distinta da Open Platform Video Management**.
