# Migração de autenticação — Supabase Auth (e-mail e Google)

> **Estado:** preparação em `feature/supabase-auth-email-google`; NÃO foi ativado em produção.
> Preservar as duas contas legadas em `public.users`. Não associar IDs de Auth ou mesclar contas sem nova autorização de Rafa.
> Staging e produção compartilham o mesmo projeto Supabase: qualquer criação de conta ou migration na staging é real nesse banco.

## Objetivo e fronteira

- O Supabase Auth verifica senhas de contas novas e a identidade retornada pelo Google.
- `public.users.id` continua sendo o ID interno do Auto Orbital para produtos, perfis e publicações.
- `public.users.supabase_auth_user_id` associa a identidade `auth.users.id` à conta interna. Não vincular pelo e-mail de perfil, nome ou coincidência de username.
- A sessão JWT interna `access_token` ainda é **ponte transitória** para os routers existentes e NÃO representa a migração completa de sessão. Não declarar o Render fora da autenticação até substituir essa dependência e migrar settings, troca de perfil, sessões e revogação.
- `api/routers/auth.py` mantém o código legado apenas enquanto a flag está desligada. Quando Supabase Auth é ativado, login, cadastro e troca de senha legados respondem 410. Não ativar na produção antes da vinculação dos administradores.
- Cadastro por e-mail fica em `pending_auth_registrations` até a confirmação da caixa postal. O primeiro login validado provisiona `public.users` (USER), o perfil principal e credenciais vazias. Google possui onboarding próprio.

## Passo a passo para o proprietário — não compartilhar chaves no chat

### 1. Google Cloud

