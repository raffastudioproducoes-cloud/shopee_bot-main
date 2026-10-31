#!/usr/bin/env python3
"""Black-box security smoke against staging only (no public postings).

Read-only public probes plus an artificial login username. Optional valid
credentials are supplied explicitly as STAGING_SMOKE_USERNAME/PASSWORD.
No credentials or cookies are printed.
"""
import argparse
import http.cookiejar
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

STAGING_ORIGIN = "https://shopee-bot-staging.onrender.com"


def request(opener, path, *, form=None):
    headers = {"Accept": "application/json", "User-Agent": "auto-orbital-staging-security-smoke/1"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(STAGING_ORIGIN + path, data=data, headers=headers)
    try:
        with opener.open(req, timeout=35) as response:
            return response.status, response.headers, response.read(4096)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read(4096)


def check_health(opener):
    # Render free instance might wake up slowly, so allow several cold-start probes.
    for delay in (0, 10, 20, 30, 30):
        if delay:
            time.sleep(delay)
        try:
            status, headers, body = request(opener, "/health")
        except (TimeoutError, OSError, urllib.error.URLError):
            continue
        if status == 200:
            payload = json.loads(body)
            assert payload.get("status") == "ok", "Health malformed"
            assert headers.get("X-Content-Type-Options") == "nosniff"
            assert "max-age=" in headers.get("Strict-Transport-Security", "")
            policy = headers.get("Content-Security-Policy", "")
            assert "script-src 'self'" in policy
            assert "'unsafe-eval'" not in policy
            print("PASS: staging health and security headers")
            return
    raise AssertionError("Staging did not return healthy HTTP 200")


def check_anonymous(opener):
    code, _, _ = request(opener, "/api/auth/me")
    assert code == 401, f"Unauthenticated /auth/me unexpectedly returned {code}"
    print("PASS: anonymous session denied")


def check_login_limits(opener):
    # Username randomizado impossível de colidir com uma conta real:
    # não tenta senhas de pessoas nem interfere nos limites de usuários reais.
    probe_username = "security-probe-" + secrets.token_hex(14)
    for index in range(6):
        code, _, _ = request(opener, "/api/auth/login", form={
            "username": probe_username,
            "password": "invalid-" + secrets.token_hex(12),
        })
        expected = 429 if index == 5 else 401
        assert code == expected, f"Attempt {index + 1}: expected {expected}, got {code}"
    print("PASS: sixth invalid login blocked with 429")


def check_optional_authenticated_flow(opener):
    username = os.getenv("STAGING_SMOKE_USERNAME", "")
    password = os.getenv("STAGING_SMOKE_PASSWORD", "")
    if not username and not password:
        print("SKIP: authenticated smoke (credentials not supplied)")
        return
    assert username and password, "Both staging smoke credentials are required"
    code, _, _ = request(opener, "/api/auth/login", form={
        "username": username, "password": password,
    })
    assert code == 200, f"Explicit test account login failed ({code})"
    code, _, payload = request(opener, "/api/auth/me")
    assert code == 200, f"Authenticated /me failed ({code})"
    user = json.loads(payload)
    assert user.get("username") == username
    code, _, _ = request(opener, "/api/auth/logout", form={})
    assert code == 200, f"Logout failed ({code})"
    code, _, _ = request(opener, "/api/auth/me")
    assert code == 401, "Logout did not revoke session"
    print("PASS: opt-in login/me/logout/session revocation")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default=STAGING_ORIGIN)
    args = parser.parse_args()
    if args.origin.rstrip("/") != STAGING_ORIGIN:
        parser.error("This smoke may target staging ONLY")
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    check_health(opener)
    check_anonymous(opener)
    check_login_limits(opener)
    check_optional_authenticated_flow(opener)
    print("PASS: staging security smoke completed")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, ValueError, OSError) as exc:
        # Errors have no credential-bearing request content.
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
