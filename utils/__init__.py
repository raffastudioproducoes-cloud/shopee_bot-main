import os
import io
import time
import locale
import requests
from flask import Request
from PIL import Image
from shopee_bot.clogging import logger


def get_cursor_limit_from_args(request: Request):
    cursor = request.args.get('cursor')
    limit = int(request.args.get('limit', 10))
    return cursor, limit


def retry_with_backoff(
    func,
    *args,
    attempts=3,
    base_delay=1,
    exceptions=(Exception,),
    **kwargs
):
    """Chama func(*args, **kwargs), tentando novamente em falha.

    Backoff exponencial simples (base_delay * 2^tentativa). Última falha
    é relançada para o chamador decidir o que fazer.
    """
    last_err = None
    for attempt in range(attempts):
        try:
            return func(*args, **kwargs)
        except exceptions as err:
            last_err = err
            if attempt < attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Tentativa {0}/{1} falhou para {2}: {3}. "
                    "Retentando em {4}s...".format(
                        attempt + 1, attempts, func.__name__, err, delay
                    )
                )
                time.sleep(delay)
    raise last_err


def format_product_from_shopee(product):
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")

    def _local_currency(text):
        return locale.currency(float(text), grouping=True)

    product = {
        "name": product["productName"].replace('"', '\"'),
        "product_id": product["itemId"],
        "original_link": product["productLink"],
        "image": product["imageUrl"],
        "price_min": _local_currency(product["priceMin"]),
        "price_max": _local_currency(product["priceMax"]),
        "commission": _local_currency(product["commission"]),
    }
    return product


def download_image(url, save_path=None):
    try:
        # Fazer a requisição HTTP com stream para evitar carregar tudo na memória
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, stream=True, timeout=10)

        # Verificar se a requisição foi bem-sucedida
        response.raise_for_status()

        # Verificar o tipo de conteúdo
        content_type = response.headers.get('Content-Type', '').lower()
        if not content_type.startswith('image/'):
            logger.error(
                f"URL não contém uma imagem válida. Content-Type: {content_type}")
            return False

        # Baixar o conteúdo em memória para validação
        image_data = b''
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                image_data += chunk

        # Validar se é uma imagem válida usando PIL
        try:
            image = Image.open(io.BytesIO(image_data))
            image.verify()  # Verifica a integridade da imagem
        except Exception as err:
            logger.exception(f"Imagem corrompida ou inválida: {err}")
            return False

        # Se nenhum caminho for especificado, extrair o nome do arquivo da URL
        if save_path is None:
            # Remove parâmetros da URL, se houver
            file_name = url.split('/')[-1].split('?')[0]
            save_path = file_name if file_name else 'downloaded_image.jpg'

        # Criar diretório se não existir
        os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)

        # Salvar a imagem em modo binário
        with open(save_path, 'wb') as file:
            file.write(image_data)

        # Reabrir e salvar novamente para garantir formato correto
        with Image.open(io.BytesIO(image_data)) as img:
            img.save(save_path, quality=95)  # Salva com alta qualidade

        logger.debug(f"Imagem baixada e validada com sucesso: {save_path}")
        return True

    except requests.exceptions.HTTPError as err:
        logger.exception(f"Erro HTTP ao baixar a imagem: {err.response.status_code} - {err}")
    except requests.exceptions.RequestException as err:
        logger.exception(f"Erro na requisição: {err}")
    except IOError as err:
        logger.error(f"Erro ao salvar o arquivo: {err}")
    except Exception as err:
        logger.exception(f"Erro inesperado: {err}")
    return False
