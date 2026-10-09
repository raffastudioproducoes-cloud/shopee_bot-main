import os
import cloudinary
import cloudinary.uploader

NAME = os.environ.get("CLOUDINARY_NAME")
API_KEY = os.environ.get("CLOUDINARY_API_KEY")
SECRET = os.environ.get("CLOUDINARY_SECRET")

cloudinary.config(
    cloud_name=NAME,
    api_key=API_KEY,
    api_secret=SECRET,
    secure=True
)


MISSING_CONFIG_MESSAGE = (
    "Armazenamento de mídia não configurado no servidor "
    "(CLOUDINARY_NAME, CLOUDINARY_API_KEY e CLOUDINARY_SECRET). "
    "Posts só com texto continuam funcionando."
)


class MediaStorageNotConfigured(RuntimeError):
    pass


def ensure_configured():
    """Falha cedo com mensagem clara em vez do `ValueError: Must supply
    api_key` cru do SDK no meio do upload."""
    if not (NAME and API_KEY and SECRET):
        raise MediaStorageNotConfigured(MISSING_CONFIG_MESSAGE)
