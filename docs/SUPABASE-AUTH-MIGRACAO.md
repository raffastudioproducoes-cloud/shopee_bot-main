# Migração de autenticação — Supabase Auth (e-mail e Google)

> **Estado (01/11/2026):** PR #149 integrado em `staging` (`4c57385`), migration 066 aplicada e registrada no Supabase compartilhado, e Render staging com Google habilitado e segundo deploy `dep-dbjbbtbbc2fs73cb60hg` live. **Produção não ativada. Homologação Google E2E aguarda login real de Rafa nos dois Gmail.**
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

> **Atualização 01/11/2026:** as quatro variáveis acima foram configuradas somente em staging, via Render, e o deploy está live. O código permanece com padrão `false` e a produção deve continuar sem ativação até homologação real.

### 4. Esquema e CI

- Migration versionada: `database/migrations/066_supabase_auth_identities.sql` adiciona `email` e `supabase_auth_user_id` opcionais, deixa `password` nullable, cria `pending_auth_registrations` com RLS bloqueada ao cliente e preserva IDs e dados legados.
- Validar schema, backup/reversão, conflitos de e-mail e RLS antes de aplicar. A rotina de migrations do app pode executar DDL no startup: revisar deploy antes de mesclar em staging, já que staging/produção usam o mesmo DB.
- Executar testes da API e build React. CI não autentica uma conta Google real.
- Testar manualmente, com contas de teste aprovadas: entrega real do e-mail padrão a endereço autorizado, link de confirmação, negação antes de confirmar, login após confirmar, primeiro provisionamento e segundo login, Google OAuth, logout, criação de perfil, isolamento, ADMIN não concedido e PKCE adulterado/expirado. Testar recuperação de senha com link de verdade e atualizar senha, além de expiração do link e exclusão de conta.

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

## Recuperação de senha pelo Supabase Auth — preparada no PR #149

- No login, **Esqueci minha senha** abre modal que solicita **apenas o e-mail**. Em Configurações → Trocar senha, há o mesmo formulário de solicitação. Ambos chamam `POST /auth/supabase/password/recovery`.
- O backend chama somente `supabase.auth.reset_password_for_email(email, {"redirect_to": ".../login"})` e responde de forma genérica para não revelar se o e-mail existe. A entrega depende das limitações do servidor padrão do Supabase e do endereço autorizado.
- O link do template padrão **Reset password** é criado/validado pelo Supabase Auth e redireciona a `/login` (já autorizada em ambos os ambientes). A UI retira imediatamente o token do fragmento da URL, não salva refresh token nem senha em `localStorage` e mostra modal **Definir nova senha** com dois campos iguais e aviso explícito de alteração.
- `POST /auth/supabase/password/complete` valida o token com GoTrue e efetua a alteração em `/auth/v1/user` sob o **token de acesso autorizado**, usando só a chave publicável. Nenhum endpoint novo grava em `public.users.password`. A rota antiga `PUT /settings/password` retorna 410 com `SUPABASE_AUTH_ENABLED=true`. O login/senha continua sob gestão do Supabase.
- O cadastro exige usuário/nome de usuário, e-mail, senha, senha repetida e aceite dos Termos. O registro continua pendente até a confirmação por e-mail; o site não concede sessão nem cria perfil antes de login confirmado.
- Testes automatizados de envio (mock), endereço normalizado, ausência de vazamento do erro SMTP, senhas diferentes, token inválido/não confirmado, atualização remota e bloqueio da rota local estão em `tests/api/test_supabase_auth_transition.py`. **Ainda não é teste de entrega real nem de clique em link.**
- **Limite importante:** a sessão interna JWT permanece ponte de compatibilidade de até 24 horas, e a troca de senha no Supabase não invalida automaticamente todas essas sessões antigas. Revogação de sessões e migração completa de autenticação são pré-requisitos para abertura de produção.
- **Estado 01/11/2026:** PR #149 integrado em `staging` e formulário/link Google testados visualmente; ainda não testado login efetivo com identidade Google nem clique real em e-mail. Não ativar em produção sem esses testes, migração segura dos administradores e solução de envio a clientes.

