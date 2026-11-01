# Migração de autenticação — Supabase Auth (e-mail e Google)

## Decisão do proprietário — conta temporária da Shopee e retirada do login legado (01/11/2026)

**Vigente até nova ordem de Rafa.** `RafaelTesteCliente` (USER, ID `2e895580-b2ac-4254-83ce-f465e77918c1`) é uma conta de testes destinada à equipe de suporte da Shopee. **Mantê-la exatamente como está:** acesso por nome de usuário e senha legada, sem e-mail, sem Google, sem outro provedor OAuth, sem cadastro fictício no Supabase Auth e sem alteração de senha/permissões/dados. O hash da senha já está em `public.users` no Supabase; a API atualmente hospedada no Render apenas valida esse login. O Supabase Auth/GoTrue não oferece senha+username nativos sem email/telefone; não iniciar autenticação especial/Edge Function para esta conta.

**Gatilho futuro (não automático):** Rafa informa que a Shopee concluiu os testes e concedeu a aprovação necessária. **Só depois** ele decidirá/executará a exclusão de `RafaelTesteCliente` e autorizará, em tarefa separada, a retirada definitiva do fluxo de autenticação legado do backend no Render. Aprovação da Shopee, isoladamente, **não autoriza** nenhum agente a excluir conta, senha ou recursos.

**Checklist futuro obrigatório:**
1. Confirmar encerramento dos testes com Rafa; inventariar perfis, credenciais, posts, agendamentos, jobs, mídia, logs e obrigações de retenção da conta antes da exclusão.
2. Planejar backup/reversibilidade, revogar sessões ativas e executar a exclusão **somente mediante ordem explícita**, com conferência dos IDs exatos e dependências/FKs. Preservar auditoria legal necessária; não limpar tabelas indiscriminadamente.
3. Verificar que a conta não autentica mais nem detém recursos indevidos. Separadamente, garantir que login Google do ADMIN e todos os fluxos de email/recuperação/registro por Supabase estão testados em staging e prontos para produção.
4. Remover verificação de senha legada, endpoints e modos de login antigos, hashes e dependências **somente após migração integral das demais contas e sessões**, com PR → CI → staging → testes → PR main → deploy/monitoramento e plano de reversão. A hospedagem da API no Render é outra decisão: \"tirar Auth do Render\" significa retirar a **verificação de credenciais legadas**, não necessariamente remover o serviço Render.
5. Atualizar `AGENTS.md`, guia mestre, `docs/TASK.md` e espelhos no Vault, anotando consentimento, evidências, PR/commit e testes.

**Até esse gatilho:** não criar novo mecanismo de username-only, não forçar Supabase Auth nativo nesta conta, não desligar o único login que permite os testes da Shopee e não promover a migração de autenticação para produção se ela bloquear essa conta.


> **Estado atualizado (01/11/2026):** PR #149 em staging, migration 066 no Supabase compartilhado e callback Google corrigido pelo PR #152 (deploy staging `645c815`). O primeiro Gmail completou onboarding real, criou sessão USER e foi **vinculado transacionalmente ao ADMIN legado `rafastudio`**, com preservação de seus dados. **Sessão Google pré-existente recuperada no navegador pelo PR #153; OAuth totalmente novo pós-deploy ainda pendente. Segunda vinculação cancelada para `RafaelTesteCliente` por decisão atual do proprietário: conta de suporte sem e-mail/Google. Produção não ativada para Supabase Auth.**
> Staging e produção compartilham o banco: a associação Google na `public.users` já é um fato no banco usado por ambos; o login Supabase só está ativado na staging.
> Não fazer novas mesclagens sem autorização específica de Rafa, sobretudo `RafaelTesteCliente`.

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

## Contas existentes — vínculos autorizados manualmente, nunca por e-mail automático

- A conta `rafastudio` (ADMIN) foi vinculada ao Google `raffastudioproducoes@gmail.com` mediante autorização específica e operação transacional documentada abaixo; ainda devem ser concluídos os testes E2E e de sessões necessários para produção.
- **Exceção expressa:** `RafaelTesteCliente` permanece sem vínculo com e-mail/Google/Supabase Auth. Continua com username/senha legada para a Shopee até Rafa autorizar sua exclusão, após o encerramento dos testes. Não há uma segunda mesclagem pendente.
- Para qualquer eventual vínculo futuro de outra conta: confirmar autorização de Rafa, verificar identidade e sessões, inventariar IDs/FKs e objetos, planejar backup e migração transacional com locks, revogar sessões antigas e testar o novo login antes de desativar o anterior. Nunca vincular automaticamente por coincidência de e-mail/nome, nem excluir identidades em massa.

## Pendências para encerrar a migração de autenticação

