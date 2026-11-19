"""Duração e dimensões de um MP4 sem baixar o arquivo inteiro (requisições Range).

Lê só os cabeçalhos das caixas de topo e o `moov` (metadados), nunca o `mdat`.
Usado para validar Reels do Facebook antes de chamar a Meta. Qualquer falha
(servidor sem Range, MP4 fora do padrão, rede) devolve None: quem chama decide.
A URL (assinada) nunca vai para log nem para mensagem de erro.
"""

import struct

import requests

TIMEOUT = (10, 30)  # s (conexão, leitura)
MAX_MOOV_BYTES = 8 * 1024 * 1024
MAX_TOP_BOXES = 64
_ROTATED = (0x10000, -0x10000)


def _read(url, start, length):
    """Bytes [start, start+length) via Range; None se o servidor ignorar o Range."""
    with requests.get(url, headers={"Range": f"bytes={start}-{start + length - 1}"},
                      stream=True, timeout=TIMEOUT) as res:
        if res.status_code != 206:
            return None
        data = res.raw.read(length + 1)
    return data[:length]


def _boxes(data):
    """(tipo, corpo) das caixas filhas de um bloco já lido."""
    offset = 0
    while offset + 8 <= len(data):
        size, kind = struct.unpack(">I4s", data[offset:offset + 8])
        header = 8
        if size == 1 and offset + 16 <= len(data):
            size, header = struct.unpack(">Q", data[offset + 8:offset + 16])[0], 16
        elif size == 0:
            size = len(data) - offset
        if size < header:
            return
        yield kind, data[offset + header:offset + size]
        offset += size


def _child(data, kind):
    return next((body for name, body in _boxes(data) if name == kind), None)


def _movie_seconds(mvhd):
    if mvhd[0] == 1:
        timescale, duration = struct.unpack(">IQ", mvhd[20:32])
    else:
        timescale, duration = struct.unpack(">II", mvhd[12:20])
    return duration / timescale if timescale else None


def _video_size(trak):
    """(largura, altura) exibidas da faixa de vídeo, considerando rotação de 90°."""
    hdlr = _child(_child(trak, b"mdia") or b"", b"hdlr")
    tkhd = _child(trak, b"tkhd")
    if not hdlr or hdlr[8:12] != b"vide" or not tkhd:
        return None
    base = 52 if tkhd[0] == 1 else 40  # início da matriz 3x3
    a, b = struct.unpack(">ii", tkhd[base:base + 8])
    width, height = (value >> 16 for value in struct.unpack(">II", tkhd[base + 36:base + 44]))
    if a == 0 and b in _ROTATED:
        width, height = height, width
    return (width, height) if width and height else None


def parse_moov(moov):
    mvhd = _child(moov, b"mvhd")
    duration = _movie_seconds(mvhd) if mvhd else None
    size = next((found for kind, body in _boxes(moov) if kind == b"trak"
                 for found in [_video_size(body)] if found), None)
    if duration is None or size is None:
        return None
    return {"width": size[0], "height": size[1], "duration": duration}


def probe_mp4(url):
    """{"width", "height", "duration"} ou None."""
    try:
        offset = 0
        for index in range(MAX_TOP_BOXES):
            head = _read(url, offset, 16)
            if not head or len(head) < 8:
                return None
            size, kind = struct.unpack(">I4s", head[:8])
            header = 8
            if size == 1 and len(head) >= 16:
                size, header = struct.unpack(">Q", head[8:16])[0], 16
            if index == 0 and kind != b"ftyp":
                return None  # não é MP4/ISO BMFF
            if kind == b"moov":
                if not header < size <= MAX_MOOV_BYTES:
                    return None
                body = _read(url, offset + header, size - header)
                return parse_moov(body) if body and len(body) == size - header else None
            if size < header:
                return None  # size 0 (até o fim) antes do moov: sem metadados
            offset += size
    except (requests.RequestException, struct.error, ValueError, ZeroDivisionError):
        return None
    return None
