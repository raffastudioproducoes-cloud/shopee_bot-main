# Assets da marca Auto Orbital

Desde 10/11/2026 a marca é **código** (SVG vetorial), redesenhada fielmente a partir do logo original
(buraco negro com disco de acreção, anel de fótons e cards de conteúdo; nome "AutoOrbital" em Poppins
SemiBold com o "O" como anel planetário). Gerador: `docs/brand/gerador-da-logo.py` (fontTools + Poppins 600).

| Arquivo | Uso |
|---|---|
| logo-symbol.svg | símbolo completo animado (buraco negro + cards + estrelas): apresentação, composições grandes |
| logo-mark.svg | buraco negro animado, sem cards: abertura pós-login, carregamento, apresentação |
| logo-mark-static.svg | buraco negro sem animação, para tamanhos pequenos (menu lateral, rodapé, admin) |
| logo-wordmark.svg | nome "AutoOrbital" (login, cabeçalho da apresentação, abertura) |
| symbol.png (512) / symbol-128.png | rasterização (fallback, e-mail, integrações) |
| wordmark.png (1060x213, transparente) | rasterização do nome |
| favicon-16/32.png, ../favicon.ico (16/32/48), apple-touch-icon.png (180), icon-192/512.png, icon-maskable-512.png | favicon, iOS e PWA (rasterizados do símbolo) |
| og-image.png (1200x630) | pré-visualização social |

Os SVGs animam por CSS embutido (pulso do disco, flutuação dos cards, brilho das estrelas, esfera em órbita
por SMIL) e respeitam `prefers-reduced-motion`. Os glifos do nome são curvas (sem dependência de fonte).
