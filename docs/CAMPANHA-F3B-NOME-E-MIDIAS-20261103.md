# Auto Orbital — F3B: nome da campanha e mídias duráveis por produto (03/11/2026)

## Requisito e fronteira
Cada campanha tem um **nome próprio**, independente do nome da lista-fonte. O editor de campanha na página `/posts/criar` permite selecionar a foto principal da Shopee e anexar fotos/vídeos enviados pelo usuário em PC ou celular **para cada produto**. O formulário permanece página, nunca modal.

Esta fase **não ativa campanhas, cria posts/jobs, altera calendários reais ou dispara redes**. O fluxo de **Publicação única** e suas fontes, uploads, automações e credenciais não foi modificado. `main`, produção e `VERSION=3.0.0` permanecem fora da entrega.

## Contrato
1. Campo obrigatório **Nome da campanha**, 1–120 caracteres após retirar espaços nas pontas. O nome é salvo em `campaign_drafts.campaign_name`, retornado na API e usado ao selecionar um rascunho. Legados recebem o nome da lista anterior na migração.
2. Mantidos snapshot por produto: título, copy, link afiliado, redes, versões por rede, ordem e foto Shopee. Alterar campanha não muda listas-fonte.
3. Anexo durável exige primeiro **Salvar rascunho**. Cada produto comporta até 10 anexos. Formatos suportados pela pipeline existente: imagens JPEG/PNG/WEBP/GIF e vídeo MP4, no máximo 50 MB por arquivo; sanitização/reconstrução no backend. A interface lista nome e tipo e permite remover.
4. Referências em tabela `campaign_draft_media` separada de `temporary_media_uploads`. Bucket privado **post-media**, prefixo exclusivo `campaigns/{user}/{profile}/{campaign}/{product}/{uuid}...`. Sem URL pública ou chave bruta em resposta.
5. Autenticação de usuário e perfil em todas as operações; validação do produto pertencente ao snapshot; índice de ownership, RLS sem direitos `anon/authenticated`, trigger que valida vínculo campanha/produto, `service_role` somente no servidor. A quantidade máxima de mídias é garantida por slots únicos 0–9 no banco, inclusive concorrência.
6. Upload interrompido fica em `uploading`; falha de rollback em `delete_failed`. Em próximo upload da mesma campanha, recuperação limitada de objetos incompletos com mais de 2 h. Mídias `ready` **não expiram em 24 h** e nunca entram nessa limpeza. Remoção explícita tenta apagar Storage antes do registro.
7. `DELETE` de campanha ainda não é oferecido; qualquer implementação futura deverá remover objetos do Storage antes do `ON DELETE CASCADE` das referências, para não gerar órfãos. A ativação posterior deve consumir snapshots e mídia sem reaproveitar temporários vencidos.

## Migração 071 e implantação
- Arquivo `database/migrations/071_campaign_names_and_media.sql` **aditivo e reentrante**, pois a aplicação também roda seu migrador no boot. Nunca usar DDL que falhe ao executar duas vezes. Índices e triggers são condicionais; o schema compartilhado recebeu a 071 com autorização e o migrador do aplicativo a reexecutou sem erro.
- Supabase staging/produção usam banco compartilhado: Rafa autorizou o escopo necessário; 071 aplicada e verificada sob o nome `campaign_names_media_071`. PR #209 mesclada somente em `staging` após CI verde. Não promover `main` sem aprovação de release.
- CI API/frontend da PR e verificação pontual após deploy bastam; sem publicações reais nos testes. Toda mudança documentada em `docs/TASK.md`, `CHANGELOG.md` e Vault do projeto.
- **Limitação de escopo:** seleção de foto Shopee é a principal já autenticada; a API atual não entrega galeria extra validada. O experimento anterior foi encerrado como indisponível na fonte existente. Upload próprio permanece alternativa. Nenhum reenquadramento do fluxo TikTok Photo Direct Post nesta fase.

## Critérios de aceite
- [ ] O usuário consegue dar nomes distintos a campanhas baseadas na mesma lista e retomar cada uma em outro dispositivo.
- [ ] Arquivos de diferentes produtos e perfis ficam segregados, persistem sem TTL temporário e podem ser excluídos.
- [x] Integridade de nomes/slots/ownership e migration reentrante validadas pelo CI; frontend compila.
- [ ] Após autorização da 071 e merge `staging`, checagem rápida de boot/health e teste controlado de upload/recuperação/exclusão, sem criar posts reais.
- [x] Publicação única, Shopee, credenciais, scheduler, produção e cotas inalterados.

## Evidências de integração (03/11/2026)
- CI [#41578367282](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41578367282) SUCCESS; merge staging `5ec24df`.
- Migration Supabase `campaign_names_media_071` aplicada, RLS true, privilégios `anon/authenticated` ausentes, service_role permitido, trigger único, zero mídias antes do ensaio.
- Render `dep-dbkm74ks728c738ritc0` LIVE; log da 071 aplicada na segunda execução e `Application startup complete`; `/health` respondeu `{"status":"ok"}`.
- UI autenticada: campo nome no topo, rascunho recuperado, checkbox foto Shopee preservado e seletor de arquivos disponível. **Nenhum upload real por navegador nem criação de post foi realizado**; esse ensaio segue pendente com mídia descartável e mecanismo de limpeza.
