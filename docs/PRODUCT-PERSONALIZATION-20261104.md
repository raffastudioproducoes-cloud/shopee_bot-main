# Produto salvo — personalização de nome, copy e mídia

Data: 04/11/2026 · Escopo: staging · Candidato SemVer: MINOR 3.3.0 (não publicado).

## Contrato funcional

- Em **Editar/Personalizar produto**, o usuário altera apenas o nome, a descrição curta e a galeria privada.
- O backend rejeita (422) qualquer tentativa de PUT de `product_id`, `original_link`, `commission_link`, `commission`, `price_min`, `price_max` ou `image`. Essas informações de comércio continuam preservadas no banco; cálculo de ganho não é afetado.
- A imagem original Shopee fica disponível como URL somente leitura e **não consome** as cinco imagens extras.
- Descrição: até 280 caracteres ponderados segundo regra atual de X (o limite mais curto entre as redes consideradas), sem URL, inclusive links de afiliado. A API e a UI validam; a descrição é separada do link de comissão.
- Cada produto admite **cinco imagens adicionais** (JPEG/PNG/GIF/WebP) e **dois vídeos** (MP4), até 50 MB por arquivo, enviados do computador ou celular. O envio é persistido imediatamente; nome/copy são salvos ao pressionar **Salvar**. Os objetos ficam no bucket privado `post-media`.
- Conta proprietária é validada em toda listagem, upload e remoção. As URLs de preview são assinadas por 15 minutos; a UI não recebe credenciais de Storage. A sanitização é idêntica à usada pelos posts e reprocessa vídeos.
- Slots restritos por tipo e únicos no banco asseguram o teto mesmo contra requisições concorrentes. Upload respeita a RPC já existente de reserva global de armazenamento; erros não concedem bypass.
- Ao excluir o produto, a API remove os objetos físicos antes de apagar a linha; os metadados usam FK `ON DELETE CASCADE`. Na exclusão integral da conta, os objetos estão sob `products/<user_id>/<product_id>/...` e já são cobertos pelo manifesto de limpeza `account_erasure_storage_manifest` (segundo segmento igual ao ID da conta).
- Sem alterações no fluxo de agendamento, pg_cron, pg_net, funções de publicação e deploy.

## Banco compartilhado, rollout e recuperação

- Migração `database/migrations/087_product_personalization.sql`: `products.description` nullable e tabela `product_media` nova, RLS habilitado sem políticas para `anon`/`authenticated`; acesso por service role no backend com filtro `user_id`.
- Migração **aditiva**: produção antiga ignora os novos campos/tabela e continua funcionando enquanto a staging é validada. Não criar Supabase separado.
- Esta entrega **não escolhe automaticamente mídia armazenada ao criar posts**; a galeria fica salva no produto para futura seleção explícita, preservando o pipeline atual de publicação. Nenhuma mudança nos publicadores foi feita.
- Falha de upload: cancela reserva, remove metadados pendentes e tenta excluir objeto eventualmente enviado. Remoção de produto falha fechada se não for possível remover mídia.
- Recuperação de código: reversão do commit da staging; manter coluna e tabela aditivas para não perder mídia/dados. Jamais executar DROP como rollback automático.

## Gate de validação

1. Validar no Supabase real a existência das estruturas sem modificar dados já cadastrados; confirmar manifesto de exclusão.
2. Validar testes para payload de comissão/links bloqueado, descrição com URL/limite, quotas 5+2, account scope, upload inválido e exclusão segura.
3. Compilar frontend e validar modal desktop/mobile, nome/copy, URL original imutável, upload/preview/remoção e criação de produto intacta.
4. Commit, push e deploy na **staging**; validar Render LIVE/readiness e logs. **Não publicar main sem aprovação posterior**.
5. Registrar evidências em Vault e manter CHANGELOG [Não lançado] até promoção. `VERSION=3.2.0` por enquanto.
