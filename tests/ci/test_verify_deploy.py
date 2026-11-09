import http.server
import importlib.util
import sys
import threading
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "verify_deploy", Path(__file__).resolve().parents[2] / "scripts" / "verify_deploy.py")
verify = importlib.util.module_from_spec(SPEC)
sys.modules["verify_deploy"] = verify
SPEC.loader.exec_module(verify)


class _Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def _run(responses, timeout=100, interval=10):
    clock, it, calls = _Clock(), iter(responses), []

    def fetch(_url):
        calls.append(1)
        return next(it)

    ok, last = verify.wait_for_version(
        "https://x.example/", "3.9.0", timeout, interval,
        fetch=fetch, sleep=clock.sleep, now=clock.now, log=lambda _m: None)
    return ok, last, len(calls)


class WaitForVersionTests(unittest.TestCase):
    def test_returns_immediately_when_version_matches(self):
        ok, _last, calls = _run([(200, "3.9.0")])
        self.assertTrue(ok)
        self.assertEqual(calls, 1)

    def test_tolerates_cold_start_5xx_and_old_version_then_succeeds(self):
        ok, _last, calls = _run([(None, None), (502, None), (200, "3.8.0"), (200, "3.9.0")])
        self.assertTrue(ok)
        self.assertEqual(calls, 4)

    def test_times_out_and_reports_last_response(self):
        ok, last, _calls = _run([(200, "3.8.0")] * 50, timeout=30, interval=10)
        self.assertFalse(ok)
        self.assertIn("3.8.0", last)

    def test_wrong_status_with_matching_text_is_not_success(self):
        ok, _last, _calls = _run([(503, "3.9.0")] * 50, timeout=20, interval=10)
        self.assertFalse(ok)

    def test_version_regex_reads_splash_markup(self):
        match = verify.VERSION_RE.search('<div class="site-splash-version">Versão 3.9.0</div>')
        self.assertEqual(match.group(1), "3.9.0")


class _Handler(http.server.BaseHTTPRequestHandler):
    body = b'<div class="site-splash-version">Vers\xc3\xa3o 3.9.0</div>'

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        pass


class MainTests(unittest.TestCase):
    def test_rejects_invalid_usage(self):
        for argv in (
            ["--url", "http://x.example/", "--expect-version", "3.9.0"],
            ["--url", "https://u:p@x.example/", "--expect-version", "3.9.0"],
            ["--url", "https://x.example/", "--expect-version", "latest"],
            ["--url", "https://x.example/", "--expect-version", "3.9.0", "--timeout", "0"],
        ):
            self.assertEqual(verify.main(argv), 2, argv)

    def test_end_to_end_against_local_server(self):
        server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/"
            self.assertEqual(verify.main(["--url", url, "--expect-version", "3.9.0", "--allow-http",
                                          "--timeout", "5", "--interval", "1"]), 0)
            self.assertEqual(verify.main(["--url", url, "--expect-version", "9.9.9", "--allow-http",
                                          "--timeout", "2", "--interval", "1"]), 1)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
