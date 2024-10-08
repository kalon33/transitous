#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 Jonah Brüchert <jbb@kaidan.im>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import csv
import io
import transitland
import pycountry

from pathlib import Path
from metadata import Source, TransitlandSource, Region
from zipfile import ZipFile
from typing import Optional


REGIONS = {"EU": "European Union"}


if __name__ == "__main__":
    feed_dir = Path("feeds/")

    transitland_atlas = transitland.Atlas.load(Path("transitland-atlas/"))

    attributions = []

    for feed in sorted(feed_dir.glob("*.json")):
        parsed = {}
        with open(feed, "r") as f:
            parsed = json.load(f)

        region = Region(parsed)
        for source in region.sources:
            if type(source) == TransitlandSource:
                source = transitland_atlas.source_by_id(source)
                if not source:
                    continue

            if source.skip:
                continue

            if source.spec == "gtfs-rt":
                continue

            attribution: dict = {}

            if source.license:
                if source.license.spdx_identifier:
                    attribution["spdx_license_identifier"] = source.license.spdx_identifier
                if source.license.url:
                    attribution["license_url"] = source.license.url

            attribution["operators"] = []
            attribution["source"] = source.url

            metadata_filename = feed.name
            region_name = metadata_filename[: metadata_filename.rfind(".")]

            feed_path = Path(f"out/{region_name}_{source.name}.gtfs.zip")

            attribution["filename"] = feed_path.name

            human_name: str = feed_path.name.replace(".gtfs.zip", "").split("_")[1].replace("-", " ")
            human_name = " ".join(map(lambda w: w[0].upper() + w[1:] if len(w) > 0 else w, human_name.split(" ")))
            attribution["human_name"] = human_name

            if not feed_path.exists():
                print(f"Info: {feed_path} does not exist, skipping…")
                continue

            with ZipFile(feed_path) as z:
                with z.open("agency.txt", "r") as a:
                    with io.TextIOWrapper(a) as at:
                        agencyreader = csv.DictReader(at, delimiter=",", quotechar='"')
                        for row in agencyreader:
                            attribution["operators"].append(row["agency_name"])

            if (
                "operators" in attribution
                and len(attribution["operators"]) == 1
                and len(attribution["operators"][0]) > 1
            ):
                attribution["human_name"] = attribution["operators"][0]

            region_code = feed_path.name.split("_")[0].upper()
            attribution["region_code"] = region_code
            region_name = ""
            subdivision = pycountry.subdivisions.get(code=region_code)
            if not subdivision:
                country = pycountry.countries.get(alpha_2=region_code)
                if country:
                    region_name = country.name
                else:
                    region_name = REGIONS[region_code]
            else:
                region_name = subdivision.name
            attribution["region_name"] = region_name

            attributions.append(attribution)

    with open("out/license.json", "w") as outfile:
        json.dump(attributions, outfile, indent=4, ensure_ascii=False)
