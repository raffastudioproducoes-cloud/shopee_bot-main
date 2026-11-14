"""Testes de api/utils/log_sanitizer.py — nunca pode devolver segredo em texto claro."""

from api.utils.log_sanitizer import sanitize_log_data


class TestSanitizeDict:
    def test_masks_password_key(self):
        result = sanitize_log_data({"username": "rafa", "password": "hunter2"})

        assert result["password"] == "***REDACTED***"
        assert result["username"] == "rafa"

    def test_masks_key_variants_case_and_style_insensitive(self):
        result = sanitize_log_data(
            {
                "accessToken": "abc",
                "ACCESS_TOKEN": "def",
                "Access-Token": "ghi",
                "client_secret": "jkl",
                "API_KEY": "mno",
            }
        )

        assert all(v == "***REDACTED***" for v in result.values())

    def test_masks_nested_dict_and_list(self):
        result = sanitize_log_data(
            {
                "user": {"name": "rafa", "refresh_token": "xyz"},
                "items": [{"secret": "s1"}, {"secret": "s2"}],
            }
        )

        assert result["user"]["refresh_token"] == "***REDACTED***"
        assert result["user"]["name"] == "rafa"
        assert result["items"][0]["secret"] == "***REDACTED***"
        assert result["items"][1]["secret"] == "***REDACTED***"

    def test_leaves_non_sensitive_fields_untouched(self):
        result = sanitize_log_data({"method": "GET", "status_code": 200})

        assert result == {"method": "GET", "status_code": 200}


class TestSanitizeFreeString:
    def test_masks_password_inside_free_text(self):
        text = 'payload recebido: {"password": "hunter2", "user": "rafa"}'

        result = sanitize_log_data(text)

        assert "hunter2" not in result
        assert '"user": "rafa"' in result  # campo não sensível continua visível

    def test_masks_jwt_like_token_in_free_text(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PYYkYSwPKcQr"
        text = f"erro na chamada, token usado: {jwt}"

        result = sanitize_log_data(text)

        assert jwt not in result
        assert "***REDACTED***" in result

    def test_masks_bearer_header_in_free_text(self):
        text = "Authorization: Bearer abc123.def456-ghi789"

        result = sanitize_log_data(text)

        assert "abc123.def456-ghi789" not in result
        assert "Bearer ***REDACTED***" in result

    def test_masks_basic_authorization_and_oauth_query_values(self):
        text = (
            "upstream recusou Authorization: Basic Y2xpZW50OnNlZ3JlZG8= "
            "em https://example.test/callback?code=oauth-code-123&state=csrf-state&hash=hash-value"
        )

        result = sanitize_log_data(text)

        for secret in ("Y2xpZW50OnNlZ3JlZG8=", "oauth-code-123", "csrf-state", "hash-value"):
            assert secret not in result
        assert "code=***REDACTED***" in result


class TestSanitizePassthrough:
    def test_none_and_numbers_pass_through(self):
        assert sanitize_log_data(None) is None
        assert sanitize_log_data(200) == 200


class TestMetaErrorCodes:
    def test_preserves_numeric_meta_code_and_subcode(self):
        text = (
            "Failed to Publish Media Container: HTTP 400 | Meta code=24 | "
            "subcode=4279009 | The requested resource does not exist"
        )

        assert sanitize_log_data(text) == text
        assert sanitize_log_data({"error": text})["error"] == text

    def test_preserves_json_numeric_code(self):
        text = '{"error": {"code": 190, "error_subcode": 463}}'

        assert sanitize_log_data(text) == text

    def test_still_masks_tokens_next_to_codes(self):
        text = (
            "Meta code=24 subcode=4279009 access_token=EAAGabc123secret "
            "token=xyz789 code=oauth-code-123 state=12345"
        )

        result = sanitize_log_data(text)

        assert "code=24" in result and "subcode=4279009" in result
        for secret in ("EAAGabc123secret", "xyz789", "oauth-code-123", "12345"):
            assert secret not in result

    def test_still_masks_code_in_query_string(self):
        result = sanitize_log_data("https://x.test/cb?code=123456&state=s")

        assert "123456" not in result
