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
