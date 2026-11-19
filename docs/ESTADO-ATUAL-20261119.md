# Estado atual do Auto Orbital — 19/11/2026

Este documento é um resumo curto, escrito em 19/11/2026 (release `3.27.0`), que aponta para os documentos detalhados. Ele não substitui o `CHANGELOG.md`, o `docs/TASK.md` nem o Guia Mestre. Quando algo aqui disser "a confirmar", significa que o fato foi informado por Rafa na sessão de sincronização de 19/11/2026, mas não existe prova registrada no CHANGELOG, no código ou nos documentos do repositório. Nenhuma senha, chave, token, `partner_key` ou login de conta de teste é registrado aqui; quando for preciso citar esses itens, citamos só o nome da variável ou o lugar onde ficam.

## 1. Versões e releases

- Staging e produção estão na versão `3.27.0` (publicada em 18/11/2026; o cabeçalho do CHANGELOG usa a data 2026-11-19).
- O `CHANGELOG.md` tem seção datada para todas as versões de `3.17.0` a `3.27.0`: 3.17.0, 3.18.0, 3.19.0, 3.20.0, 3.20.1, 3.21.0, 3.22.0, 3.23.0, 3.23.1, 3.24.0, 3.24.1, 3.25.0, 3.26.0 e 3.27.0. O gate SemVer (`scripts/check_release_semver.py`) só exige a seção da versão que está sendo promovida e o bloco `[Não lançado]`; ambos existem. Nenhuma lacuna encontrada no CHANGELOG.
- Documentos `docs/RELEASE-x.y.z-*.md` existem apenas para 3.3.0, 3.4.0, 3.5.0, 3.6.0, 3.6.1, 3.6.2, 3.7.0, 3.8.0, 3.8.1, 3.9.0, 3.10.0 e 3.16.0. Não há um padrão obrigatório de criar um por versão (nenhum gate ou teste exige); as versões 3.11.0 a 3.15.0 e 3.17.0 a 3.27.0 ficam registradas só no CHANGELOG. Não foram criados documentos de release novos.
- Resumo da 3.27.0 (detalhes no [CHANGELOG](../CHANGELOG.md)): Reels no Facebook (`post_reel_as_page`, fluxo start, upload, finish) e no Instagram (`media_type=REELS`, `share_to_feed=true`); painel "Publicar como Reels" no Criar Post; a escolha do Facebook é guardada como `{"reels": true}` em `posts.tiktok_options` (a mesma coluna jsonb da migração 104, sem coluna nova); insights de vídeo e Reels do Facebook; reposts e tempo médio de visualização no Instagram; cliques do Facebook em posts só de produto passam pelo redirecionador `/r/{token}`. Sem migração.

## 2. Migrations recentes

- `103_publication_insights_reach_saves.sql`: colunas aditivas `reach` e `saves` em `publication_insights` (insights de Instagram e Facebook). Documentada no CHANGELOG 3.23.0 e no `docs/TASK.md` (seção de 14/11/2026).
- `104_posts_tiktok_options.sql`: coluna jsonb anulável `posts.tiktok_options` (opções do TikTok com consentimento e, desde a 3.27.0, a escolha de Reels do Facebook). Documentada no CHANGELOG 3.25.0.
- As migrations rodam no boot do deploy; que as duas já constam em `public.migrations` do banco compartilhado: a confirmar (não há registro escrito dessa conferência).
- Não existe outra lista de migrations nos documentos vivos além do CHANGELOG e dos documentos de release/tarefa; por isso nada mais foi atualizado.

## 3. Estado das redes e das análises

