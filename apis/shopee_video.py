"""Cliente isolado da API Shopee Vídeo v2 (não é a API Shopee Affiliate).

Guia oficial: https://open.shopee.com/developer-guide/706 e /669. Todas as
chamadas v2.media.* e v2.video.* são User-type: assinatura HMAC-SHA256 de
partner_id + path + timestamp + access_token + user_id. O chamador obtém o
token por OAuth (api/shopee_video_tokens.py) e passa permission_granted
explícito. Nunca registrar chaves, assinaturas nem tokens. post_video é
chamado uma única vez: em resposta incerta, reconciliar por get_video_list.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import time
from typing import BinaryIO, Callable

import requests

from .shopee_video_host import api_base_url


MAX_VIDEO_SIZE = 1024 * 1024 * 1024  # limite da API
MIN_VIDEO_SECONDS = 3
MAX_VIDEO_SECONDS_BR = 60  # limite documentado na ajuda Shopee Brasil
MAX_CAPTION_LENGTH = 150
MAX_LINKED_PRODUCTS = 6
# Parâmetros de init_video_upload sem valor oficial publicado para vídeo de
# criador: a confirmar no primeiro teste real.
INIT_UPLOAD_BUSINESS = 3
INIT_UPLOAD_SCENE = 1
UPLOAD_STATUSES = frozenset({"INITIATED", "UPLOADING", "UPLOADED", "PROCESSING",
                             "SUCCEEDED", "FAILED", "CANCELLED"})
ALLOWED_PATHS = frozenset({
    "/api/v2/media/init_video_upload",
    "/api/v2/media/upload_video_part",
    "/api/v2/media/complete_video_upload",
    "/api/v2/media/get_video_upload_result",
    "/api/v2/video/get_cover_list",
    "/api/v2/video/edit_video_info",
    "/api/v2/video/post_video",
    "/api/v2/video/get_video_list",
    "/api/v2/video/get_video_detail",
    "/api/v2/video/delete_video",
    "/api/v2/video/get_video_performance_list",
    "/api/v2/video/get_video_detail_performance",
})


class ShopeeVideoError(Exception):
    """Falha controlada, sem credenciais ou corpos de resposta sensíveis."""


class ShopeeVideoTransportError(ShopeeVideoError):
    """Sem resposta válida (rede/timeout/HTTP): o desfecho remoto é incerto."""


class ShopeeVideoRejected(ShopeeVideoError):
    """A Shopee respondeu com erro explícito: a operação não foi aceita."""

    def __init__(self, message: str, *, code: str = "", detail: str = "", request_id: str = "") -> None:
        super().__init__(message)
        # Só texto curto de diagnóstico; nunca o corpo bruto da resposta.
        self.code, self.detail, self.request_id = code, detail, request_id


class ShopeeVideoTimeout(ShopeeVideoError):
    """O processamento não terminou no prazo: resultado "unknown", não falha."""


@dataclass(frozen=True)
class ShopeeVideoAuthorization:
    partner_id: int
    partner_key: str
    user_id: int
    access_token: str
    # TRUE somente após verificação do escopo no aplicativo aprovado + OAuth.
    permission_granted: bool = False


class ShopeeVideoClient:
    """Métodos para upload, publicação e consulta. Não persiste tokens nem posts."""

    def __init__(
        self, authorization: ShopeeVideoAuthorization, *,
        sandbox: bool = True, enabled: bool = False,
        session: requests.Session | None = None,
    ) -> None:
        if not enabled or not authorization.permission_granted:
            raise ShopeeVideoError(
                "Shopee Vídeo indisponível: aplicativo e conta precisam de autorização."
            )
        if not (authorization.partner_id > 0 and authorization.partner_key
                and authorization.user_id > 0 and authorization.access_token):
            raise ShopeeVideoError("Credenciais OAuth Shopee Vídeo incompletas.")
        self.authorization = authorization
        self.host = api_base_url(sandbox=sandbox)
        self.session = session if session is not None else requests.Session()
        self._succeeded: set[str] = set()

    def _params(self, path: str) -> dict:
        auth = self.authorization
        timestamp = int(time.time())
        base = f"{auth.partner_id}{path}{timestamp}{auth.access_token}{auth.user_id}"
        signature = hmac.new(auth.partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()
        return {"partner_id": auth.partner_id, "timestamp": timestamp, "sign": signature,
                "access_token": auth.access_token, "user_id": auth.user_id}

    def _send(self, path: str, method: str, params: dict, payload: dict | None,
              file_part: tuple[str, bytes] | None):
        url = self.host + path
        if file_part is not None:
            return self.session.post(
                url, params=params, data=payload,
                files={"part_content": (file_part[0], file_part[1], "video/mp4")},
                timeout=(10, 120),
            )
        if method == "GET":
            return self.session.get(url, params={**params, **(payload or {})}, timeout=(10, 30))
        return self.session.post(url, params=params, json=payload, timeout=(10, 60))

    def _request(
        self, path: str, *, method: str = "POST", payload: dict | None = None,
        file_part: tuple[str, bytes] | None = None,
    ) -> dict:
        # Somente endpoints fixos conhecidos; o host não vem do usuário.
        if path not in ALLOWED_PATHS:
            raise ShopeeVideoError("Endpoint de Shopee Vídeo não autorizado.")
        try:
            response = self._send(path, method, self._params(path), payload, file_part)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ShopeeVideoTransportError("Não foi possível obter resposta válida da Shopee.") from exc
        if not isinstance(body, dict):
            raise ShopeeVideoError("Resposta da Shopee fora do formato esperado.")
        if body.get("error"):
            # Não devolver o corpo, URLs assinadas nem tokens ao cliente.
            raise ShopeeVideoRejected(
                "Shopee recusou a operação: " + str(body["error"])[:75],
                code=str(body["error"])[:75], detail=str(body.get("message") or "")[:200],
                request_id=str(body.get("request_id") or "")[:100],
            )
        return body

    def _response(self, path: str, **kwargs) -> dict:
        data = self._request(path, **kwargs).get("response")
        return data if isinstance(data, dict) else {}

    # ── Upload ────────────────────────────────────────────────────────────
    def init_upload(self, file_name: str, file_size: int, duration: int | None) -> tuple[str, int]:
        if not file_name.lower().endswith(".mp4"):
            raise ShopeeVideoError("Shopee Vídeo exige arquivo MP4.")
        if not 0 < file_size <= MAX_VIDEO_SIZE:
            raise ShopeeVideoError("Vídeo vazio ou acima de 1 GB.")
        if duration is not None and not MIN_VIDEO_SECONDS <= duration <= MAX_VIDEO_SECONDS_BR:
            raise ShopeeVideoError("O vídeo precisa ter de 3 a 60 segundos.")
        payload = {"business": INIT_UPLOAD_BUSINESS, "scene": INIT_UPLOAD_SCENE,
                   "file_name": file_name, "file_size": file_size}
        if duration is not None:
            payload["duration"] = duration
        data = self._response("/api/v2/media/init_video_upload", payload=payload)
        upload_id, part_size = data.get("video_upload_id"), data.get("part_size")
        if not isinstance(upload_id, str) or not upload_id or not isinstance(part_size, int) or part_size <= 0:
            raise ShopeeVideoError("Shopee não retornou ID ou tamanho do bloco de upload.")
        return upload_id, part_size

    def upload_parts(self, upload_id: str, stream: BinaryIO, part_size: int, file_size: int) -> None:
        if not upload_id or not 0 < part_size <= MAX_VIDEO_SIZE or not 0 < file_size <= MAX_VIDEO_SIZE:
            raise ShopeeVideoError("Parâmetros inválidos de upload.")
        total, sequence = 0, 0
        while total < file_size:
            part = stream.read(min(part_size, file_size - total))
            if not isinstance(part, bytes) or not part:
                raise ShopeeVideoError("Arquivo incompleto durante o upload.")
            # Nome e MD5 descrevem exatamente os bytes deste bloco.
            self._request("/api/v2/media/upload_video_part", payload={
                "video_upload_id": upload_id, "part_seq": sequence,
                "part_md5": hashlib.md5(part).hexdigest(),  # checksum exigido pela Shopee
            }, file_part=(f"{upload_id}_part{sequence}.mp4", part))
            total += len(part)
            sequence += 1

    def complete_upload(self, upload_id: str) -> None:
        self._request("/api/v2/media/complete_video_upload", payload={"video_upload_id": upload_id})

    def upload_file(self, stream: BinaryIO, file_name: str, size: int, duration: int | None) -> str:
        """Upload em partes de um MP4; a transcodificação é assíncrona (ver wait_upload_result)."""
        if not hasattr(stream, "read"):
            raise ShopeeVideoError("Arquivo de mídia inválido.")
        upload_id, part_size = self.init_upload(file_name, size, duration)
        self.upload_parts(upload_id, stream, part_size, size)
        self.complete_upload(upload_id)
        return upload_id

    def get_upload_status(self, upload_id: str) -> str:
        data = self._response("/api/v2/media/get_video_upload_result", method="GET",
                              payload={"video_upload_id": upload_id})
        status = data.get("status")
        if status not in UPLOAD_STATUSES:
            raise ShopeeVideoError("Shopee retornou estado de processamento desconhecido.")
        if status == "SUCCEEDED":
            self._succeeded.add(upload_id)
        return status

    def wait_upload_result(
        self, upload_id: str, *, timeout_s: float = 300, interval_s: float = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> str:
        """Aguarda SUCCEEDED. FAILED/CANCELLED → erro; prazo esgotado → ShopeeVideoTimeout."""
        deadline = time.monotonic() + timeout_s
        while True:
            status = self.get_upload_status(upload_id)
            if status == "SUCCEEDED":
                return status
            if status in ("FAILED", "CANCELLED"):
                raise ShopeeVideoError("A Shopee recusou o processamento do vídeo. Revise o arquivo MP4.")
            if time.monotonic() >= deadline:
                raise ShopeeVideoTimeout("A Shopee não terminou de processar o vídeo no prazo.")
            sleep(interval_s)

    # ── Metadados e publicação ────────────────────────────────────────────
    def get_covers(self, upload_id: str) -> list[str]:
        data = self._response("/api/v2/video/get_cover_list", method="GET",
                              payload={"video_upload_id": upload_id})
        covers = data.get("image_url_list") or []
        if not isinstance(covers, list):
            raise ShopeeVideoError("Capas inválidas na resposta da Shopee.")
        return [url for url in covers if isinstance(url, str) and url.startswith("https://")]

    @staticmethod
    def _check_video_info(upload_id: str, caption: str, cover_url: str | None,
                          product_item_ids: list[int], ai_assisted: object) -> None:
        if not upload_id or len(caption) > MAX_CAPTION_LENGTH or not caption.strip():
            raise ShopeeVideoError("Legenda obrigatória de até 150 caracteres.")
        if cover_url is not None and not cover_url.startswith("https://"):
            raise ShopeeVideoError("A capa deve ser uma URL HTTPS da Shopee.")
        if len(product_item_ids) > MAX_LINKED_PRODUCTS or any(i <= 0 for i in product_item_ids):
            raise ShopeeVideoError("Máximo de seis produtos Shopee válidos por vídeo.")
        if len(set(product_item_ids)) != len(product_item_ids):
            raise ShopeeVideoError("Não repita produtos vinculados ao vídeo.")
        if not isinstance(ai_assisted, bool):
            raise ShopeeVideoError("Informe se o vídeo foi gerado com IA (aigc_label).")

    @staticmethod
    def _scheduled_info(scheduled_at_ms: int | None) -> dict:
        if scheduled_at_ms is None:
            return {"scheduled_post": False}
        now_ms = int(time.time() * 1000)
        if not now_ms + 15 * 60_000 <= scheduled_at_ms <= now_ms + 30 * 86400_000:
            raise ShopeeVideoError("Agendamento permitido entre 15 minutos e 30 dias.")
        return {"scheduled_post": True, "scheduled_post_time": scheduled_at_ms}

    def set_video_info(
        self, upload_id: str, *, caption: str, cover_url: str | None,
        product_item_ids: list[int], ai_assisted: bool,
        allow_duet: bool = False, allow_stitch: bool = False,
        scheduled_at_ms: int | None = None,
    ) -> None:
        """edit_video_info: rascunho editável até post_video. cover_url=None segue sem capa."""
        self._check_video_info(upload_id, caption, cover_url, product_item_ids, ai_assisted)
        item = {
            "video_upload_id": upload_id,
            "caption": caption.strip(),
            "item_info": [{"item_id": item_id} for item_id in product_item_ids],
            "allow_info": {"allow_duet": allow_duet, "allow_stitch": allow_stitch},
            "scheduled_info": self._scheduled_info(scheduled_at_ms),
        }
        if cover_url is not None:
            item["cover_image_url"] = cover_url
        result = self._response("/api/v2/video/edit_video_info",
                                payload={"aigc_label": ai_assisted, "video_upload_list": [item]})
        if upload_id not in (result.get("success_list") or []):
            raise ShopeeVideoError("Shopee não confirmou os metadados do vídeo.")

    def post_video(self, upload_id: str, *, upload_status: str | None = None) -> dict:
        """Chamar APENAS UMA VEZ, depois de wait_upload_result (ou com upload_status
        "SUCCEEDED" já confirmado). Em resposta incerta, reconciliar por get_video_list.
        """
        if upload_id not in self._succeeded and upload_status != "SUCCEEDED":
            raise ShopeeVideoError("Vídeo ainda não foi processado com sucesso.")
        result = self._response("/api/v2/video/post_video",
                                payload={"video_upload_id_list": [upload_id]})
        success = result.get("success_list") or []
        if not success:
            raise ShopeeVideoError("Shopee não confirmou a publicação do vídeo.")
        return {"video_upload_id": upload_id, "confirmation": success}

    # ── Consulta e gestão (formato dos campos a confirmar no primeiro teste real) ──
    # A Shopee exige list_type (1 ou 2): resposta real "list_type must be 1,2". O significado de
    # cada valor (publicados x rascunhos) é a confirmar; por isso a conciliação olha os dois.
    LIST_TYPES = (1, 2)

    def get_video_list(self, *, page_no: int = 1, page_size: int = 20, list_type: int = 1) -> dict:
        if list_type not in self.LIST_TYPES:
            raise ShopeeVideoError("list_type inválido")
        return self._response("/api/v2/video/get_video_list", method="GET",
                              payload={"page_no": page_no, "page_size": page_size,
                                       "list_type": list_type})

    def find_posted_video(self, upload_id: str) -> dict | None:
        """Procura na primeira página o vídeo publicado a partir deste upload."""
        for list_type in self.LIST_TYPES:
            videos = self.get_video_list(list_type=list_type).get("video_list") or []
            found = next((v for v in videos if isinstance(v, dict)
                          and v.get("video_upload_id") == upload_id), None)
            if found:
                return found
        return None

    def get_video_detail(self, video_id: str) -> dict:
        return self._response("/api/v2/video/get_video_detail", method="GET",
                              payload={"video_id": video_id})

    def delete_video(self, video_id: str) -> dict:
        return self._response("/api/v2/video/delete_video", payload={"video_id": video_id})

    def get_video_performance_list(self, *, page_no: int = 1, page_size: int = 20) -> dict:
        return self._response("/api/v2/video/get_video_performance_list", method="GET",
                              payload={"page_no": page_no, "page_size": page_size})

    def get_video_detail_performance(self, video_id: str) -> dict:
        return self._response("/api/v2/video/get_video_detail_performance", method="GET",
                              payload={"video_id": video_id})
