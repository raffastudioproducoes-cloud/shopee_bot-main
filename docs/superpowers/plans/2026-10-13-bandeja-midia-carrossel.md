# Bandeja de fotos (carrossel/álbum) — plano curto

1. `lib/mediaTray.ts` (puro): `moveItem(list, from, to)` e `trayLimit(rules)` = menor `maxMedia` entre redes que entregam `carousel`.
2. `components/posts/MediaTray.tsx`: tira horizontal rolável (altura fixa), miniaturas numeradas, `N/limite`, remover, arrastar (HTML5 DnD) e botões ◀ ▶ (teclado).
3. Avisos por rede lidos de `compositionPlans` (modo `text_only`/`blocked`), sem lógica nova.
4. `PostsPage` (PostModal, só post novo): bandeja aparece com ≥2 imagens ou ao clicar "Montar carrossel/álbum"; vídeo segue na lista antiga; lista antiga só mostra o que não está na bandeja.
5. Ordem: `pendingFiles` → `uploadDraftMedia` em `for` sequencial → `draft_media_ids` → backend `enumerate` = `display_order`. Mover na bandeja = mover em `pendingFiles`.
6. `clearComposer` já zera `pendingFiles`; reabrir manual é estado local reiniciado no mesmo clear.
7. Teste: `frontend/tests/media-tray.test.mjs` (moveItem/trayLimit). Validação: `npm run build`, `node --test tests/*.mjs`, screenshot desktop/mobile.
