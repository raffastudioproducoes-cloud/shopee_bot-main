"""Versão única da Graph API da Meta (Facebook Login, Pages, Instagram).

Módulo sem dependências: importável tanto pelo processo da API nova
(`from apis.meta_version import ...`) quanto pelo Flask/scheduler
(`from shopee_bot.apis.meta_version import ...`).

v26.0: lançada em 2026-07-29, a mais recente em 2026-10-12 (changelog:
https://developers.facebook.com/docs/graph-api/changelog). v18.0 e v19.0
já passaram da data de expiração; v20.0 expira em 2026-09-24. Não vale para
a Threads API (graph.threads.net, versionamento próprio).
"""

GRAPH_VERSION = "v26.0"
GRAPH_URL = "https://graph.facebook.com"
GRAPH_BASE = f"{GRAPH_URL}/{GRAPH_VERSION}"
