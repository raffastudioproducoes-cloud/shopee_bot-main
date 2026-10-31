"""Cliente isolado da API Shopee Vídeo v2 (não é a API Shopee Affiliate).

A integração NÃO é ativada em produção neste módulo. O chamador deve obter,
por OAuth autorizado, user_id/access_token da conta Shopee e passar um
permission_granted explícito. Nunca registrar chaves, assinaturas nem tokens.
Publicação e retries devem ser coordenados por uma fila persistente com
idempotência: não chamar post_video novamente após confirmação incerta.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import io
import time
from typing import BinaryIO

import requests


PRODUCTION = "https://partner.shopeemobile.com"
SANDBOX = "https://partner.test-stable.shopeemobile.com"
MAX_VIDEO_SIZE = 1024 * 1024 * 1024  # limite da API
MAX_VIDEO_SECONDS_BR = 60  # limite documentado na ajuda Shopee Brasil
MAX_CAPTION_LENGTH = 150
MAX_LINKED_PRODUCTS = 6


class ShopeeVideoError(Exception):
    """Falha controlada, sem credenciais ou corpos de resposta sensíveis."""


@dataclass(frozen=True)
class ShopeeVideoAuthorization:
    partner_id: int
    partner_key: str
    user_id: int
    access_token: str
    # TRUE somente após verificação do escopo no aplicativo aprovado + OAuth.
    permission_granted: bool = False


class ShopeeVideoClient:
    """Métodos para upload e publicação. Não persiste tokens nem posts."""

    def __init__(
        self, authorization: ShopeeVideoAuthorization, *,
        sandbox: bool = True, enabled: bool = False,
        session: requests.Session | None = None,
    ) -> None:
        self.authorization = authorization
        self.host = SANDBOX if sandbox else PRODUCTION
        self.session = session if session is not None else requests.Session()
        if not enabled or not authorization.permission_granted:
            raise ShopeeVideoError(
                "Shopee Vídeo indisponível: aplicativo e conta precisam de autorização."
            )
        if not (authorization.partner_id > 0 and authorization.partner_key
                and authorization.user_id > 0 and authorization.access_token):
            raise ShopeeVideoError("Credenciais OAuth Shopee Vídeo incompletas.")

    def _request(
        self, path: str, *, method: str = "POST", payload: dict | None = None,
        file_part: bytes | None = None, user_scope: bool = False,
    ) -> dict:
        # Somente endpoints fixos conhecidos; host não vem do usuário.
        if path not in {
            "/api/v2/media/init_video_upload",
            "/api/v2/media/upload_video_part",
            "/api/v2/media/complete_video_upload",
            "/api/v2/media/get_video_upload_result",
            "/api/v2/video/get_cover_list",
            "/api/v2/video/edit_video_info",
            "/api/v2/video/post_video",
        }:
            raise ShopeeVideoError("Endpoint de Shopee Vídeo não autorizado.")
        auth = self.authorization
        timestamp = int(time.time())
        signature_base = f"{auth.partner_id}{path}{timestamp}"
        if user_scope:
            signature_base += f"{auth.access_token}{auth.user_id}"
        signature = hmac.new(
            auth.partner_key.encode(), signature_base.encode(), hashlib.sha256
        ).hexdigest()
        params: dict[str, str | int] = {
            "partner_id": auth.partner_id, "timestamp": timestamp, "sign": signature,
        }
        if user_scope:
            params.update(access_token=auth.access_token, user_id=auth.user_id)
        try:
            if file_part is not None:
                response = self.session.post(
                    self.host + path, params=params,
                    data=payload,
                    files={"part_content": ("part.mp4", file_part, "video/mp4")},
                    timeout=(10, 120),
                )
            elif method == "GET":
                response = self.session.get(
                    self.host + path, params={**params, **(payload or {})},
                    timeout=(10, 30),
                )
            else:
                response = self.session.post(
                    self.host + path, params=params, json=payload,
                    timeout=(10, 60),
                )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ShopeeVideoError("Não foi possível obter resposta válida da Shopee.") from exc

        if not isinstance(body, dict):
            raise ShopeeVideoError("Resposta da Shopee fora do formato esperado.")
        if body.get("error"):
            # Não devolver o corpo, URLs assinadas nem tokens ao cliente.
            reason = str(body["error"])[:75]
            raise ShopeeVideoError("Shopee recusou a operação: " + reason)
        return body

    def init_upload(self, file_name: str, file_size: int, duration: int) -> tuple[str, int]:
        if not file_name.lower().endswith(".mp4"):
            raise ShopeeVideoError("Shopee Vídeo exige arquivo MP4.")
        if not 0 < file_size <= MAX_VIDEO_SIZE:
            raise ShopeeVideoError("Vídeo vazio ou acima de 1 GB.")
        if not 3 <= duration <= MAX_VIDEO_SECONDS_BR:
            raise ShopeeVideoError("O vídeo precisa ter de 3 a 60 segundos.")
        data = self._request("/api/v2/media/init_video_upload", payload={
            "business": 3, "scene": 1, "file_name": file_name,
            "file_size": file_size, "duration": duration,
        }).get("response") or {}
        upload_id = data.get("video_upload_id")
        part_size = data.get("part_size")
        if not isinstance(upload_id, str) or not upload_id or not isinstance(part_size, int) or part_size <= 0:
            raise ShopeeVideoError("Shopee não retornou ID ou tamanho do bloco de upload.")
        return upload_id, part_size

    def upload_parts(self, upload_id: str, stream: BinaryIO, part_size: int, file_size: int) -> None:
        if not upload_id or not 0 < part_size <= MAX_VIDEO_SIZE or not 0 < file_size <= MAX_VIDEO_SIZE:
            raise ShopeeVideoError("Parâmetros inválidos de upload.")
        total = 0
        sequence = 0
        while total < file_size:
            part = stream.read(min(part_size, file_size - total))
            if not isinstance(part, bytes) or not part:
                raise ShopeeVideoError("Arquivo incompleto durante o upload.")
            self._request("/api/v2/media/upload_video_part", payload={
                "video_upload_id": upload_id, "part_seq": sequence,
                "part_md5": hashlib.md5(part).hexdigest(),  # checksum exigido pela Shopee
            }, file_part=part)
            total += len(part)
            sequence += 1

    def complete_upload(self, upload_id: str) -> None:
        self._request("/api/v2/media/complete_video_upload",
                      payload={"video_upload_id": upload_id})

    def get_upload_status(self, upload_id: str) -> str:
        data = self._request(
            "/api/v2/media/get_video_upload_result", method="GET",
            payload={"video_upload_id": upload_id},
        ).get("response") or {}
        status = data.get("status")
        if status not in {"INITIATED", "UPLOADING", "UPLOADED", "PROCESSING",
                          "SUCCEEDED", "FAILED", "CANCELLED"}:
            raise ShopeeVideoError("Shopee retornou estado de processamento desconhecido.")
        return status

    def get_covers(self, upload_id: str) -> list[str]:
        data = self._request(
            "/api/v2/video/get_cover_list", method="GET",
            payload={"video_upload_id": upload_id}, user_scope=True,
        ).get("response") or {}
        covers = data.get("image_url_list") or []
        if not isinstance(covers, list):
            raise ShopeeVideoError("Capas inválidas na resposta da Shopee.")
        return [url for url in covers if isinstance(url, str) and url.startswith("https://")]

    def set_video_info(
        self, upload_id: str, *, caption: str, cover_url: str,
        product_item_ids: list[int], ai_assisted: bool,
        allow_duet: bool = False, allow_stitch: bool = False,
        scheduled_at_ms: int | None = None,
    ) -> None:
        if not upload_id or len(caption) > MAX_CAPTION_LENGTH or not caption.strip():
            raise ShopeeVideoError("Legenda obrigatória de até 150 caracteres.")
        if not cover_url.startswith("https://"):
            raise ShopeeVideoError("A capa deve ser uma URL HTTPS da Shopee.")
        if len(product_item_ids) > MAX_LINKED_PRODUCTS or any(i <= 0 for i in product_item_ids):
            raise ShopeeVideoError("Máximo de seis produtos Shopee válidos por vídeo.")
        if len(set(product_item_ids)) != len(product_item_ids):
            raise ShopeeVideoError("Não repita produtos vinculados ao vídeo.")
        scheduled: dict[str, bool | int] = {"scheduled_post": False}
        if scheduled_at_ms is not None:
            now_ms = int(time.time() * 1000)
            if not now_ms + 15 * 60_000 <= scheduled_at_ms <= now_ms + 30 * 86400_000:
                raise ShopeeVideoError("Agendamento permitido entre 15 minutos e 30 dias.")
            scheduled = {"scheduled_post": True, "scheduled_post_time": scheduled_at_ms}
        payload = {
            "aigc_label": ai_assisted,
            "video_upload_list": [{
                "video_upload_id": upload_id,
                "caption": caption.strip(),
                "cover_image_url": cover_url,
                "item_info": [{"item_id": item_id} for item_id in product_item_ids],
                "allow_info": {"allow_duet": allow_duet, "allow_stitch": allow_stitch},
                "scheduled_info": scheduled,
            }],
        }
        result = self._request(
            "/api/v2/video/edit_video_info", payload=payload, user_scope=True,
        ).get("response") or {}
        if upload_id not in (result.get("success_list") or []):
            raise ShopeeVideoError("Shopee não confirmou os metadados do vídeo.")

    def post_video(self, upload_id: str) -> dict:
        """Chamar APENAS UMA VEZ. Em resposta incerta, reconciliar por get_video_list.

        Nunca repetir automaticamente: a Shopee pode publicar mesmo se a rede cair.
        """
        if self.get_upload_status(upload_id) != "SUCCEEDED":
            raise ShopeeVideoError("Vídeo ainda não foi processado com sucesso.")
        result = self._request(
            "/api/v2/video/post_video",
            payload={"video_upload_id_list": [upload_id]}, user_scope=True,
        ).get("response") or {}
        success = result.get("success_list") or []
        if not success:
            raise ShopeeVideoError("Shopee não confirmou a publicação do vídeo.")
        return {"video_upload_id": upload_id, "confirmation": success}

    def upload_file(self, stream: BinaryIO, file_name: str, size: int, duration: int) -> str:
        """Upload de um MP4 já validado por ffprobe; transcodificação é assíncrona."""
        if not isinstance(stream, (io.BufferedIOBase, io.RawIOBase)) and not hasattr(stream, "read"):
            raise ShopeeVideoError("Arquivo de mídia inválido.")
        upload_id, part_size = self.init_upload(file_name, size, duration)
        self.upload_parts(upload_id, stream, part_size, size)
        self.complete_upload(upload_id)
        return upload_id
