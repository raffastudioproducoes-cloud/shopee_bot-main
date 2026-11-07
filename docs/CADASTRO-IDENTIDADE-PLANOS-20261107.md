# Identidade cadastral da conta e preparo de cobrança — 07/11/2026

**Decisão de Rafa; implementação destinada somente a `staging`.** O gateway, checkout,
planos pagos reais e a renovação automática **não estão integrados**. Não existe
cobrança ou captura de cartão nesta entrega. `VERSION=3.4.0` atual; este acréscimo
entra na versão **MINOR candidata 3.5.0**, sujeita à homologação e aprovação de Rafa.

## Interface

- `/profiles`: substitui o banner grande por cota compacta de perfis e
  `Melhorar plano` apenas para Free/Pro (não para Premium/ADMIN). Após revisão,
  removida também a etiqueta do plano desta área; não afeta a TopBar global.
  **Revisão de 07/11:** a cota e os textos informativos (título, instruções,
  prontidão/pendências de contratação e aviso de carregamento) ficam organizados
  **acima do card principal**, sem duplicação dentro dele.
- **Dentro do card do perfil principal** (foto e nome), formulário **Dados cadastrais da conta**,
  com dados de titular armazenados separadamente de `public.profiles`: nome/sobrenome,
  CPF, e-mail de acesso, celular, data de nascimento com calendário, e-mail
  alternativo de recuperação, telefone, endereço (logradouro, número,
  complemento, bairro, cidade, UF) e CEP.
- Nome completo, CPF, e-mail e senha são pedidos no cadastro por e-mail; o
  username técnico é gerado automaticamente. Login Google usa credencial do
  Google e pede nome/CPF ao finalizar OAuth (sem senha local inventada).
- Celular completa os requisitos de identificação para futura compra. Data de nascimento,
  e-mail alternativo, telefone, endereço e CEP são opcionais. O CPF anterior
  permanece cifrado e não é reexibido. Campo em branco significa preservar CPF.
- A máscara de CPF surge automaticamente na digitação (`000.000.000-00`);
  mantém validação de dígitos verificadores, sem mudar o contrato cifrado.
  O calendário nativo permite selecionar dia/mês/ano, salvo em `birth_date`
  como data completa, sem deduzir nascimento a partir da idade legada.
- E-mail principal é herdado da autenticação, somente leitura; mudanças devem
  seguir fluxo de verificação separado. E-mail alternativo ainda **não recebe**
  links de redefinição: precisará provar propriedade antes de habilitar isso.
- A página organiza a conta em **cards**, não apresenta formulário cadastral
  isolado acima dos perfis: o card principal ocupa a largura disponível, traz
  foto/nome e a grade editável de dados do titular. Cota e informações gerais
  ficam acima do card, no mesmo bloco da coluna esquerda, sem outros formulários.
  Os demais cards continuam compactos, só com foto e nome; seu menu permite
  editar apenas nome/foto. Se o registro de perfil principal estiver temporariamente
  ausente da lista, um card de contingência mantém acesso ao cadastro da conta.
- **Distribuição dos cards em 07/11/2026:** em largura de desktop (a partir de
  1000px) e com perfis adicionais, o card principal permanece à **esquerda** e
  os secundários ocupam a coluna da **direita em fila vertical**, alinhados ao
  topo. Abaixo disso, os cards são empilhados com o principal primeiro. Se a
  conta ainda não tem secundários, o principal pode usar a largura disponível.
  Nenhum campo muda de dono, e os cards secundários continuam só foto/nome.
- **Correção de primeiro acesso em 07/11/2026:** para contas antigas sem linha em
  `account_billing_identity`, `maybe_single().execute()` pode retornar o objeto
  Python `None`, não apenas uma resposta com `data=None`. A leitura e a primeira
  gravação agora toleram esse resultado; `GET` retorna dados vazios com HTTP 200
  e `PUT` insere o registro da conta. O formulário inteiro é renderizado desde
  o início. Em caso de indisponibilidade real da API, fica visível mas bloqueado,
  com opção de tentar novamente; nunca permitir salvar estado vazio sobre dados
  existentes sem hidratar o formulário. Teste de regressão simula `None`.

## Dados, isolamento e LGPD

- Migration `093_account_billing_identity.sql`: tabela aditiva
  `public.account_billing_identity` com PK/FK `user_id -> users`, cascade na
  exclusão integral, RLS habilitado, nenhum GRANT para anon/authenticated,
  service_role apenas; sem lista ou leitura global no browser.
- Migration `094_account_identity_birth_date.sql`: coluna opcional `birth_date
  DATE`, aditiva e idempotente, na mesma tabela com RLS/grants preservados.
  Coluna legada `age` não é removida; somente a data completa é atualizada
  pelo novo formulário. Não converter idade para uma data aproximada.
- `full_name`, idade legada, data de nascimento, telefone, endereço e CEP ficam somente na tabela de
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
  valida CPF (dígitos), nome, telefone, CEP e data de nascimento não futura;
  `birth_date` é ISO `YYYY-MM-DD` ou `null`, erro não revela fingerprint.
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

## Simplificação dos perfis sociais (07/11/2026)

- **Somente os cards secundários** exibem exclusivamente imagem e nome. O
  card principal também reúne todos os dados cadastrais da conta titular.
  Clique/toque na área da identidade para ativar; menu discreto permite alterar
  foto, editar nome e, quando permitido, excluir.
  Perfil ativo fica distinguido pela borda, sem tag de status; função e plano
  continuam no backend, mas não são repetidos no cartão.
- Formulário de perfil pede **nome** e **foto opcional** (JPEG/PNG/WebP até
  5 MB). Se a foto falhar após criar ou renomear, o perfil continua salvo e a
  interface avisa; nunca recria o perfil automaticamente.
- `profiles.email`, `telefone` e `endereco` permanecem como colunas legadas
  compatíveis com produção, mas **não são coletadas** no novo formulário.
  RPC existente permite `p_email=NULL`; edições somente do nome preservam
  valores legados, sem nova migration nem limpeza de dados. Dados cadastrais
  do titular seguem na tabela da conta (`account_billing_identity`). `GET /profiles`
  passa a retornar apenas ID, proprietário, função técnica, plano técnico,
  nome e avatar, evitando expor no browser contatos antigos desnecessários.

## Rollout e verificação

1. Executar CI/API/frontend/CSP e migration aditiva **sem tocar cron nem main**.
2. Aplicar 093 no **único Supabase compartilhado**, verificar tabela/RLS e grants
   sem consultar CPF real; compatível com main 3.4.0.
3. Merge PR para `staging`, deploy Render LIVE e checar os formulários via UI.
4. Confirmar cadastro real só em conta de teste autorizada quando SMTP e domínio
   estiverem formalmente prontos; testes automatizados usam mocks.
5. Só abrir PR `main` e alterar `VERSION` após homologação e aprovação expressa
   de Rafa; nunca ligar gateway ou assinar plano nessa fase.
