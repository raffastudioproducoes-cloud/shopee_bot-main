# Adaptação de mídia por rede, segurança de upload e PT-BR

Objetivo: a postagem chega ao destino sem a pessoa perder a conta em nenhuma rede.
Em vez de bloquear a rede inteira (dezenas de linhas vermelhas), cada rede recebe só o que aceita.

## Fases

- **A) Adaptação por rede, limites, alertas e PT-BR** (branch `feat/composer-adapt`)
  - Seletor limita ao máximo absoluto entre as redes marcadas, por tipo; arquivo que nenhuma rede aceita não entra (aviso de 1 linha).
  - Planejador (`api/media_composition.py` + espelho `frontend/src/lib/mediaComposition.ts`) filtra por extensão/tamanho/tipo, trunca no limite da rede, escolhe o grupo (imagens, senão vídeo) e informa o que foi adaptado.
  - `blocked` só se nada serve e nem texto puro é permitido; senão `text_only` com motivo curto. Respeita `delivered_modes`.
  - Batch liga ao post só as mídias usadas por aquela rede, na ordem do usuário.
  - Alertas: 1 linha por rede + `<details>` "Ver detalhes".
  - PT-BR: botão "Escolher arquivos", data `dd/mm/aaaa` e hora `hh:mm` com máscara, textos em inglês traduzidos.
- **B) Sanitização de upload** (Codex, branch `feat/upload-security`).
- **C) Investigação foto no Facebook** (outro agente, branch `feat/facebook-photo`).
- **D) Limpeza**: remover caminho Flask de DELETE de posts, docs, Vault.
- **E) Validação em staging e versão 2.3.0** (VERSION só nesta fase).

## Contrato

`/posts/preview` e `/posts/batch` mantêm os campos atuais; o plano por rede ganha `dropped`
(`[{id, name, reason}]`, opcional). `media_draft_ids` passa a ser exatamente o que a rede usa.

## Verificação

`pytest tests/api`, `npm run build`, `node --test tests/*.mjs`, `git diff --check`.