| Item | Estado | Fonte |
| --- | --- | --- |
| Facebook, Instagram, Threads e TikTok | Funcionando em produção desde 14/11/2026 (TikTok só com conta privada enquanto o app não for auditado) | CHANGELOG 3.22.0, `docs/TASK.md` |
| X (Twitter) | Reativado como rede publicável (3.22.0). OAuth reconectado informado por Rafa em 19/11/2026; registro de prova no repositório: a confirmar | CHANGELOG 3.22.0 |
| Coleta de insights de Instagram, Facebook e Threads | Funcionando segundo Rafa; código e testes na 3.23.0, 3.24.0, 3.26.0 e 3.27.0. Validação contra a API real registrada no repositório: a confirmar | CHANGELOG |
| Estados de métrica | `ok`, `permission_required`, `access_denied`, `no_data` e `audience_below_minimum` (Página com menos de 100 curtidas) existem no código (`api/meta_post_insights.py`); `token_expired` e `not_found` também existem | código, CHANGELOG 3.23.0, 3.24.0 e 3.26.0 |
| TikTok em análise | App em análise pelo TikTok. Escopos `user.info.basic`, `video.publish` e `video.upload` (variável `TIKTOK_PERMISSIONS`, padrão no código). Arquivo de verificação do prefixo de URL servido na raiz (3.24.1). Painel de compartilhamento de conteúdo (Content Sharing Guidelines) e modo rascunho (3.25.0). Credenciais de produção já devolvidas: a confirmar (informado por Rafa) | CHANGELOG 3.24.1 e 3.25.0 |
| Asaas | Código de cobrança desde a 3.16.0; na 3.26.0 a contratação só abre com chave, token do webhook e ambiente coerentes. Asaas em produção (`ASAAS_API_URL` apontando para `https://api.asaas.com/v3`, webhook registrado e `ACCOUNT_ERASURE_ENABLED=true`) foi informado por Rafa: a confirmar nos documentos, pois o texto de 3.16.0 ainda diz "contratação desligada em produção" | CHANGELOG 3.26.0, `docs/RELEASE-3.16.0-20261112.md` |
| Upload de vídeo com 504 | Corrigido na 3.26.0: prazo de 180 s no proxy para as três rotas de upload de mídia e FFmpeg com H.264 limitado a 1 thread | CHANGELOG 3.26.0 |
| Identificação da empresa | Razão social, nome fantasia, CNPJ e endereço (sem CPF) nos Termos, na Privacidade (português e inglês) e no rodapé da landing | CHANGELOG 3.25.0 e 3.26.0 |

## 4. Meta App Review

- Business Verification da Raffa Studio Produções: **verificada** (informado por Rafa; sem registro anterior no repositório).
- Análise do app **enviada em 18/11/2026** com 11 permissões: `threads_basic`, `threads_content_publish`, `threads_manage_insights`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `read_insights` e `public_profile`.
- Status em 19/11/2026: "Análise em andamento", prazo informado de até 20 dias. Vídeos de demonstração de Threads e Instagram foram enviados. As instruções de teste foram atualizadas e apontam para `https://shopee-bot-fj0w.onrender.com`; a conta de teste usada tem o acesso informado diretamente no campo da Meta, e **login e senha não são documentados**.
- Os textos usados (instruções de teste em inglês e uma justificativa curta por permissão) estão no arquivo de Rafa `META-REVIEW-TEXTOS-2026-11-18.md`, fora do repositório. Ele também prevê acrescentar, depois do ar da release de Reels, uma frase sobre vídeos publicados como Reels em `instagram_content_publish` e `pages_manage_posts`; como a análise já foi enviada, isso só deve ser feito se a Meta pedir ou depois da decisão, nunca durante a revisão sem decisão de Rafa.
- **Regra durante a análise:** não alterar casos de uso, permissões nem as conexões de Facebook, Instagram e Threads do app.
- Pendência futura: trocar a senha da conta de teste depois da revisão (dono: Rafa).

## 5. Shopee Vídeo

Estado real (verificado no código desta árvore): OAuth de afiliado com `auth_type=user`; cliente de upload e postagem em `apis/shopee_video.py`; rotas `/shopee-video/*` e `/admin/shopee-video` em `api/routers/shopee_video.py`; migration 091 com as tabelas `platform_shopee_video_apps` e `shopee_video_authorizations`; cartão em Credenciais. A publicação continua **desligada**: `publishing_enabled` é fixo em `False` na rota de status e não existe rotina em `scheduler/` que publique vídeo na Shopee. A guarda `campaign_dispatch_guard` (`database/campaign_dispatch_guard.py`) é a trava de despacho de campanhas e está citada por Rafa como parte do bloqueio; ela não é específica do Shopee Vídeo.

