"""Update restaurants.json from a saved copy of the restaurant page.

Usage: python import_restaurants.py PAGE.html
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

COMPONENT = Path(__file__).parents[2] / "custom_components" / "sunset_boulevard"


def main(page: Path) -> int:
	spec = importlib.util.spec_from_file_location("locations", COMPONENT / "locations.py")
	locations = importlib.util.module_from_spec(spec)
	sys.modules["locations"] = locations
	spec.loader.exec_module(locations)

	found = locations.parse_locations(
		page.read_text(encoding="utf-8", errors="replace"), locations.load_postal_map()
	)
	if not found:
		print(f"No restaurants found in {page.name}. Save the page again once it shows the restaurants.")
		return 1

	data = {
		"updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
		"restaurants": sorted((asdict(item) for item in found), key=lambda item: item["name"]),
	}
	with (COMPONENT / "restaurants.json").open("w", encoding="utf-8", newline="\r\n") as handle:
		handle.write(json.dumps(data, ensure_ascii=False, indent="\t") + "\n")
	print(f"Wrote {len(found)} restaurants from {page.name}.")
	return 0


if __name__ == "__main__":
	sys.exit(main(Path(sys.argv[1])))
