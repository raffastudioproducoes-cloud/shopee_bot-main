---
title: Shopee Auto Vendas
emoji: 🛒
colorFrom: green
colorTo: blue
sdk: docker
app_port: 5000
pinned: false
---

# Shopee Auto Vendas

Plataforma de automação de divulgação de links de afiliado da Shopee e redes
sociais (Threads, X, Facebook, Instagram, TikTok, Kwai).

- Web (Flask + gunicorn) e scheduler (APScheduler) rodam no mesmo container.
- Banco: PostgreSQL externo (Supabase). Mídia: Cloudinary.
- Domínio público HTTPS (`*.hf.space`) habilita o OAuth do Threads.
