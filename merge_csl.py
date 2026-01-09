#!/usr/bin/env python3
"""Merge multiple CSL JSON files into one."""

import json
from pathlib import Path
from glob import glob


def main():
    # Find all CSL JSON files
    data_dir = Path("data/papers")
    json_files = sorted(glob(str(data_dir / "papers_202601*.json")))

    if not json_files:
        print("No CSL JSON files found")
        return

    print(f"Found {len(json_files)} CSL JSON files")

    # Collect all papers
    all_papers = []
    seen_ids = set()

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # CSL JSON is a list of items
            if isinstance(data, list):
                for item in data:
                    item_id = item.get("id")

                    # Skip duplicates
                    if item_id and item_id in seen_ids:
                        print(f"  Skipping duplicate: {item_id}")
                        continue

                    if item_id:
                        seen_ids.add(item_id)

                    all_papers.append(item)
            else:
                print(f"Warning: {json_file} is not a CSL JSON list")

        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            continue

    print(f"Total unique papers: {len(all_papers)}")

    # Write merged file
    output_file = data_dir / "VersionB_References_CSL.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, ensure_ascii=False, indent=2)

    print(f"Merged CSL JSON written to: {output_file}")
    print(f"Import this file into Zotero: File > Import > Select this .json file")


if __name__ == "__main__":
    main()
