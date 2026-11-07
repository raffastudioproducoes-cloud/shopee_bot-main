# Shopee Vídeo — OAuth de criadores afiliados (07/11/2026)

**Status:** código preparado na branch `feat/shopee-video-oauth-afiliados-20261107` para PR em `staging`; nenhum post de vídeo real foi enviado. **Versão:** `3.4.0` em `VERSION`, mudança MINOR candidata a `3.5.0` somente na release aprovada para `main`.

## Fonte oficial e distinções

- [Shopee Video API Integration Guide](https://open.shopee.com/developer-guide/706): a categoria **Shopee Video Management** cobre vendedores **e criadores afiliados**. Para afiliados, autorização `auth_type=user`, APIs do tipo `User` e `user_id` em vez de `shop_id`.
- [v2.public.refresh_access_token](https://open.shopee.com/documents/v2/v2.public.refresh_access_token?module=104&type=1): acesso de aproximadamente quatro horas, refresh de aproximadamente trinta dias, refresh token de uso único com rotação.
- [v2.video.edit_video_info](https://open.shopee.com/documents/v2/v2.video.edit_video_info?module=129&type=1), [v2.video.post_video](https://open.shopee.com/documents/v2/v2.video.post_video?module=129&type=1) e [v2.media.init_video_upload](https://open.shopee.com/documents/v2/v2.media.init_video_upload?module=130&type=1) definem a futura etapa de upload/edição/publicação. Ela **não está implementada** nesta entrega.
- A integração da **Shopee Affiliate GraphQL** para catálogo e links permanece separada e sem modificação.

## Implementação desta etapa

1. Migration aditiva `091_shopee_video_oauth_affiliates.sql`: duas tabelas, chave da aplicação separada por `environment` e tokens por `user_id` + `profile_id` + `environment`, criptografados, RLS e acesso exclusivo pelo backend service role. **Não aplicar antes do gate de rollout no Supabase compartilhado.**
2. ADMIN em `/admin/credentials` registra Partner ID/Key da aplicação Shopee Video Management. Os valores não são expostos ao frontend após salvar; o backend mantém a chave cifrada.
3. `/credentials` oferece consentimento para o perfil ativo, chama `/shopee-video/authorize`, passa por OAuth com `state` assinado e cookie `HttpOnly`/`Secure`, e salva apenas depois do retorno de `/shopee-video/callback` validado. O domínio do callback é **fixado no servidor**.
4. `/shopee-video/status`, `/shopee-video/refresh` e `DELETE /shopee-video/authorization` usam o escopo do perfil. A renovação gira ambos os tokens; a identidade de afiliado permanece do lado do servidor.
5. `POST /shopee-video/preview` aceita metadados (legenda, duração, tamanho, IDs de produtos do perfil e marcação de conteúdo de IA). **Não envia o arquivo ou publica na Shopee** e não cria jobs.

## Gate de configuração e testes

- Shopee Console: aplicação `249826` categorizada como `Shopee Video Management`, ainda em **Developing** na última observação. `Test Partner ID` difere do ID da aplicação. Não confundir com credenciais da API Shopee Afiliados. Go Live/permissões finais ainda exigem homologação da plataforma.
- Host staging: `SHOPEE_VIDEO_CALLBACK_URL=https://shopee-bot-staging.onrender.com/api/shopee-video/callback` e domínio registrado/aceito na Shopee. Host produção: `https://shopee-bot-fj0w.onrender.com/api/shopee-video/callback` com configuração e credencial específicas de `production`. **Nunca usar callback de outro host:** o cookie de CSRF não acompanha a mudança de domínio.
- Executar CI com testes API (`tests/api/test_shopee_video_oauth.py`), build/contratos frontend e schema SQL. Testar conexão com conta de afiliado autorizada, renovação e isolamento por perfil sem realizar publicação externa.
- Registrar evidências do PR, checks da CI e deploy Render staging; comprovar esquema aditivo com migration em janela segura para banco compartilhado, preservando `main`/crons/`pg_net`/filas.
- O próximo incremento funcional deverá implementar upload multipart durável, processamento, capa, vínculo de até 6 produtos, `aigc_label`, publicação idempotente, conciliação de resultados e limites/rate limits **antes de habilitar `publishing_enabled`**.

## Situação de release

`staging` é homologação. **Não promover para `main` nem incrementar `VERSION` antes de autorização posterior de Rafa**. A documentação de aceite e estados no Vault deve registrar os checks efetivamente obtidos; não presumir que API test sandbox implica postagem de afiliado em produção.
