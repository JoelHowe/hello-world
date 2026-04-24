"""URL canonicalization tests.

The pure `canonicalize` covers the bulk of real-world de-dup wins (tracking
params + normalization). `expand_and_canonicalize` is exercised against a
mocked shortener so we don't hit the network in CI.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.services.url_canonicalize import (
    canonicalize,
    domain_of,
    expand_and_canonicalize,
    new_expand_cache,
)


class TestPureCanonicalize:
    def test_strips_utm_params(self):
        assert canonicalize(
            "https://example.com/story?utm_source=bsky&utm_medium=social"
        ) == "https://example.com/story"

    def test_strips_mixed_tracking_params(self):
        got = canonicalize(
            "https://example.com/x?utm_campaign=a&fbclid=xyz&id=42&gclid=abc&ref=home"
        )
        assert got == "https://example.com/x?id=42"

    def test_keeps_legitimate_query(self):
        assert canonicalize("https://example.com/search?q=hello") == "https://example.com/search?q=hello"

    def test_drops_fragment(self):
        assert canonicalize("https://example.com/a#section") == "https://example.com/a"

    def test_lowercases_host(self):
        assert canonicalize("HTTPS://Example.COM/p") == "https://example.com/p"

    def test_strips_twitter_share_params(self):
        assert canonicalize("https://example.com/p?s=20&t=abc") == "https://example.com/p"

    def test_idempotent(self):
        once = canonicalize("https://Example.com/p?utm_source=x&id=1#frag")
        twice = canonicalize(once)
        assert once == twice

    def test_preserves_empty_query(self):
        assert canonicalize("https://example.com/path") == "https://example.com/path"

    def test_domain_of_strips_www(self):
        assert domain_of("https://www.example.com/p") == "example.com"
        assert domain_of("https://Sub.Example.com/p") == "sub.example.com"


class TestExpandAndCanonicalize:
    @respx.mock
    def test_expands_known_shortener(self):
        respx.head("https://bit.ly/abc").mock(
            return_value=httpx.Response(
                301,
                headers={"location": "https://example.com/article?utm_source=bitly"},
            )
        )
        with httpx.Client() as client:
            got = expand_and_canonicalize("https://bit.ly/abc", client)
        assert got == "https://example.com/article"

    @respx.mock
    def test_does_not_expand_unknown_host(self):
        # No mock set — would fail if we tried to hit the network.
        with httpx.Client() as client:
            got = expand_and_canonicalize(
                "https://example.com/story?utm_source=x", client
            )
        assert got == "https://example.com/story"

    @respx.mock
    def test_follows_chain_but_caps_hops(self):
        respx.head("https://bit.ly/1").mock(
            return_value=httpx.Response(301, headers={"location": "https://t.co/2"})
        )
        respx.head("https://t.co/2").mock(
            return_value=httpx.Response(301, headers={"location": "https://buff.ly/3"})
        )
        respx.head("https://buff.ly/3").mock(
            return_value=httpx.Response(301, headers={"location": "https://example.com/final?utm_source=x"})
        )
        with httpx.Client() as client:
            got = expand_and_canonicalize("https://bit.ly/1", client)
        assert got == "https://example.com/final"

    @respx.mock
    def test_swallows_network_error(self):
        respx.head("https://bit.ly/broken").mock(side_effect=httpx.ConnectError("nope"))
        with httpx.Client() as client:
            got = expand_and_canonicalize("https://bit.ly/broken", client)
        # We return the best we had.
        assert got == "https://bit.ly/broken"

    @respx.mock
    def test_cache_dedupes_repeated_expansions(self):
        route = respx.head("https://bit.ly/dup").mock(
            return_value=httpx.Response(
                301, headers={"location": "https://example.com/dup"}
            )
        )
        cache = new_expand_cache()
        with httpx.Client() as client:
            expand_and_canonicalize("https://bit.ly/dup", client, cache)
            expand_and_canonicalize("https://bit.ly/dup", client, cache)
        assert route.call_count == 1
