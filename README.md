# Shopee Bot
É uma plataforma de automação da divulgação de links de afiliado. Atualmente funciona apenas
com a Shopee. O projeto é divido em módulos, porém para fins práticas basicamente há três módulos
[Web](./web/), e [Scheduler](./scheduler/). O restante dos módulos existem como 
dependências.

## Web
Interface da plataforma, é por ela que se cadastra usuários, produtos, lista de produtos, onde se
configura os bots e coloca as credenciais. Implementado em Flask rodando num docker com gunicorn.

## Scheduler
A lógica das tarefas recorrentes ficam nele. Faz uso do banco de dados para atualizar que tarefas
deve realizar e quando.

## Estrutura do Projeto
    apis/               <- wrapper simples para as APIs utilizadas
    database/           <- wrapper de acesso ao banco de dados, cada
                           arquivo representa uma tabela no BD.
    nginx/              <- configuração do proxy reverso
    scheduler/
    utils/
    web/
    clogging.py         <- logger personalizado, compartilhado
    gunicorn.conf.py    <- configuração de produção

## Rodando Local
Crie um ambiente virtual na pasta raiz ``python -m venv .venv``, instale os pacotes necessários
``pip install -r requirements.txt`` e configure o ambiente ``cp .env-example .env`` alterando
o que for necessário.

### Uso
    source .venv/bin/active
    flask --debug --app web run


## Rodando em Produção
Crie a imagem com ``COMPOSE_BAKE=true docker build --no-cache -t shopee-bot-app .``, gere os certificados
para o Nginx ``openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 
-subj "/C=BR/ST=Rio de Janeiro/L=Rio de Janeiro/O=Bro Inc./OU=TI/CN=localhost"``.

Crie as [variáveis de ambiente](https://help.ubuntu.com/community/EnvironmentVariables#Session-wide_environment_variables)
para a plataforma. Você pode usar o ``.env-example`` como referência.

- ``POSTGRES_HOST``
- ``POSTGRES_USER``
- ``POSTGRES_PASSOWRD``
- ``POSTGRES_DB``
- ``CLOUDINARY_NAME``
- ``CLOUDINARY_API_KEY``
- ``CLOUDINARY_SECRET``
- ``THREADS_APP_ID``
- ``THREADS_SECRET``
- ``FLASK_SESSION_SECRET``
- ``FLASK_UPLOAD_FOLDER``
- ``FLASK_MAX_CONTENT_LENGTH``
- ``LOG_LEVEL``

### Uso
    docker compose up -d
