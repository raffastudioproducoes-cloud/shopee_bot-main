# Dockerfile para Hugging Face Spaces
# Mantém o Dockerfile original (docker-compose + nginx) intacto.
# No HF: copie este conteúdo para "Dockerfile" na raiz do repo do Space
# e o README.hfspaces.md para "README.md".
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

# Copia o app (a pasta raiz tem __init__.py -> vira o pacote shopee_bot)
COPY . .

EXPOSE 5000

# Scheduler sobe dentro do gunicorn (hook post_fork -> init_scheduler);
# on_starting sobe o processo uvicorn da API FastAPI (ver gunicorn.conf.py)
ENTRYPOINT ["tini", "--"]
CMD ["gunicorn", "web:app", "--config=gunicorn.conf.py"]
