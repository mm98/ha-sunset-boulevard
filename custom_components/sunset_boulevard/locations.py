"""Parsing of the Sunset Boulevard restaurant list.

Reads the markers embedded in the ``map-container`` element of
https://sunset-boulevard.dk/restauranter/ . Kept free of Home Assistant
imports so it can be tested standalone.
"""

from __future__ import annotations

import html
import json
import logging
import re
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

_POSTAL_CODES_FILE = "postal_codes.json"

_POSTAL_RE = re.compile(r"\d{4}")


@dataclass(frozen=True)
class SunsetBoulevardLocation:
    """A single restaurant from the website's location list."""

    name: str
    latitude: float
    longitude: float
    address: str | None = None  # full normalized one-line address
    venue: str | None = None  # mall/terminal prefix, e.g. "HerningCentret"
    street: str | None = None  # street, number, and floor markers
    postal: str | None = None
    city: str | None = None
    link: str | None = None  # URL of the restaurant's page on the website


@dataclass(frozen=True)
class ParsedAddress:
    """A feed address broken into its parts, plus the one-line rendering."""

    formatted: str
    venue: str | None = None
    street: str | None = None
    postal: str | None = None
    city: str | None = None


def _format_address(
    venue: str | None, street: str | None, postal: str | None, city: str | None
) -> str:
    """Render the components as "[venue, ]street, postal city"."""
    if postal and city:
        tail = f"{postal} {city}"
    else:
        tail = city or postal or ""
    if street and tail:
        formatted = f"{street}, {tail}"
    else:
        formatted = street or tail
    if venue:
        formatted = f"{venue}, {formatted}" if formatted else venue
    return formatted


def _postal_city(block: str) -> tuple[str | None, str | None]:
    """Split a "postal city" (or "city postal") tail into its two parts."""
    tokens = block.split()
    for index, token in enumerate(tokens):
        if _POSTAL_RE.fullmatch(token):
            after = tokens[index + 1 :]
            before = tokens[:index]
            city = " ".join(after) if after else " ".join(before)
            return token, (city or None)
    return None, (block.strip() or None)


def parse_address(raw: str) -> ParsedAddress:
    """Split a marker address into venue/street/postal/city components.

    The page writes addresses with ``<br>`` line breaks and irregular
    variants: venue prefixes, floor markers, a missing postal code, or the
    postal code and city in either order. Anything that can't be split is
    returned as ``formatted`` only, with the parts left None.
    """
    text = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        return ParsedAddress(formatted="")

    # A venue is a leading segment without a house number: it may sit on its
    # own line ("HerningCentret,") or lead the first line ("Fields, Arne ...").
    venue: str | None = None
    head, sep, rest = lines[0].partition(",")
    if sep and head and not any(ch.isdigit() for ch in head):
        venue = head.strip()
        rest = rest.strip()
        lines = ([rest] if rest else []) + lines[1:]

    if not lines:
        return ParsedAddress(formatted=venue or "", venue=venue)

    postal: str | None
    city: str | None
    if len(lines) >= 2:
        street = " ".join(lines[:-1]).strip().rstrip(",").strip()
        postal, city = _postal_city(lines[-1])
    else:
        line = lines[0]
        match = re.search(r"\b\d{4}\b", line)
        if match:
            street = line[: match.start()].strip().rstrip(",").strip()
            postal = match.group(0)
            city = line[match.end() :].strip() or None
        else:
            tokens = line.split()
            if len(tokens) >= 2:
                street, city, postal = " ".join(tokens[:-1]), tokens[-1], None
            else:
                street, city, postal = line, None, None

    street = street or None
    return ParsedAddress(
        formatted=_format_address(venue, street, postal, city),
        venue=venue,
        street=street,
        postal=postal,
        city=city,
    )


class _MarkerParser(HTMLParser):
    """Collects the ``marker custom-marker`` blocks from the page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.markers: list[dict[str, str | None]] = []
        self._current: dict[str, str | None] | None = None
        self._depth = 0
        self._in_h4 = False
        self._capture: str | None = None  # "name" | "address" | None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "div" and "custom-marker" in classes:
            self._finalize()
            self._current = {
                "lat": attributes.get("data-lat"),
                "lng": attributes.get("data-lng"),
                "name": None,
                "link": None,
                "address": None,
            }
            self._depth = 1
            return
        if self._current is None:
            return
        if tag == "div":
            self._depth += 1
        elif tag == "h4":
            self._in_h4 = True
        elif tag == "a" and self._in_h4:
            if self._current["link"] is None:
                self._current["link"] = attributes.get("href")
            self._capture = "name"
            self._buffer = []
        elif tag == "p" and "address" in classes:
            self._capture = "address"
            self._buffer = []
        elif tag == "br" and self._capture == "address":
            self._buffer.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if tag == "a" and self._capture == "name":
            self._current["name"] = "".join(self._buffer).strip()
            self._capture = None
            self._buffer = []
        elif tag == "h4":
            self._in_h4 = False
        elif tag == "p" and self._capture == "address":
            self._current["address"] = "".join(self._buffer).strip()
            self._capture = None
            self._buffer = []
        elif tag == "div":
            self._depth -= 1
            if self._depth == 0:
                self._finalize()

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def _finalize(self) -> None:
        if self._current is not None:
            self.markers.append(self._current)
        self._current = None
        self._depth = 0
        self._in_h4 = False
        self._capture = None
        self._buffer = []


def load_postal_map(path: str | None = None) -> dict[str, str]:
    """Load the bundled ``{city: postal}`` lookup of Danish postal codes.

    The page omits the postal code for a couple of locations; this fills them
    in by city name. Only city names that map to a single postal code are
    included, so a lookup is never ambiguous.
    """
    file = Path(path) if path else Path(__file__).with_name(_POSTAL_CODES_FILE)
    with file.open(encoding="utf-8") as handle:
        return json.load(handle)


def _fill_postal(
    location: SunsetBoulevardLocation, postal_by_city: dict[str, str]
) -> SunsetBoulevardLocation:
    """Add a missing postal code (and reformat the address) from the lookup."""
    if location.postal or not location.city:
        return location
    postal = postal_by_city.get(location.city)
    if not postal:
        return location
    address = _format_address(
        location.venue, location.street, postal, location.city
    )
    return replace(location, postal=postal, address=address or None)


def parse_locations(
    page: str, postal_by_city: dict[str, str] | None = None
) -> list[SunsetBoulevardLocation]:
    """Parse restaurant markers from the /restauranter/ page HTML.

    If ``postal_by_city`` is given, locations the page lists without a postal
    code have it filled in by city name (see :func:`load_postal_map`).
    """
    parser = _MarkerParser()
    parser.feed(page)
    parser.close()

    locations: list[SunsetBoulevardLocation] = []
    for marker in parser.markers:
        name = marker["name"]
        if not name or not marker["lat"] or not marker["lng"]:
            continue
        try:
            latitude = float(marker["lat"])
            longitude = float(marker["lng"])
        except (TypeError, ValueError):
            _LOGGER.warning(
                "Skipping marker %s with unparsable coordinates: %s, %s",
                name,
                marker["lat"],
                marker["lng"],
            )
            continue

        parsed = parse_address(marker["address"] or "")
        location = SunsetBoulevardLocation(
            name=name,
            latitude=latitude,
            longitude=longitude,
            address=parsed.formatted or None,
            venue=parsed.venue,
            street=parsed.street,
            postal=parsed.postal,
            city=parsed.city,
            link=marker["link"] or None,
        )
        if postal_by_city:
            location = _fill_postal(location, postal_by_city)
        locations.append(location)

    return locations
