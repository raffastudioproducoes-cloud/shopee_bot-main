# Identidade cadastral da conta e preparo de cobrança — 07/11/2026

**Decisão de Rafa; implementação destinada somente a `staging`.** O gateway, checkout,
planos pagos reais e a renovação automática **não estão integrados**. Não existe
cobrança ou captura de cartão nesta entrega. `VERSION=3.4.0` atual; este acréscimo
entra na versão **MINOR candidata 3.5.0**, sujeita à homologação e aprovação de Rafa.

## Interface

- `/profiles`: substitui o banner grande por etiqueta de plano, cota compacta de
  perfis e `Melhorar plano` apenas para Free/Pro (não para Premium/ADMIN).
- Na própria página, formulário **Dados cadastrais da conta**, independente de
  `public.profiles`: nome/sobrenome, CPF, e-mail de acesso, celular, idade, e-mail
  alternativo de recuperação, telefone, endereço (logradouro, número,
  complemento, bairro, cidade, UF) e CEP.
- Nome completo, CPF, e-mail e senha são pedidos no cadastro por e-mail; o
  username técnico é gerado automaticamente. Login Google usa credencial do
  Google e pede nome/CPF ao finalizar OAuth (sem senha local inventada).
- Celular completa os requisitos de identificação para futura compra. Idade,
  e-mail alternativo, telefone, endereço e CEP são opcionais. O CPF anterior
  permanece cifrado e não é reexibido. Campo em branco significa preservar CPF.
- E-mail principal é herdado da autenticação, somente leitura; mudanças devem
  seguir fluxo de verificação separado. E-mail alternativo ainda **não recebe**
  links de redefinição: precisará provar propriedade antes de habilitar isso.

## Dados, isolamento e LGPD

- Migration `093_account_billing_identity.sql`: tabela aditiva
  `public.account_billing_identity` com PK/FK `user_id -> users`, cascade na
  exclusão integral, RLS habilitado, nenhum GRANT para anon/authenticated,
  service_role apenas; sem lista ou leitura global no browser.
- `full_name`, idade, telefone, endereço e CEP ficam somente na tabela de
  conta. CPF fica cifrado Fernet `APP_ENCRYPTION_KEY`, com HMAC-SHA256 derivado
  da chave para deduplicação. Nunca transmitir CPF de volta no GET, em logs,
  histórico ou no Store/localStorage. **Manter chave de cifragem compatível entre
  ambientes** ao publicar 3.5.0; planejar rotação sem invalidar fingerprint.
- `pending_auth_registrations` recebe nome/CPF cifrado enquanto aguarda e-mail
  confirmado pelo Supabase Auth. A conta comercial não nasce antes de Confirm
  Email. Pendências legadas sem nome/CPF permanecem legíveis e necessitam
  completar dados antes de futura contratação.
- GDPR/LGPD: atualizar lista pública de dados e política; antes de gateway,
  revisar base legal/retenção de cadastros abandonados e qual provedor de pagamento
  receberá quais informações. Não compartilhar CPF com fornecedores antes desse
  contrato e da necessidade real.

## Contratos de API e futuros gates

- `GET /users/me/identity`: apenas dados da conta autenticada, CPF mascarado
  como `cpf_registered: boolean` e `purchase_readiness` calculado pelo servidor.
- `PUT /users/me/identity`: altera apenas o próprio `user_id` obtido da sessão;
  valida CPF (dígitos), nome, telefone e CEP; erro não revela fingerprint.
- `GET /users/me/purchase-readiness`: `{ ready, missing }`. Para contratar:
  **nome completo + CPF + e-mail de acesso + celular**. O gateway futuro deve
  aplicar o mesmo gate no backend imediatamente antes de criar pedido ou mudar
  período/tier, jamais confiar no botão ou nos campos do cliente.
- Nenhuma operação atualiza `users.plan_tier`, `campaign_paid_through`, recibos,
  assinaturas ou limites. Futuro checkout precisa IDs imutáveis de conta/pedido,
  recibo do PSP, webhooks autenticados/idempotentes, reconciliação de datas/fusos,
  estado de assinatura e histórico sem duplicar cobranças.
- Perfis sociais secundários não adquirem assinaturas independentes. Titular é
  `public.users.id` e a conta compartilha um plano.

## Rollout e verificação

1. Executar CI/API/frontend/CSP e migration aditiva **sem tocar cron nem main**.
2. Aplicar 093 no **único Supabase compartilhado**, verificar tabela/RLS e grants
   sem consultar CPF real; compatível com main 3.4.0.
3. Merge PR para `staging`, deploy Render LIVE e checar os formulários via UI.
4. Confirmar cadastro real só em conta de teste autorizada quando SMTP e domínio
   estiverem formalmente prontos; testes automatizados usam mocks.
5. Só abrir PR `main` e alterar `VERSION` após homologação e aprovação expressa
   de Rafa; nunca ligar gateway ou assinar plano nessa fase.
