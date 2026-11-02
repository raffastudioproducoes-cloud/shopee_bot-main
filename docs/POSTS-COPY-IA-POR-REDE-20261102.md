# Correção — IA e composição de posts por rede (2026-11-02)

> Destino: **staging** do Auto Orbital. Não promover a main nem alterar produção sem aprovação estética/funcional de Rafa. Sem chamadas de publicação reais neste ajuste.

## Evidência e causa raiz

No modal de post, o texto criado pela IA para Threads tinha **1.208/500 caracteres e 6/1 hashtags**. O usuário solicitou que um clique gerasse versões específicas para as redes marcadas. A implementação anterior:
- gerava descrições compartilhadas por **faixa de tamanho** (Facebook, Instagram e TikTok usavam a mesma legenda de 2.200 caracteres);
- validava a resposta, repetia só as variantes inválidas uma vez, mas **devolvia a variante ainda inválida** com `over_limit=true`;
- o frontend colocava o texto inválido no campo e o planejamento bloqueava o envio, exibindo inclusive "mídia não enviada" em consequência de erro exclusivamente textual.

## Contrato corrigido

1. A pessoa seleciona produto e redes. **Um clique** em "Gerar texto com IA" pede, numa solicitação estruturada, **uma descrição individual para cada rede selecionada**: Facebook, Instagram, TikTok, Threads e X (X permanece desabilitado no produto enquanto essa integração não estiver liberada).
2. As chaves estáveis de `variants` passam a ser o identificador da rede: `facebook`, `instagram`, `tiktok`, `threads`, `x`. O frontend compartilha a mesma ordem determinística por capacidade máxima e mostra abas com nomes das redes. Sem rede selecionada, o endpoint continua admitindo uma variante genérica de até 2.200 caracteres por compatibilidade, mas o **botão da interface exige uma rede**.
3. Os textos são avaliados por `api/network_limits.py` e `frontend/src/lib/networkLimits.ts`: caracteres Unicode, pesos do X, contagem UTF-16 TikTok, hashtags, links e menções. A IA recebe limites e orientação por rede e não pode inventar ofertas, estoque, desconto ou depoimentos.
4. Se a IA extrapolar, o servidor pede reescrita **somente das versões inválidas**. Se a segunda tentativa ainda falhar, aplica uma **adaptação determinística** com validação final: remove hashtags/menções excedentes, mantém o link cadastrado inteiro, reduz a descrição sem quebrar URLs e, se necessário, usa nome e link reais do produto como base. Nada é publicado nessa etapa. A resposta contém `adjusted=true` nas versões ajustadas, e a interface exibe aviso para revisão.
5. Uma saída que ainda viole os limites **não é retornada como sucesso**. O servidor devolve erro legível.
6. Edições **manuais** não são reescritas automaticamente. O sistema continua validando cada rede antes de criar os posts; post para rede incompatível não impede outras redes válidas.

## Imagens e vídeos (aproveitamento do planejador existente)

- O upload é único por pessoa/perfil. `adaptMedia` no frontend e `adapt_media` no backend selecionam, por rede, apenas mídia aceita por **extensão, peso, mistura e quantidades**. Preservam a ordem do subconjunto enviado e indicam quais arquivos foram omitidos.
- Se nenhuma mídia for utilizável, plataformas com postagem textual suportada recebem **apenas texto**, com aviso explícito antes de confirmar. Plataformas que exigem mídia são **excluídas daquela tentativa**, com motivo. Outro destino compatível continua publicável.
- O resumo passou a diferenciar **"rede excluída deste envio"**, **"publicará sem imagem/vídeo"** e **"recebe N de M mídias"**.
- O navegador também verifica duração, dimensão e proporção quando consegue ler metadados. O backend reconfirma as características persistidas que conhece; **transcodificação e inspeção de codec por rede não foram adicionadas**.
- Não prometer suporte universal a vídeo: apenas os modos em `delivered_modes` são candidatos; a disponibilidade real depende do publicador, permissões e credenciais. TikTok Photo Direct Post continua indisponível até a integração específica.
- Regras e limites de cada rede ficam em `networkLimits.ts` e `network_limits.py`, sempre sujeitos à documentação e rejeições reais da plataforma.

## Regressões / aceitação

- Caso real reproduzido em teste: Threads com texto acima de 1.200 caracteres e seis hashtags, mesmo após duas respostas ruins da IA; o resultado deve conter no máximo 500 caracteres, uma hashtag e link completo.
- Variantes distintas para Facebook e Instagram mesmo com teto idêntico (2.200).
- Um pedido de IA para todas as variantes válidas; nova tentativa somente para as inválidas.
- Contagem ponderada X e manutenção do link do afiliado; retorno antigo sem redes continua estável.
- Testes existentes de mídia cobrem excesso de fotos/vídeos, carrossel, arquivos rejeitados, queda para texto, bloqueio de TikTok/Instagram sem mídia, persistência de subconjuntos no lote e isolamento de perfil.

## Limites da verificação

- Testes unitários/integrados e CI são **simulados**, sem tráfego real para Threads, Meta ou TikTok.
- Rafa informou em 02/11/2026 que o layout Android e a visualização da conta USER passaram. Isso é **aprovação relatada pelo usuário**, não nova inspeção automatizada.
- Threads tem posts reais já agendados pelo usuário. **Não disparar publicações de teste** nem duplicar agendamentos; acompanhar as execuções e tratar novos erros separadamente, mediante acesso aos logs.
- Validar na interface de staging após o deploy: escolher Threads, gerar cópia, conferir 500/1, selecionar duas ou mais redes e revisar abas e avisos de mídia; testar desktop/Android com arquivos simulados antes de liberar em main.