## Contas existentes — somente no final, nunca por e-mail automático

1. Rafa identifica as duas contas legadas e os dois novos registros de Auth destinados a elas.
2. Ambas as sessões são verificadas por desafio legítimo (senha antiga + sessão Google correspondente).
3. Listar IDs/FKs/objetos de cada conta, perfis, credenciais e jobs antes de quaisquer mudanças.
4. Planejar transferência transacional dos registros novos (se houver) para os IDs `public.users` antigos, respeitando ownership/unique constraints e preservando o papel ADMIN apenas para o ID antigo já autorizado.
5. Reatribuir `supabase_auth_user_id` sob lock/transação, revogar sessões legadas e validar com login Google real; só então inativar o login antigo.
6. Fazer backup e registrar evidência da operação; não excluir identidades/usuários em massa.

## Pendências para encerrar a migração de autenticação

- Substituir a ponte JWT da aplicação pela validação e renovação de sessão Supabase Auth em todos os endpoints, inclusive mudança de perfil, settings, exclusão de conta, logout global e revogação.
- [Preparado no PR #149; falta E2E] Recuperação de senha das contas Supabase via e-mail/link e modal com senha repetida. Confirmar clique real, expiração e revogação de sessões internas.
- Validar end-to-end o fluxo de confirmação, duplicidade e recuperação de cadastros pendentes, inclusive concorrência e falhas.
- Validar concorrência/rollback do provisionamento de usuários e órfãos de Auth.
- Introduzir tratamento de redirect/cookies com testes de proxy e teste OAuth em staging.
- Concluir o vínculo manual das duas contas antigas somente com autorização final.

**Não promover para main enquanto essas pendências de autenticação essencial e validação real não forem resolvidas.**

## Registro de homologação parcial — staging, 01/11/2026

- [x] PR #149 integrado em `staging` no merge commit `4c57385dba5b07c9d2de1b319d2c5d417cf1c604`; CI do PR verde antes do merge; **não em `main`**.
- [x] `066_supabase_auth_identities.sql` aplicada ao Supabase `wcentenooirmwwlwlljp` e registrada na tabela `public.migrations` (campo real `aplied_at`). Estrutura/índice/tabela pendente/policy RLS verificados em SQL de leitura.
- [x] Render staging `srv-daukgs17lnhs738tpl50` com as quatro flags/valores de Auth habilitados e segundo deploy `dep-dbjbbtbbc2fs73cb60hg` live. Logs de inicialização: versão 066 já aplicada, ignorada sem erro.
- [x] Browser direto no staging mostrou login por e-mail e botão Google habilitado. Modal Criar conta: username, email, senha, confirmação e checkbox obrigatório. Recuperação de senha: email e envio de link.
- [x] Clique em Google redirecionou à conta oficial do Google com client OAuth existente; URL de retorno indicava `/api/auth/supabase/google/callback` em staging e Supabase `/auth/v1/callback`.
- [x] SQL de leitura confirmou `rafastudio` (ADMIN) e `RafaelTesteCliente` (USER) ainda sem `supabase_auth_user_id` nem e-mail gravado. Não alterar nem mesclar agora.
- [ ] **BLOQUEIO DE HOMOLOGAÇÃO E2E**: Rafa deve entrar com `raffastudioproducoes@gmail.com` e `rafael.c.m.galvao@gmail.com` no OAuth Google e concluir onboarding com usernames temporários diferentes dos legados. Testar callback, primeira sessão, segundo login, logout, usuário USER, isolamento de recursos e ausência de associação automática a legados. Nunca registrar credenciais/códigos/URLs de callback com tokens na documentação.
- [ ] Associar explicitamente as identidades novas às contas legadas apenas na etapa final com nova autorização e plano transacional/verificação de propriedade.
- [ ] Validar e-mail/recuperação com entrega real a endereços autorizados; sem SMTP próprio não abrir cadastro público por e-mail nem declarar esse fluxo homologado.

