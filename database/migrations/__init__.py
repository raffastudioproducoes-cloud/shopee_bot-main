import os
from psycopg import Connection, Error, connect
from pathlib import Path
from shopee_bot.clogging import logger
from dotenv import load_dotenv
load_dotenv()

HOST = os.environ.get("SHOPEE_PG_HOST")
DB = os.environ.get("SHOPEE_PG_DB")
USER = os.environ.get("SHOPEE_PG_USER")
PASSWORD = os.environ.get("SHOPEE_PG_PASSWORD")
SSLMODE = os.environ.get("SHOPEE_PG_SSLMODE")
MIGRATIONS_DIR = Path(f"{os.getcwd()}/database/migrations/")

def _dsn() -> str:
    from urllib.parse import quote_plus
    user = quote_plus(USER) if USER else ""
    pwd = quote_plus(PASSWORD) if PASSWORD else ""
    dsn = f"postgresql://{user}:{pwd}@{HOST}/{DB}"
    if SSLMODE:
        dsn += f"?sslmode={SSLMODE}"
    return dsn


def _get_applied_migrations(conn: Connection):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    aplied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

            cur.execute("SELECT name FROM migrations;")
            return {row[0] for row in cur.fetchall()}
    except Error as err:
        logger.error(f"Erro ao recuperar migrações aplicadas {err}")
        conn.rollback()
        raise


def _apply_migration(conn: Connection, migration_file):
    try:
        with open(migration_file, "r") as f:
            sql = f.read()

        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO migrations (name) VALUES (%s);",
                (migration_file.name, )
            )
        conn.commit()
        logger.info(f"Migração {migration_file.name} aplicada.")
    except Error as err:
        logger.error(f"Erro ao aplicar migração {migration_file.name}: {err}")
        conn.rollback()
        raise


def run_migrations():
    try:
        with connect(_dsn()) as conn:
            applied_migrations = _get_applied_migrations(conn)
            migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

            for migration_file in migration_files:
                if migration_file.name not in applied_migrations:
                    logger.info(f"Aplicando migração: {migration_file.name}")
                    _apply_migration(conn, migration_file)
                else:
                    logger.info(
                        f"Migração {migration_file.name} já aplicada, ignorando."
                    )
    except Error as err:
        logger.error(f"Erro na conexão com o banco de dados: {err}")
        raise
