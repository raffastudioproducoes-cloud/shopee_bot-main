import logging

from api import main  # noqa: F401


def test_http_client_loggers_stay_warning_to_avoid_token_query_leaks():
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