Aplicativo e console (informado por Rafa; o número do app já constava em `docs/SHOPEE-VIDEO-OAUTH-AFILIADOS-20261107.md`):

- App "Auto Orbital" (id 249826, categoria Shopee Video Management) **enviado para Go Live em 18/11/2026 às 22:56**, no console `https://open.shopee.com/console/app/249826`. Status "em análise"; resultado por e-mail em até 24 horas. Test Partner_id 1252254 (a partner key não é documentada).
- Declarações enviadas: domínio de redirecionamento de produção `https://shopee-bot-fj0w.onrender.com`; dados de comprador (PII) desligado.
- IPs declarados. Servidores de banco: os IPs de `aws-0-us-east-1.pooler.supabase.com` (52.45.94.125, 44.208.221.186 e 44.216.29.125), que ficam atrás de um balanceador da AWS e podem mudar. Demais servidores: faixas de saída compartilhadas da Render em Virgínia (74.220.49.0/24 e 74.220.57.0/24), que também podem mudar; a fonte é Render Dashboard, serviço shopee-bot, Connect, Outbound.
- Variável na Render (staging e produção, já configurada): `SHOPEE_VIDEO_CALLBACK_URL` terminando em `/api/shopee-video/callback`. `partner_id` e `partner_key` **não** vão na Render: o admin os salva em `/admin/credentials`.
- Correção de entendimento: documentos de 15/10 diziam que o Shopee Vídeo era "inviável/bloqueado" porque a API de Afiliados não tem endpoint de vídeo. Isso está desatualizado. A Shopee Open Platform (`open.shopee.com`, famílias `v2.media.*` e `v2.video.*`, guia oficial `https://open.shopee.com/developer-guide/706`) tem API de vídeo para o papel de afiliado. Os trechos antigos receberam nota de revisão datada.

Pendências técnicas conhecidas (nada disto está feito):

1. Hosts diferentes: `apis/shopee_video.py` usa `https://partner.shopeemobile.com` e `api/shopee_video_oauth.py` usa `https://openplatform.shopee.com.br`; alinhar com a documentação oficial.
2. A lista de caminhos permitidos do cliente não inclui `get_video_list`, `get_video_detail`, `delete_video` nem os caminhos de desempenho.
3. Não há polling de resultado nem renovação automática (refresh) de tokens; hoje o refresh é manual (`POST /shopee-video/refresh`).
4. `shopee_video` não está em `NETWORK_RULES` (`api/network_limits.py`), portanto não tem limites de texto, mídia e produtos por rede.
5. A regra de 1 produto vale hoje para todas as redes e deve virar limite por rede (6 só no Shopee Vídeo).
6. O teste `tests/api/test_security_release_contract_20261031.py::test_shopee_video_not_registered_as_live_api_endpoint` afirma que nenhuma rota começa com `/shopee-video`, mas `api/main.py` inclui o roteador `shopee_video`, cujas rotas começam com `/shopee-video`. A verificar (não foi possível rodar a suíte nesta sessão; falta o pacote `flask` no ambiente local). Se o teste falhar, ele é que está desatualizado.

**Decisão de produto de Rafa (plano, não está feito):** o lote de post passa a ter uma lista de produtos e cada rede recebe só o que aceita; o Shopee Vídeo aceita até 6 produtos vinculados (`MAX_LINKED_PRODUCTS = 6` já existe no cliente) e as demais redes aceitam 1.

## 6. Fluxo entre staging e produção

