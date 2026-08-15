import pytest
from app.ingestion.safety import UnsafeURLError, assert_public_http_url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "http://localhost/admin",
        "http://127.0.0.1/",
        "http://10.0.0.5/secret",
        "http://192.168.1.9/x",
        "http://169.254.169.254/latest/meta-data",
        "http://user:pass@example.com",
    ],
)
def test_blocks_unsafe_urls(url: str) -> None:
    with pytest.raises(UnsafeURLError):
        assert_public_http_url(url)


def test_allows_public_https(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert assert_public_http_url("https://example.com/menu") == "https://example.com/menu"
