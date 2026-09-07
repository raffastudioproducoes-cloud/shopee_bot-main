"""
APIs do ShopeeAutoVendas - Módulos de integração externa.

Nota: Alguns submódulos podem requerer dependências extras (cloudinary, etc.)
que não estão instaladas no ambiente local. Use imports diretos quando necessário:
    from apis.threads import ThreadsAPI
    from apis.threads_poster import post_to_threads
    from apis.x import XAPI
    from apis.facebook import FacebookAPI
    from apis.instagram import InstagramAPI
    from apis.tiktok import TikTokAPI
    from apis.kwai import KwaiAPI
"""

__all__ = [
    "threads",
    "shopee",
    "llm",
    "cloudinary",
    "x",
    "facebook",
    "instagram",
    "tiktok",
    "kwai",
]
