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


## Correção operacional do salvamento (05/11/2026, somente staging)

- **Incidente:** o PUT /products/34 retornou HTTP 500 às 00:45:07 UTC (21:45:07 BRT em 04/11). O log do Render identificou AttributeError: 'SyncFilterRequestBuilder' object has no attribute 'single' em api/routers/products.py:242. O upload da imagem já havia sido persistido separadamente e não causou a falha.
- **Causa e correção:** consulta pós-UPDATE usava um método válido em leituras SELECT, mas não no builder de atualização da biblioteca. Removido .single(); a resposta do .execute() é lista, com tratamento de zero linhas como 404 e normalização da primeira linha. O filtro id + user_id permanece aplicado em ambas as etapas e o payload permitido continua apenas name/description.
- **Escopo de dados:** a coluna products.description já existe no Supabase único; sem necessidade de migração, alteração de política, Storage, cron ou outros serviços. Arquivos enviados antes do erro não devem ser reenviados cegamente.
- **Gate:** teste com builder fake sem .single() reproduziu a falha antiga e validou o código corrigido, inclusive isolamento de conta, integridade comercial e rejeição de payload vazio. Conclusão de deploy/QA real e referência de commit devem ser registradas no TASK vivo do Vault.

## Prévia no card expandido de Produtos (05/11/2026, somente staging)

- Ao expandir um produto em **Meus Produtos**, o card mantém as estatísticas comerciais originais e passa a exibir em largura total o bloco **Personalização salva**, somente leitura: descrição curta persistida no produto e galeria de imagens/vídeos adicionais.
- O bloco é montado apenas quando o card está expandido. A consulta autenticada existente `GET /products/{id}/media` é feita sob demanda, por produto/conta, reutilizando cache `["product-media", id]` e invalidação já realizada no editor após upload/remoção. Não há busca em massa de mídias de todos os produtos.
- Imagens adicionais aparecem em miniaturas que abrem um modal de visualização ampliada; vídeos MP4 abrem o mesmo modal com player e controles. Não há ações de edição/remoção nesse bloco: alterações continuam exclusivas do botão **Editar**.
- A descrição vem da API de listagem de produtos, não do rascunho local nem do resultado gerado pela IA antes de **Salvar**. Estados explícitos de ausência de descrição, galeria vazia, carregamento e falha de rede. A imagem original Shopee continua como miniatura do card e não conta nas mídias extras.
- Sem nova API, storage, migration, cron, mudança de cálculo/valores comerciais ou impacto no fluxo de publicações. Compatível com card desktop/mobile e reutiliza design system/Modal/ícones existentes.
- Teste local antes do commit: `node --test frontend/tests/products-saved-preview.test.mjs` (3 cenários). A validação visual na staging é feita após o Render LIVE.
\n## Limpeza de duplicidades no card (05/11/2026, somente staging)\n\n- Card expandido mantém os indicadores superiores (ID Shopee, preço, comissão, ganho estimado e data de cadastro) e o nome no cabeçalho.\n- A timeline inferior deixa de repetir Produto, Preço, Comissão e Cadastro: exibe **somente Links** com URL original e URL de afiliado já existentes.\n- O bloco de personalização salva continua abaixo dos links, com descrição persistida e galeria privada sob demanda; editar e excluir não mudam.\n- Ajuste visual compatível PATCH, sem alteração de backend, schema, API ou regras comerciais; incorporado à candidata MINOR 3.3.0, sem bump antecipado de VERSION.\n