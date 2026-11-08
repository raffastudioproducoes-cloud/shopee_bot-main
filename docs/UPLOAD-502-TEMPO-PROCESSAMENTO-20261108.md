# Auto Orbital — diagnóstico HTTP 502 e cronômetro de processamento de mídia

> **Autorização posterior (08/11/2026):** Rafa informou que os testes da staging passaram e autorizou **PATCH 3.6.2 e merge para main**. O registro abaixo preserva o estado da fase de homologação; a release só estará em produção após os portões de CI/SemVer e Render LIVE. [Acompanhamento da promoção](RELEASE-3.6.2-20261108.md).

**Data:** 08/11/2026 · **Área:** Produtos → Editar → Imagens e vídeos do produto  
**Classificação:** correção compatível, **PATCH candidata 3.6.2** · **Ambiente:** staging **LIVE**; `main` exige novo aceite de Rafa.
**Versão oficial enquanto não houver aceite:** `VERSION=3.6.1`.

## Ocorrência e análise causal

- Rafa observou `Erro inesperado (HTTP 502). Tente novamente.` no upload em Android (captura às 18:21, hora de Brasília), após homologar a correção do MP4 da 3.6.1. A captura comprova a resposta **502**, mas não sua causa interna.
- **Defeito reproduzível em código:** o proxy Flask `web/routes/api_proxy.py` impunha 30 segundos para **todas** as chamadas FastAPI. A API de Produtos processa MP4 sincronicamente pelo pipeline de reencodificação: FFmpeg permite até 90 segundos, ffprobe até 10 segundos por inspeção, seguidos de sanitização e armazenamento Supabase. Assim o proxy podia retornar 502 por `requests.ReadTimeout` **enquanto o processamento continuava**, criando incerteza e risco de reenvio duplicado. O frontend ignorava o campo JSON `{error}` do proxy, exibindo texto genérico.
- **Limite da evidência:** a consulta aos logs Render no intervalo da captura não identificou o registro individual do 502 nem uma exceção FFmpeg. Portanto o timeout de 30 segundos é a **causa provável, demonstrada pela incompatibilidade de prazos**, não confirmação forense daquela requisição específica. Persistindo erro, examinar request ID/log, recursos do worker, rede interna e Storage.

## Decisões implementadas

1. Somente `POST /api/products/{id}/media` ganha prazo upstream de **5 segundos de conexão e 180 segundos de leitura/resposta**. Todas as demais rotas permanecem com **30 segundos**; a regra não aumenta `MAX_CONTENT_LENGTH`, tamanho de vídeo, permissões ou capacidade de upload.
2. Timeout HTTP vira **504** com explicação em português e orientação para consultar a galeria antes de reenviar, já que o servidor pode concluir a gravação após a desistência do cliente. Falha real de conexão mantém **502**. Logs sanitizados discriminam `product-media-upload` e `api-general`, sem nomes de arquivos, dados pessoais, corpo HTTP, tokens ou host interno.
3. `formatApiError` passa a respeitar também o campo textual `{error}` do proxy. Erros de validação FastAPI continuam sendo apresentados normalmente.
4. No **mesmo painel sombreado/skeleton com anel circular**, a porcentagem permanece a fração **real de bytes transmitidos por `XMLHttpRequest.upload.onprogress`**. A fase de processamento começa quando `xhr.upload.onload` confirma o fim do envio; um cronômetro `MM:SS` usa relógio real (`Date.now()` + tick de 1 s), com atualização e limpeza do intervalo ao concluir, falhar ou desmontar. A contagem reinicia em cada arquivo de lotes múltiplos.
5. Avisos de status evoluem em **0, 15, 30, 60 e 120 segundos** de processamento, inclusive aviso sobre possível gravação tardia. O painel permanece após sucesso/falha, apresenta motivo do erro, e disponibiliza **Atualizar galeria para conferir** após falha. Não reenvia automaticamente, nem inventa estágio específico de FFmpeg/Storage, percentual de conversão ou sucesso anterior à resposta da API.
6. Para acessibilidade, as mudanças de etapa e mensagem usam `aria-live=polite`; o timer, que muda a cada segundo, usa `aria-live=off` para evitar anúncio de cada incremento. Respeitar `prefers-reduced-motion`, layout mobile e os limites existentes de 5 imagens/2 vídeos.

## Testes e aceite

- [x] Teste Flask **isolado**, sem banco/Supabase: upload de Produtos usa timeout `(5,180)`, outra rota continua em `30`, timeout resulta 504 com texto sanitizado, falha de conexão continua 502 (4 cenários PASS).
- [x] `frontend/tests/product-media-upload-progress.test.mjs`: 4/4 PASS, cobrindo porcentagem real, timer, avisos, ciclo/limpeza, sucesso/falha, erros e skeleton.
- [x] `npm run build`: TypeScript + Vite PASS.
- [x] `python -m pytest tests/web/test_api_proxy.py tests/web/test_api_proxy_csrf.py --confcutdir=tests/web -q`: **10/10 PASS**, utilizando a fixture isolada em `tests/web/conftest.py` (não requer PostgreSQL). O primeiro comando sem `--confcutdir` carregou a fixture legada da raiz que exige Postgres indisponível e falhou na inicialização; corrigida a invocação, os testes passaram.
- [x] Lote frontend utilizado no CI que inclui o teste de mídia: **33/33 PASS**. Suite total `node --test tests/*.test.mjs` foi testada exploratoriamente e contém falhas preexistentes fora do filtro de CI (sem relação comprovada com este patch); não ocultar essa limitação.
- [x] API isolada integral `python -m pytest tests/api --confcutdir=tests/api -q`: **1.308/1.308 PASS**; testes web da etapa CI: **34/34 PASS**; gate SemVer: **5/5 PASS**.
- [x] [PR de app #366](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/366) para **staging**, commit de código `cbf81558`; [CI #1168](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42526353791) **SUCCESS** nas três etapas obrigatórias (API Python, frontend, PostgreSQL descartável); workflow de estágio externo ignorado no contexto de PR, conforme configuração.
- [x] Merge **exclusivo staging** `33d73d97572ce0ee736d535f1cbfe35a11bb3314`; Render staging deploy `dep-dboep9qvcj2c739apqug` **LIVE** no commit correto. HTTP 200 em `/health`, `/api/health/ready` (`{"status":"ok"}`) e `/login`; consulta a logs após troca não mostrou request 5xx novo. `SIGTERM` de worker **antigo** durante substituição observado e esperado, não é falha do novo deploy.
- [ ] QA autenticada de Rafa no Android: MP4, espera superior a 30 s, timer, status, gravação, erro controlado e ação de atualizar galeria. Testar também lote com dois arquivos e responsividade desktop.
- [x] **Aprovação expressa de Rafa** recebida em 08/11/2026 para preparar `VERSION=3.6.2` e promover após CI/SemVer/staging LIVE; promoção efetiva e documentação de produção acompanhadas na [release 3.6.2](RELEASE-3.6.2-20261108.md).

**Fora de escopo:** alterar ou relaxar FFmpeg/sanitização, Supabase Storage/RLS, `pg_cron`, `pg_net`, publicação externa, planos, gateway, schema ou produção. Para histórico da correção anterior: [UPLOAD-MP4-PROGRESSO-20261108.md](UPLOAD-MP4-PROGRESSO-20261108.md).