- Mudanças entram por PR na `staging` com **merge commit**. Release: um PR que sobe `VERSION` e `CHANGELOG.md` (um passo SemVer). Promoção: PR `staging` para `main` com **merge commit, nunca squash** (squash diverge o histórico e o gate SemVer deixa de funcionar bem; ver PR #396).
- Depois de cada release, `staging` e `main` devem ter a **mesma árvore e o mesmo `VERSION`**. A `main` ganha commits de merge extras; isso é esperado e não é divergência.
- Em 19/11/2026 ambas estavam em `3.27.0` com árvore idêntica: staging `25c0c8c6` e main `0c58a350`.
- A cópia local antiga do projeto (pasta `ShopeeAutoVendas-local/repo`) estava **1322 commits atrás** e foi alinhada. As edições de documentação locais que não tinham sido commitadas foram salvas em `C:\Users\rafae\Documents\Projetos\ShopeeAutoVendas-local\local-private\backup-docs-locais-20261119\docs-locais-nao-commitados.patch` (fora do repositório) e as decisões de 16/10/2026 foram integradas manualmente nesta atualização (ver `docs/ROADMAP-MVP.md`, `docs/TASK.md` e `docs/superpowers/plans/2026-10-13-escalabilidade-futura.md`).
- A regra de fluxo de 10/11/2026 (tudo entra primeiro na staging, inclusive variáveis e configuração) continua em vigor; está no topo do `AGENTS.md`.

## 7. Pendências abertas e donos

| Pendência | Dono |
| --- | --- |
| Resultado da análise do app na Meta (até 20 dias); não mexer em permissões, casos de uso e conexões durante a análise | Rafa |
| Trocar a senha da conta de teste da Meta depois da revisão | Rafa |
| Resultado da análise do TikTok e conta privada até a auditoria | Rafa (TikTok) |
| Resultado do Go Live do app Shopee 249826 (e-mail em até 24 h) e conferir se os IPs declarados ainda valem | Rafa |
| Confirmar no Render e no painel Asaas o estado de produção (`ASAAS_API_URL`, webhook, `ACCOUNT_ERASURE_ENABLED`) e registrar nos documentos | Rafa, com apoio do agente |
| Alinhar hosts do Shopee Vídeo, ampliar a lista de caminhos, polling e refresh, incluir `shopee_video` em `NETWORK_RULES` | Engenharia (agente), com decisão de Rafa para ligar a publicação |
| Limite de produtos por rede (lista de produtos no lote; 6 no Shopee Vídeo, 1 nas demais) | Engenharia (agente), decisão de produto já tomada por Rafa |
| Revisar o teste de contrato de 31/10 que proíbe rotas `/shopee-video` | Engenharia (agente) |
| Conferir se as migrations 103 e 104 constam em `public.migrations` do banco compartilhado | Engenharia (agente) |
| Pentest, reteste dos 54 alertas e relatório para a Shopee (ver `docs/TASK.md`) | Rafa decide; execução pelo agente |

## 8. Onde ler mais

- Releases e histórico: [CHANGELOG](../CHANGELOG.md) e `docs/RELEASE-*.md`.
- Tarefas vivas: [TASK](TASK.md). Estado resumido: [MEMORY](MEMORY.md). Regras para IAs: [AGENTS](../AGENTS.md) e [Guia Mestre](GUIA-MESTRE-IA.md).
- Análises de redes: [ANALISE-REDES-PLANO](ANALISE-REDES-PLANO.md) e [ANALISE-REDES-COBERTURA-20261107](ANALISE-REDES-COBERTURA-20261107.md).
- Pagamentos: [PAGAMENTOS-ASAAS-PLANO-20261110](PAGAMENTOS-ASAAS-PLANO-20261110.md) e [RELEASE-3.16.0-20261112](RELEASE-3.16.0-20261112.md).
- Shopee Vídeo: [OAuth de afiliados](SHOPEE-VIDEO-OAUTH-AFILIADOS-20261107.md), [gate](SHOPEE-VIDEO-AFILIADOS-GATE-20261107.md), [validação](SHOPEE-VIDEO-VALIDACAO.md) e [cadastro Open Platform](SHOPEE-OPEN-PLATFORM-CADASTRO-20261107.md).
- Roadmap e handoff históricos: [ROADMAP-MVP](ROADMAP-MVP.md) e [HANDOFF-2026-10-15](HANDOFF-2026-10-15.md).