- Substituir a ponte JWT da aplicação pela validação e renovação de sessão Supabase Auth em todos os endpoints, inclusive mudança de perfil, settings, exclusão de conta, logout global e revogação.
- [Preparado no PR #149; falta E2E] Recuperação de senha das contas Supabase via e-mail/link e modal com senha repetida. Confirmar clique real, expiração e revogação de sessões internas.
- Validar end-to-end o fluxo de confirmação, duplicidade e recuperação de cadastros pendentes, inclusive concorrência e falhas.
- Validar concorrência/rollback do provisionamento de usuários e órfãos de Auth.
- Introduzir tratamento de redirect/cookies com testes de proxy e teste OAuth em staging.
- [Primeiro vínculo concluído em 01/11; falta login E2E] Validar no browser a identidade Google `raffastudioproducoes@gmail.com` vinculada ao ADMIN `rafastudio`; não repetir tentativa de autenticação recusada sem novo pedido. Não vincular o segundo Gmail à `RafaelTesteCliente`: a conta fica no login legado até o fim dos testes Shopee e exclusão autorizada.

**Não promover para main enquanto essas pendências de autenticação essencial e validação real não forem resolvidas.**

## Registro de homologação parcial — staging, 01/11/2026

- [x] PR #149 integrado em `staging` no merge commit `4c57385dba5b07c9d2de1b319d2c5d417cf1c604`; CI do PR verde antes do merge; **não em `main`**.
- [x] `066_supabase_auth_identities.sql` aplicada ao Supabase `wcentenooirmwwlwlljp` e registrada na tabela `public.migrations` (campo real `aplied_at`). Estrutura/índice/tabela pendente/policy RLS verificados em SQL de leitura.
- [x] Render staging `srv-daukgs17lnhs738tpl50` com as quatro flags/valores de Auth habilitados e segundo deploy `dep-dbjbbtbbc2fs73cb60hg` live. Logs de inicialização: versão 066 já aplicada, ignorada sem erro.
- [x] Browser direto no staging mostrou login por e-mail e botão Google habilitado. Modal Criar conta: username, email, senha, confirmação e checkbox obrigatório. Recuperação de senha: email e envio de link.
- [x] Clique em Google redirecionou à conta oficial do Google com client OAuth existente; URL de retorno indicava `/api/auth/supabase/google/callback` em staging e Supabase `/auth/v1/callback`.
- [x] SQL de leitura confirmou `rafastudio` (ADMIN) e `RafaelTesteCliente` (USER) ainda sem `supabase_auth_user_id` nem e-mail gravado. Não alterar nem mesclar agora.
- [ ] **BLOQUEIO DE HOMOLOGAÇÃO E2E (plano revisado):** concluir login fresco, segunda sessão, logout, isolamento de recursos e recuperação/cadastro Supabase sem afetar a conta de testes da Shopee. `rafastudio` já foi vinculado ao Google `raffastudioproducoes@gmail.com` por operação autorizada; verificar a sessão ADMIN de ponta a ponta. **Não exigir login com `rafael.c.m.galvao@gmail.com` nem associá-lo a `RafaelTesteCliente`.** Nunca registrar credenciais/códigos/URLs de callback com tokens na documentação.
- [ ] Qualquer outra associação de identidade exige pedido novo, verificação de propriedade e plano transacional; `RafaelTesteCliente` está excluído do escopo de mesclagem nesta fase.
- [ ] Validar e-mail/recuperação com entrega real a endereços autorizados; sem SMTP próprio não abrir cadastro público por e-mail nem declarar esse fluxo homologado.


### Incidente do primeiro login Google — 01/11/2026, 03:52 UTC

- Teste real com `raffastudioproducoes@gmail.com`: Supabase Auth confirmou Google e respondeu `/token` 200 para PKCE. `auth.users` possui agora a identidade Google confirmada. Não houve vínculo automático com `public.users.rafastudio` nem criação de sessão Auto Orbital.
- Render staging registrou `Callback Google rejeitado` (03:52:04/03:52:12 UTC) e redirecionamento a `/login?google_error=1`. Os logs Auth não exibiram a leitura `/user` entre o sucesso do token e a rejeição; o erro está no backend pós-troca, ainda sem stack específico porque o código capturava a exceção genericamente.
- [Correção aplicada em staging no PR #152](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/152): validação do access token diretamente via `GET /auth/v1/user`, sem recriar cliente SDK antigo com chave publicável moderna, e logs apenas com status/classe de erro. **CI #419 passou; merge `645c815a`, deploy Render `dep-dbjbhsdg1s2s73fqklh0` live. Novo OAuth real 04:00:27 UTC: Supabase `/token` 200, `/user` 200, callback levou a `/login?google_setup=1`. Ainda falta completar onboarding e validar sessão/painel.**
- Não apagar a identidade de Auth criada no teste; reutilizar o mesmo Gmail na repetição. **Nota posterior à homologação inicial:** a associação Google → `rafastudio` já foi realizada; a antiga hipótese de associar um segundo Gmail a `RafaelTesteCliente` foi explicitamente cancelada por Rafa. Ver decisão vigente no início deste documento.


### Mesclagem autorizada: Google do proprietário → ADMIN legado (01/11/2026)

- **Ambiente:** Supabase compartilhado `wcentenooirmwwlwlljp` (o vínculo de dados impacta staging e produção); **somente** o código/Auth Google de Render staging está habilitado. A autorização explícita de Rafa foi dada depois de concluir onboarding e autenticar em staging.
- **Identidade verificada:** `auth.users.id=a03469dc-daed-400c-8163-40120eba2c85`, Google `raffastudioproducoes@gmail.com`, com `email_confirmed_at` e identidade `auth.identities(provider=google)`.
- **Destino preservado:** `public.users.id=bb62026a-a7bf-4aa0-a05f-7ac570db3509` (`rafastudio`, ADMIN), perfil principal `909789bc-1882-4803-9895-12daa40e8cf3`. A conta original continua ADMIN; a senha legada não foi modificada para manter a produção operante até o corte.
- **Origem do onboarding:** `public.users.id=b4ef5316-f42a-4e6a-acab-74fb444a40e4` (`Raffastudio`, USER). Antes da mesclagem tinha a identidade Google e e-mail, perfil principal próprio, credenciais sociais vazias e logs, mas nenhum produto, post ou lista.
- **Operação SQL atômica `DO` com `FOR UPDATE`, pré-condições e rollback automático em erro:** desassociou e-mail/UUID Auth da origem e associou-os ao ADMIN antigo; transferiu os campos de aceite legal (sem alterar GPS), preservando IDs e dados de ambos os registros. **Nenhum usuário, perfil, log, token social ou publicação foi excluído ou reatribuído.** O USER provisório permanece sem Google/e-mail, apenas para auditoria e reversão; limpeza futura exige inventário e autorização específicos.
- **Verificação SQL após commit:** o ADMIN possui o UUID Google/e-mail confirmado, papel ADMIN, 1 perfil principal antigo, 6 produtos, 6 posts, 4 listas e 30 eventos de auditoria; origem mantém perfil e 19 request logs; `RafaelTesteCliente` (`2e895580-b2ac-4254-83ce-f465e77918c1`) intacta e ainda sem Auth.
- **Sessão/UI:** antes da transferência, browser em staging exibiu `Perfil ativo: Raffastudio` com zero produtos; foi feito logout e confirmado `/login`. **Validação do novo login Google na conta ADMIN NÃO concluída:** o pedido de autenticação no browser foi recusado; não repetir sem nova solicitação do usuário. Ao autorizar novo teste, confirmar `Perfil ativo: rafastudio`, Painel Admin, 6 produtos, perfil/credenciais e logout. Não alegar E2E concluído.
- **Pendentes:** autenticação Google completa do ADMIN, envio real SMTP/recovery e migração de sessão. **Sem segunda mesclagem** para `RafaelTesteCliente`: manter username/senha até fim dos testes da Shopee, exclusão autorizada e corte planejado do login legado. **Não publicar migração em main ainda.**
- **Reversibilidade:** dados e hashes anteriores preservados; eventual desfazer deve ocorrer em nova transação com conferências de IDs/únicos e retornar o `supabase_auth_user_id` e e-mail ao USER provisório, limpando-os do ADMIN; avaliar também os campos de termos, nunca reverter sem ordem do proprietário.


### Diagnóstico após primeiro vínculo — Google retorna ao login (01/11/2026)

- Evidência: Render staging `645c815` registrou sucessivos `GET /auth/supabase/google/authorize` 302 e `/callback` 303; Supabase Auth confirmou `POST /token` 200 e `GET /user` 200 para o UUID Google associado ao ADMIN antigo. Não havia `/auth/me` subsequente.
- **Causa no frontend:** o callback emitia cookie httpOnly e redirecionava a `/`, mas `PanelPage.tsx` verificava apenas `useAuthStore.isAuthenticated` persistido (false depois do logout). Antes de consultar o cookie via `/auth/me`, redirecionava a `/login`. Isso não significa que o vínculo `auth.users → public.users` falhou.
- **Correção preparada no PR #153:** o painel primeiro valida a sessão no backend; se cookie válido e store deslogado/trocado, reidrata com a identidade retornada; sessão inválida continua indo para `/login`. CI, deploy e login real pós-fix pendentes. Não promover a main sem homologação.
- **Exceção de conta de suporte (DECISÃO FINAL DESTA FASE):** `RafaelTesteCliente` segue username/senha sem e-mail/Google até testes Shopee terminarem; hash já em Supabase e verificação permanece no Render. **Não desenvolver autenticação especial**, nem criar identificador falso. Após aprovação informada por Rafa: exclusão sob autorização separada, depois retirada segura do login legado. Detalhes no início do documento.


### Correção publicada e sessão ADMIN recuperada — 01/11/2026

**Homologação complementar (01/11/2026):** PR #153 integrado em staging (merge `1613cb2ec4922d6ac1f32e7c000b2dd36a8db189`), CI #424 verde (build TS/Vite e testes API) e Render deploy `dep-dbjbsd2vcj2c73erdmag` **live**. Teste em browser com o cookie Google existente: navegar diretamente a `/` reidratou a sessão via `/auth/me` e abriu `/admin/overview`, exibindo `rafastudio` / `Administrador` e dados administrativos. **Ainda não foi executado OAuth completo a partir do zero depois desse deploy.** A conta `RafaelTesteCliente` continua USER com senha legada no Supabase, sem e-mail/Auth Google, reservada a testes do suporte Shopee; não migrar com email fictício nem tocar na senha.
