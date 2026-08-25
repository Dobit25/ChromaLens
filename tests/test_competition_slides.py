from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "docs" / "competition-feature-slides.html"


class _DeckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.slide_ids: list[str] = []
        self.asset_urls: list[str] = []
        self.profile_values: set[str] = set()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "section" and "slide" in classes:
            self.slide_ids.append(values.get("id") or "")
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.asset_urls.append(value)
        profile = values.get("data-profile")
        if profile:
            self.profile_values.add(profile)


def _parse_deck() -> tuple[str, _DeckParser]:
    source = DECK.read_text(encoding="utf-8")
    parser = _DeckParser()
    parser.feed(source)
    return source, parser


def test_competition_deck_has_exactly_six_ordered_slides() -> None:
    _, parser = _parse_deck()
    assert parser.slide_ids == [f"slide-{index}" for index in range(1, 7)]


def test_competition_deck_is_offline_and_fixture_is_available() -> None:
    _, parser = _parse_deck()
    assert all(not url.startswith(("http://", "https://", "//")) for url in parser.asset_urls)
    assert (ROOT / "tests" / "samples" / "t02" / "astronaut.png").is_file()
    assert "../tests/samples/t02/astronaut.png" in parser.asset_urls


def test_competition_deck_exposes_all_supported_profiles_and_controls() -> None:
    source, parser = _parse_deck()
    assert parser.profile_values == {"deutan", "protan", "tritan"}
    assert "profileCycle" in source
    assert "ArrowRight" in source
    assert "requestFullscreen" in source
    assert "Sensor-to-photon" in source
    assert "NOT MEASURED" in source
