# Pré-visualização de postagens (Auto Orbital)

## Objetivo

O botão **Visualizar** no modal de posts abre uma representação aproximada de como o texto e a mídia serão apresentados em cada rede. A prévia começa fechada e não altera os campos do editor.

- **Desktop (>920 px):** editor e prévia em colunas no mesmo modal.
- **Tablet/celular (≤920 px):** painel de visualização sobreposto, com botão para voltar ao editor.
- **Celular (≤560 px):** tela cheia, abas com rolagem horizontal e vídeo vertical limitado à altura da tela.

## Organização por rede

| Rede | Estrutura visual | Situação no Auto Orbital |
| --- | --- | --- |
| Threads | Autor, texto, mídia e ações sociais abaixo | Planejamento de mídias existente. |
| X | Autor, texto, mídia horizontal, respostas/reposts/curtidas/salvos | Prévia disponível, publicação bloqueada no plano atual. |
| Facebook | Autor/Página, texto, mídia, Curtir/Comentar/Compartilhar | Elementos de interação ilustrativos. |
| Instagram | Foto em 4:5 com legenda abaixo; vídeo em visualização vertical | Exige mídia compatível. |
| TikTok | Vídeo vertical 9:16, legenda sobreposta e ícones laterais | O publicador exige MP4. |
| Kwai | Tela vertical de vídeo e interações | Prévia ilustrativa; publicação indisponível. |

Fontes oficiais consultadas:
- Instagram/Meta: https://about.fb.com/news/2023/11/new-ways-to-create-content-on-instagram/
- Threads/Meta: https://about.fb.com/news/2025/03/new-threads-features-more-personalized-experience-you-control/
- Facebook/Meta: https://about.fb.com/news/2025/12/making-it-easier-to-create-discover-and-share-content-on-facebook/
- TikTok: https://support.tiktok.com/en/getting-started/for-you/test-for-you
- X: https://help.x.com/en/using-x/types-of-posts
- Kwai: https://www.kwai.com/pt-BR/creators/grow

As interfaces mudam constantemente. A visualização não garante equivalência pixel a pixel nem o enquadramento final realizado pelas redes.

## Mídias Shopee e segurança

- Imagens e vídeos anexados pelo usuário continuam usando o endpoint existente de rascunhos e o bucket privado do Supabase.
- Ao selecionar produtos e marcar **Usar fotos dos produtos Shopee**, as imagens cadastradas entram na prévia e serão importadas para a publicação.
- A importação usa o endpoint autenticado POST /posts/product-image-drafts/{product_id}. O servidor consulta apenas produto da conta/perfil ativo.
- O servidor rejeita URLs arbitrárias, protocolos não HTTPS, redirecionamentos para hosts não confiáveis, arquivos acima de 8 MB e imagens inválidas. Só aceita os CDNs de imagem Shopee permitidos.
- Cada foto é sanitizada, normalizada para JPEG e armazenada como rascunho privado; quando a publicação é criada, a mídia fica vinculada de modo durável e pode ser reaproveitada entre redes.
- O catálogo atual salva a URL de foto, mas não oferece URL de vídeo do produto. **Vídeos Shopee ainda precisam ser enviados manualmente**; não se faz scraping de páginas.
- O usuário deve possuir os direitos necessários para divulgação do material.

## Arquivos e testes

- Interface: frontend/src/components/posts/PostLivePreview.tsx
- Estilo responsivo: frontend/src/components/posts/postLivePreview.css
- Integração: frontend/src/pages/PostsPage.tsx
- API e segurança: api/routers/posts.py
- Testes: tests/api/test_posts_media_drafts.py

Cenários manuais: campos vazios, variantes de texto, 1+ imagens, carrossel, MP4, seleção de produto, formatos 360/768/1280 px, navegação por teclado.


## Threads geradas por IA e filtragem por rede

A API `POST /posts/generate-copy` aceita `part_count` (1 a 10):
- `mode="full"` gera a descrição principal, variantes por limite de rede e
  todas as respostas adicionais existentes (até 10 partes, incluindo a primeira).
- `mode="append"` recebe `existing_texts` com o prefixo preenchido, gera
  apenas as partes ausentes, devolvendo `parts` + `start_index`. O editor
  aguarda 700 ms após adicionar partes para agrupar solicitações de IA e
  preserva qualquer texto digitado manualmente enquanto aguarda.
- A chave de IA é exclusiva do perfil; mantém o limite de 5 requisições por
  60 segundos aplicado ao endpoint. Respostas de IA passam por validação de
  comprimento e hashtags, com apenas uma tentativa adicional de correção.
- **Máximo de 10 partes** é uma decisão preventiva do Auto Orbital, não um
  limite oficial nem uma garantia contra bloqueio. As cotas e políticas de
  automação de cada rede ainda se aplicam.

### O que é enviado realmente

| Rede | Publicação do Auto Orbital | Texto enviado |
| --- | --- | --- |
| Threads | Post original + replies encadeadas via `reply_to_id` | Até 10 partes, cada uma no máximo 500 caracteres. |
| X | Suporta criação de replies via API, mas está indisponível no plano atual | O botão segue desativado; quando habilitado, até 10 partes de 280 unidades ponderadas. |
| Facebook | Uma publicação de Página | Apenas a descrição principal; as partes adicionais são descartadas no servidor. |
| Instagram | Uma publicação de imagem/carrossel/vídeo | Apenas a legenda principal (até 2.200 caracteres). |
| TikTok | Uma publicação de vídeo | Apenas a legenda do vídeo (até 2.200 unidades UTF-16). |
| Kwai | Não há integração confirmada | Botão inativo; nada é publicado. |

A filtragem acontece no planejamento da API e novamente no armazenamento
da thread: publicações sem suporte não recebem replies e não persistem
partes extras. O editor não exibe mensagens desnecessárias sobre essa
adaptação interna. Regras de mídia continuam sendo aplicadas por rede.

Referências oficiais pesquisadas em 2026-10-31:
- [Meta Threads API: criação e respostas `reply_to_id`](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api)
- [X API: criação de posts e replies](https://github.com/xdevplatform/docs/blob/main/x-api/posts/manage-tweets/introduction.mdx)
- [Instagram Publishing API](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
- [TikTok Direct Post: legenda até 2.200 unidades UTF-16](https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post)

O usuário não deve interpretar o teto de 10 como proteção completa contra
punições: volume diário, conteúdo repetitivo, reclamações e rate limits
continuam relevantes. Os publicadores registram falhas de plataforma sem
tentar contornar bloqueios.
