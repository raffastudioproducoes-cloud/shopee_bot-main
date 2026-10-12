# Dockerfile para Hugging Face Spaces
# Mantém o Dockerfile original (docker-compose + nginx) intacto.
# No HF: copie este conteúdo para "Dockerfile" na raiz do repo do Space
# e o README.hfspaces.md para "README.md".

# Estágio 1: build do frontend React (frontend/, Vite). Node 22 exigido
# pelo Vite 6 (^18.19 / ^20.11 / >=22) — usamos 22 direto, sem meio-termo.
# Resultado (frontend/dist) é copiado pro estágio Python abaixo; nada de
# Node sobra na imagem final.
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
# O Vite injeta a versao definida na raiz do repositorio no bundle.
COPY VERSION /app/VERSION
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim

# tini garante shutdown limpo; locales evita warning do pt_BR
RUN apt update && apt install locales tini -y

RUN sed -i '/pt_BR.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG=pt_BR.UTF-8
ENV LANGUAGE=pt_BR:pt:en
ENV LC_ALL=pt_BR.UTF-8

# HF Spaces: app escuta na porta definida em app_port (README do space = 5000)
WORKDIR /shopee_bot

# Pacote shopee_bot resolve a partir da raiz (/)
# (o docker-compose seta PYTHONPATH=/; sem isso o import shopee_bot quebra)
ENV PYTHONPATH=/

# Instala deps antes de copiar o codigo (cache de layer)
# api/requirements.txt vai no mesmo venv/layer do requirements.txt da raiz —
# os dois processos (gunicorn/Flask + uvicorn/FastAPI) rodam no mesmo container.
COPY requirements.txt .
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api/requirements.txt

# Usuário sem privilégios: o app não precisa de root em runtime.
RUN useradd --system --uid 10001 --home-dir /shopee_bot app

# Copia o app (a pasta raiz tem __init__.py -> vira o pacote shopee_bot)
COPY --chown=app:app . .

# Build do frontend (estágio Node acima) -> frontend/dist, servido pelo
# Flask via web/routes/spa.py quando LEGACY_PANEL_ENABLED != true
COPY --from=frontend-build --chown=app:app /app/frontend/dist ./frontend/dist

EXPOSE 5000

# Diretórios de escrita em runtime (relativos ao WORKDIR): FLASK_UPLOAD_FOLDER=upload
# (web/__init__.py) e web/media (api/routers/posts.py). /shopee_bot é root-owned;
# sem isto o makedirs('upload') do boot falha como usuário app.
RUN mkdir -p upload web/media && chown app:app /shopee_bot upload web/media

USER app

# /health do Flask (web/__init__.py), público e sem auth. $PORT é injetada
# pela plataforma (default 5000). start-period cobre o boot do scheduler.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 CMD ["python", "-c", "import os,urllib.request as u;u.urlopen('http://127.0.0.1:'+os.environ.get('PORT','5000')+'/health',timeout=4)"]

# Scheduler sobe dentro do gunicorn (hook post_fork -> init_scheduler);
# on_starting sobe o processo uvicorn da API FastAPI (ver gunicorn.conf.py)
ENTRYPOINT ["tini", "--"]
CMD ["gunicorn", "web:app", "--config=gunicorn.conf.py"]