1. Abra [Google Auth Platform](https://console.cloud.google.com/auth/overview) e selecione/crie o projeto do Auto Orbital.
2. Em **Branding**, configure nome Auto Orbital, domínio legítimo, contato e política de privacidade. Em **Audience**, escolha tipo externo; em Teste adicione somente usuários autorizados. Para todos os usuários depois, publique o OAuth em produção quando os requisitos Google estiverem atendidos.
3. Em **Data Access**, use apenas `openid`, `userinfo.email`, `userinfo.profile`. Não peça Gmail, Drive ou outros escopos.
4. Em **Clients**, crie **OAuth client ID → Web application**.
5. Em **Authorized JavaScript origins**, adicione as origens reais do site, sem paths:
   - `https://shopee-bot-staging.onrender.com`
   - `https://shopee-bot-fj0w.onrender.com`
6. Em **Authorized redirect URIs**, cole **exatamente** a URL de callback exibida no provedor Google do Supabase. No endpoint padrão do projeto deve ser `https://wcentenooirmwwlwlljp.supabase.co/auth/v1/callback`, mas confirme no painel antes de salvar.
7. Guarde Client ID e Client Secret no Google/Supabase, nunca em GitHub, log ou mensagem.

### 2. Painel Supabase

1. Projeto `wcentenooirmwwlwlljp` → **Authentication → Sign In / Providers → Google**: habilite e forneça Client ID/Secret do Google.
2. **Authentication → URL Configuration**:
   - Site URL de produção: `https://shopee-bot-fj0w.onrender.com`.
   - Redirect URLs autorizadas (sem wildcard amplo):
     - `https://shopee-bot-staging.onrender.com/api/auth/supabase/google/callback`
     - `https://shopee-bot-fj0w.onrender.com/api/auth/supabase/google/callback`
     - `https://shopee-bot-staging.onrender.com/login` (confirmação de e-mail)
     - `https://shopee-bot-fj0w.onrender.com/login` (confirmação de e-mail)
3. **Authentication → Providers → Email**: mantenha **Email habilitado e Confirm email ligado**. Configuração pública verificada: `external.google=true`, `external.email=true`, `mailer_autoconfirm=false`, `disable_signup=false`. O envio e clique no e-mail ainda exigem teste real com caixa postal de teste.
4. Abra **Project Settings / API Keys** e copie a chave `sb_publishable_...` do projeto; **nunca** use a secret/service_role no frontend ou no fluxo público de login.
5. **Authentication → Emails → SMTP Settings — PENDENTE, decisão de Rafa 01/11/2026:** manter **Enable custom SMTP desligado** e usar o envio padrão do Supabase somente para os endereços autorizados da equipe; **não** comprar domínio nem contratar/configurar provedor agora. A entrega de confirmação a qualquer cliente continua **não operacional**. Quando domínio próprio do Auto Orbital estiver registrado, configurado no site e documentado no Vault **ou** no projeto, a IA que consultar os documentos deve **avisar Rafa** e solicitar autorização para retomar essa configuração (provedor, DNS SPF/DKIM/DMARC, templates, URL e testes reais). Ver [TASK do Vault](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/TASK.md) e [documentação SMTP](https://supabase.com/docs/guides/auth/auth-smtp).

### 3. Configuração Render (sem código de segredo no repositório)

No serviço **staging**:
- `SUPABASE_AUTH_ENABLED=true`
- `SUPABASE_AUTH_PUBLISHABLE_KEY=<chave publishable do Supabase>`
- `SUPABASE_AUTH_REDIRECT_BASE_URL=https://shopee-bot-staging.onrender.com`
- `SUPABASE_AUTH_EMAIL_SIGNUP_ENABLED=true` (ou omita, pois é o padrão desta branch; a confirmação real do Supabase é obrigatória).

Quando houver homologação real, configurar as mesmas variáveis no serviço de produção, mas `SUPABASE_AUTH_REDIRECT_BASE_URL=https://shopee-bot-fj0w.onrender.com`.

> Não configurar agora antes da revisão e do deploy controlado. O código tem flag `false` por padrão.

### 4. Esquema e CI

- Migration versionada: `database/migrations/066_supabase_auth_identities.sql` adiciona `email` e `supabase_auth_user_id` opcionais, deixa `password` nullable, cria `pending_auth_registrations` com RLS bloqueada ao cliente e preserva IDs e dados legados.
- Validar schema, backup/reversão, conflitos de e-mail e RLS antes de aplicar. A rotina de migrations do app pode executar DDL no startup: revisar deploy antes de mesclar em staging, já que staging/produção usam o mesmo DB.
- Executar testes da API e build React. CI não autentica uma conta Google real.
- Testar manualmente, com contas de teste aprovadas: entrega real do e-mail (SMTP), link de confirmação, negação antes de confirmar, login após confirmar, primeiro provisionamento e segundo login, Google OAuth, logout, criação de perfil, isolamento, ADMIN não concedido e PKCE adulterado/expirado. Testar mudança de senha e exclusão de conta após completar as rotas Supabase correspondentes.

## Confirmação obrigatória por e-mail (decisão de Rafa)

O cadastro solicita usuário, e-mail, senha e confirmação idêntica. O backend registra somente um cadastro pendente enquanto a pessoa não confirma a caixa postal. O Supabase envia o link de confirmação; o site não emite sessão nem cria public.users antes do primeiro login com endereço confirmado.

O código recusa o cadastro se o Supabase retornar uma sessão imediatamente (sinal de que Confirm Email pode ter sido desligado). Para produção, confirmar que o envio e o clique no e-mail funcionam, inclusive em navegadores diferentes.

O login antigo do Render fica disponível somente enquanto SUPABASE_AUTH_ENABLED=false, durante preparação/rollback. A migração completa de sessões ainda está pendente e não foi aplicada.

Fontes oficiais:
- [Identity linking](https://supabase.com/docs/guides/auth/auth-identity-linking)
- [General Auth configuration](https://supabase.com/docs/guides/auth/general-configuration)
- [SMTP e riscos de segurança](https://supabase.com/docs/guides/auth/auth-smtp)
- [Google sign-in](https://supabase.com/docs/guides/auth/social-sign-in/auth-google)
- [Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)

## Contas existentes — somente no final, nunca por e-mail automático

1. Rafa identifica as duas contas legadas e os dois novos registros de Auth destinados a elas.
2. Ambas as sessões são verificadas por desafio legítimo (senha antiga + sessão Google correspondente).
3. Listar IDs/FKs/objetos de cada conta, perfis, credenciais e jobs antes de quaisquer mudanças.
4. Planejar transferência transacional dos registros novos (se houver) para os IDs `public.users` antigos, respeitando ownership/unique constraints e preservando o papel ADMIN apenas para o ID antigo já autorizado.
5. Reatribuir `supabase_auth_user_id` sob lock/transação, revogar sessões legadas e validar com login Google real; só então inativar o login antigo.
6. Fazer backup e registrar evidência da operação; não excluir identidades/usuários em massa.

## Pendências para encerrar a migração de autenticação

- Substituir a ponte JWT da aplicação pela validação e renovação de sessão Supabase Auth em todos os endpoints, inclusive mudança de perfil, settings, exclusão de conta, logout global e revogação.
- Implementar troca/recuperação de senha das contas Supabase (o endpoint antigo de troca foi bloqueado para elas).
- Validar end-to-end o fluxo de confirmação, duplicidade e recuperação de cadastros pendentes, inclusive concorrência e falhas.
- Validar concorrência/rollback do provisionamento de usuários e órfãos de Auth.
- Introduzir tratamento de redirect/cookies com testes de proxy e teste OAuth em staging.
- Concluir o vínculo manual das duas contas antigas somente com autorização final.

**Não promover para main enquanto essas pendências de autenticação essencial e validação real não forem resolvidas.**
