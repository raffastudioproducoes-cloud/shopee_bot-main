# Validação Shopee Open Platform e integração Shopee Vídeo

> **Atualização de 05/11/2026 (proposta em staging, gate CI pendente):** a página Credenciais passa a ter um card *informativo* “Shopee Vídeo”, com estado “Aguardando aprovação” e botão de conexão desabilitado. Nenhum OAuth, credencial, upload ou publicador foi ativado; a separação de Shopee Afiliados permanece. A alteração visual ainda não foi promovida a staging/prod nem homologada no Render.\n\nEstado em 31/10/2026: **cliente técnico em preparação, não conectado à interface nem habilitado em produção.**

## Mensagem de reprovação recebida

O console informou que a conta de teste não tem informações suficientes e solicitou um ambiente funcional com integrações existentes. O Auto Orbital usa a API Shopee Affiliate GraphQL para produtos/links; isso NÃO equivale à Open Platform Shopee Video Management. Não usar as credenciais de afiliado para assinar APIs de vídeo.

## Checklist dos campos Enterprise

| Campo | Como preencher de forma correta |
| --- | --- |
| Company's Legal Name | Razão social exata do registro empresarial |
| Business Registration Number | CNPJ correspondente à documentação empresarial |
| Business Registration Document | Comprovante empresarial oficial legível e atual |
| City/Town, Address e Postal Code | Endereço empresarial verdadeiro, conferido no registro |
| Country/Area | Brasil, quando o registro empresarial estiver no Brasil |
| Phone Number | Telefone corporativo válido |
| First Name, Last Name | Nome real do representante autorizado |
| Registered Contact Email | Endereço válido e monitorado |
| Secondary Contact Email | Preferencialmente outro contato válido de contingência |
| Security Report & Certification Type/File | Somente pentest real, com escopo, datas e responsável identificáveis; nunca apresentar texto de IA como certificado técnico |
| Service Information | Marcar apenas serviços funcionais e demonstráveis. Shopee Vídeo exige permissão Shopee Video Management na categoria de aplicativo correta |
| Live URL | URL HTTPS pública realmente funcional do Auto Orbital |
| Live Test Username / Password | Conta exclusivamente de testes, mínimo acesso, dados sintéticos, SENHA NOVA; fornecer somente pelo console oficial |
| Supported sellers | Quantidade real de vendedores atendidos, sem inflar números |
| Other platforms | Só aquelas realmente integradas |
| Remarks | Descrição curta do fluxo demonstrável, vídeo de demonstração sem segredos e roteiro de teste |
| Data Protection Policy | Revisar e aceitar somente com conformidade |

## Evidências para aprovação

1. Abrir o site em navegador limpo, autenticar com conta de teste e percorrer os módulos.
2. Mostrar integração Shopee Affiliate que de fato existe (catálogo, ofertas, links), sem chamá-la de publicação em Shopee Vídeo.
3. Mostrar integração ativa de rede social e publicação teste realmente concluída, se autorizado.
4. Mostrar separação multi-perfil e ferramentas de segurança/privacidade.
5. Gravar vídeo navegável e legível, sem incluir senhas, chaves nem dados de clientes.
6. Rotacionar a senha de teste exibida inadvertidamente em imagem compartilhada.
7. Se Shopee Video Management não estiver disponível no console, esclarecer a categoria correta com a Shopee. Não alegar que a API já está ativa.

## Fluxo técnico necessário

1. Aprovar aplicativo Shopee Video Management e autorizar usuário por OAuth específico. Partner ID/Key e refresh token precisam de armazenamento seguro.
2. Iniciar upload via v2.media.init_video_upload (business=3, scene=1), enviar partes com checksum MD5 e completar.
3. Acompanhar transcodificação com v2.media.get_video_upload_result até SUCCEEDED.
4. Obter capas com v2.video.get_cover_list; enviar legenda (até 150 caracteres), máximo seis IDs de produtos Shopee, sinalização AI, configurações e agendamento.
5. Editar dados com v2.video.edit_video_info e conferir success_list; publicar com v2.video.post_video e conferir confirmação.
6. Usar fila persistente/idempotência por perfil: não repetir POST de publicação com resultado incerto.
7. Manter funcionalidade desativada até aprovação externa, OAuth válido, testes com ambiente autorizado e homologação.

A biblioteca preliminar está em apis/shopee_video.py, com testes offline. Não está conectada ao editor nem às credenciais atuais. Isso é deliberado: habilitar sem OAuth/escopo seria falsa integração.

## Referências

- https://open.shopee.com/developer-guide/4
- https://open.shopee.com/developer-guide/736
- https://help.shopee.com.br/portal/10/article/165030-Passo-a-Passo-para-Criar-seu-Shopee-Video
- https://open.shopee.com/documents/v2/v2.video.post_video?module=129&type=1
- https://open.shopee.com/documents/v2/v2.video.edit_video_info?module=129&type=1
