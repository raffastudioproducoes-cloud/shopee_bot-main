# Migração de autenticação — Supabase Auth (e-mail e Google)

> **Estado:** preparação em `feature/supabase-auth-email-google`; NÃO foi ativado em produção.
> Preservar as duas contas legadas em `public.users`. Não associar IDs de Auth ou mesclar contas sem nova autorização de Rafa.
> Staging e produção compartilham o mesmo projeto Supabase: qualquer criação de conta ou migration na staging é real nesse banco.

## Objetivo e fronteira

- O Supabase Auth verifica senhas de contas novas e a identidade retornada pelo Google.
- `public.users.id` continua sendo o ID interno do Auto Orbital para produtos, perfis e publicações.
- `public.users.supabase_auth_user_id` associa a identidade `auth.users.id` à conta interna. Não vincular pelo e-mail de perfil, nome ou coincidência de username.
- A sessão JWT interna `access_token` ainda é **ponte transitória** para os routers existentes e NÃO representa a migração completa de sessão. Não declarar o Render fora da autenticação até substituir essa dependência e migrar settings, troca de perfil, sessões e revogação.
- `api/routers/auth.py` conserva login das contas antigas sem vínculo; cadastro antigo recebe 410 quando Supabase Auth estiver ativado.
- Novas contas recebem sempre papel USER e passam pelo provisionamento de perfil principal/credenciais vazias.

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
3. **Authentication → Providers → Email**: mantenha Email habilitado. **Não desative "Confirm email" para cadastro público.** Ver risco abaixo. É possível testar temporariamente uma configuração sem confirmação apenas em ambiente fechado e com contas controladas; este projeto Supabase é compartilhado com produção, por isso não há isolamento automático.
4. Abra **Project Settings / API Keys** e copie a chave `sb_publishable_...` do projeto; **nunca** use a secret/service_role no frontend ou no fluxo público de login.

### 3. Configuração Render (sem código de segredo no repositório)

No serviço **staging**:
- `SUPABASE_AUTH_ENABLED=true`
- `SUPABASE_AUTH_PUBLISHABLE_KEY=<chave publishable do Supabase>`
- `SUPABASE_AUTH_REDIRECT_BASE_URL=https://shopee-bot-staging.onrender.com`
- `SUPABASE_AUTH_EMAIL_SIGNUP_ENABLED=false` **até haver verificação de propriedade do e-mail / aprovação explícita do risco**.

Quando houver homologação real, configurar as mesmas variáveis no serviço de produção, mas `SUPABASE_AUTH_REDIRECT_BASE_URL=https://shopee-bot-fj0w.onrender.com`.

> Não configurar agora antes da revisão e do deploy controlado. O código tem flag `false` por padrão.

### 4. Esquema e CI

- Migration versionada: `database/migrations/066_supabase_auth_identities.sql` adiciona `email` e `supabase_auth_user_id` opcionais, deixa `password` nullable e preserva IDs e dados legados.
- Validar schema, backup/reversão, conflitos de e-mail e RLS antes de aplicar. A rotina de migrations do app pode executar DDL no startup: revisar deploy antes de mesclar em staging, já que staging/produção usam o mesmo DB.
- Executar testes da API e build React. CI não autentica uma conta Google real.
- Testar manualmente, com contas de teste aprovadas: primeira autorização Google, onboarding com aceite de Termos, retorno, segundo login, logout, criação de perfil, isolamento de outro usuário, ADMIN não concedido, código PKCE adulterado/expirado, mudança de senha e exclusão de conta.

## ALERTA DE SEGURANÇA — cadastro sem confirmação de e-mail

Supabase documenta que desligar **Confirm Email** trata como confirmado um e-mail cuja propriedade não foi demonstrada. Supabase Auth também pode vincular automaticamente identidades por e-mail. Isso pode permitir *pre-account takeover*: alguém cadastrar o e-mail de outra pessoa e depois obter acesso quando o titular legítimo conectar Google.

Por isso, a implementação mantém `SUPABASE_AUTH_EMAIL_SIGNUP_ENABLED=false` por padrão, separadamente do login por e-mail e do login Google. Não liberar cadastro público por senha sem resolver o risco. Alternativas seguras: confirmação de e-mail (recomendada) ou cadastro restrito a usuários administrativamente convidados e verificados.

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
- Tratar clientes com confirmação de e-mail habilitada e cadastros pendentes sem duplicar usuário.
- Validar concorrência/rollback do provisionamento de usuários e órfãos de Auth.
- Introduzir tratamento de redirect/cookies com testes de proxy e teste OAuth em staging.
- Concluir o vínculo manual das duas contas antigas somente com autorização final.

**Não promover para main enquanto essas pendências de autenticação essencial e validação real não forem resolvidas.**
