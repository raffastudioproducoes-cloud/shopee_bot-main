"""Pins de seguranca dos parsers usados no login e nos uploads."""

from importlib.metadata import version


def test_multipart_parser_uses_reviewed_release():
    assert version("python-multipart") == "0.0.31"


def test_image_decoder_uses_reviewed_release():
    assert version("Pillow") == "13.0.0"
