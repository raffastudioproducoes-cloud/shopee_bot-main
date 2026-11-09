"""Confirma que o Render já serve a versão esperada (o deploy é feito pelo autoDeploy).

Por que existe: o CD antigo só "disparava" um hook de deploy e, sem o segredo, terminava
verde sem fazer nada. O Render já faz deploy automático a cada push (autoDeploy=yes), então
o CD passou a VERIFICAR: consulta a página pública até aparecer `Versão X.Y.Z` (injetada no
HTML pelo build do frontend a partir do arquivo VERSION) ou esgotar o prazo.

Só biblioteca padrão. Códigos de saída: 0 = versão esperada no ar; 1 = prazo esgotado;
2 = uso inválido.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Callable
from urllib.parse import urlsplit

VERSION_RE = re.compile(r"Vers[ãa]o\s+(\d+\.\d+\.\d+)")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
USER_AGENT = "auto-orbital-cd-verify/1.0"


def fetch_version(url: str, timeout: float = 20.0) -> tuple[int | None, str | None]:
    """(status HTTP, versão encontrada). (None, None) se não houve resposta."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (https validado)
            body = response.read(512 * 1024).decode("utf-8", errors="replace")
            match = VERSION_RE.search(body)
            return response.status, match.group(1) if match else None
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None


def wait_for_version(
    url: str,
    expected: str,
    timeout_s: float,
    interval_s: float,
    *,
    fetch: Callable[[str], tuple[int | None, str | None]] = fetch_version,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
    log: Callable[[str], None] = print,
) -> tuple[bool, str]:
    """Repete a consulta até a versão esperada aparecer. Tolera cold start e 5xx."""
    deadline = now() + timeout_s
    attempt, last = 0, "sem resposta"
    while True:
        attempt += 1
        status, version = fetch(url)
        last = f"HTTP {status}, versão {version or 'não encontrada'}" if status else "sem resposta"
        log(f"[{attempt}] {url} -> {last}")
        if status == 200 and version == expected:
            return True, last
        if now() + interval_s > deadline:
            return False, last
        sleep(interval_s)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expect-version", required=True)
    parser.add_argument("--timeout", type=float, default=900.0, help="segundos (padrão 900)")
    parser.add_argument("--interval", type=float, default=20.0, help="segundos entre tentativas")
    parser.add_argument("--allow-http", action="store_true", help="somente para testes locais")
    args = parser.parse_args(argv)

    parts = urlsplit(args.url)
    if parts.scheme not in ({"https", "http"} if args.allow_http else {"https"}):
        print("Uso inválido: a URL precisa ser https.", file=sys.stderr)
        return 2
    if not parts.hostname or parts.username or parts.password:
        print("Uso inválido: URL sem host ou com credenciais.", file=sys.stderr)
        return 2
    if not SEMVER_RE.match(args.expect_version):
        print(f"Uso inválido: versão esperada {args.expect_version!r} não é SemVer.", file=sys.stderr)
        return 2
    if args.timeout <= 0 or args.interval <= 0:
        print("Uso inválido: timeout e interval devem ser positivos.", file=sys.stderr)
        return 2

    ok, last = wait_for_version(args.url, args.expect_version, args.timeout, args.interval)
    if ok:
        print(f"OK: {args.url} serve a versão {args.expect_version}.")
        return 0
    print(
        f"FALHA: {args.url} não serviu a versão {args.expect_version} em {args.timeout:.0f}s "
        f"(última resposta: {last}). Confira o deploy no Render; o CD não dispara deploy.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
