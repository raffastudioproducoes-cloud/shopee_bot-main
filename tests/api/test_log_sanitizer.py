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


class TestSanitizePassthrough:
    def test_none_and_numbers_pass_through(self):
        assert sanitize_log_data(None) is None
        assert sanitize_log_data(200) == 200
