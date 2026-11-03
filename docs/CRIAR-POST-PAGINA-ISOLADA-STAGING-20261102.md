# Auto Orbital — Criar POST em página dedicada (R01/R02 parcial, 02/11/2026 BRT)

## Por que esta etapa

Avançar na reformulação do novo post, com entrega de interface independente e escopo limitado. Projeto já tinha código de extração no PR #198, mas esse PR mistura campanhas, agendador, backend e galeria sem homologação. Esta branch nasce diretamente de `staging` e transfere **somente o fluxo de criação** para uma página responsiva.

## Alterações de código

- Menu lateral desktop/mobile: **Criar POST**, imediatamente antes de **Automação**.
- Rota privada `/posts/criar`, renderizada pelo `PanelPage`, usando `CreatePostPage` e `PostComposer`.
- `/posts` continua histórico/lista, busca, estados, reconciliação, remoção e `PostDetailsModal`; deixa de conter o longo formulário de criação.
- `PostComposer` reutiliza o funcionamento existente: redes, um produto por post, lista como seletor de produto, imagem principal Shopee, upload de imagens/vídeos do dispositivo, adaptações por rede, IA/personas, variantes, múltiplas partes, pré-visualização, publicação Agora ou Recorrente (hora local 24h), rascunho isolado por conta/perfil.
- `CreatePostPage` mantém a rotina de envio (prévia, criação em lote por rede, mídia privada em drafts, despachos Agora, mensagens parciais e prevenção de duplicação após erro no dispatch). Não alterou API de criação, banco, agendador nem redes sociais.
- Atualização **mínima** dos testes front para localizar o compositor no novo módulo e verificar a rota e as mídias.
- `VERSION=3.0.0` fica intacta até promoção autorizada.

## Não incluído deliberadamente

- Edição de post existente em página dedicada: continuará pela experiência já implantada de revisão **somente de texto futuro** no `PostDetailsModal`, com corte T–30. A futura rota de edição R01 será integrada quando tiver contrato seguro para mídia/produto; esta fase não relaxa `PUT` ou reescreve histórico.
- Campanha por lista (R03–R05, R08–R11), janelas de 30 dias e cotas futuras de planos; permanecem aprovadas para etapa própria.
- Seleção automática de fotos adicionais Shopee (R06): 3 sondagens reais em PR #200 não confirmaram `imageUrls`; não importar URLs não verificadas. **Foto principal e uploads de PC/celular permanecem normalmente disponíveis.**
- Nenhuma publicação externa, nem ativação de rede/mídia não suportada, migração SQL, mudança de cron, credencial ou `main`.

## Verificação de entrega

1. Tests/front TS/build automatizados pelo CI do PR da branch.
2. Regressão curta em staging após merge: acessar navegação desktop e Android, ver histórico, abrir Criar POST, confirmar carregamento de imagem Shopee, seletor de arquivos e opções Agora/Recorrente; **não salvar/publicar post real**.
3. Checar ausência de falhas de render na página e funcionamento do botão de voltar.
4. Registrar CI/deploy com SHA e diferenças efetivamente verificadas no Vault.

## Pontos de atenção

- Copiou a extração do compositor já construída na branch grande, mas removeu o seletor experimental de galeria adicional e o envio de URL não implementado no backend staging.
- O compositor não deve montar dentro de `Modal`, nem apagar rascunhos após recarregar a página.
- Nunca promover para `main` sem revisão de Rafa; PR #198 permanece DRAFT.

## Referências

- [Especificação R01–R18 (PR #198)](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/blob/feat/campanhas-listas-20261102/docs/superpowers/specs/2026-11-02-campanhas-listas-design.md)
- [F1 revisão de textos implantada](POSTS-F1-REVISOES-ISOLADA-STAGING-20261102.md)
