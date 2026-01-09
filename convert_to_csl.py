#!/usr/bin/env python3
"""Convert internal JSON files to CSL JSON format."""

import json
import sys
from pathlib import Path
from glob import glob

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.paper_fetcher import Paper
from src.csl_exporter import CSLExporter


def main():
    # Find all papers_*.json files (internal format)
    data_dir = Path("data/papers")
    json_files = glob(str(data_dir / "papers_2026*.json"))

    if not json_files:
        print("No JSON files found to convert")
        return

    print(f"Found {len(json_files)} JSON files")

    # Collect all papers
    all_papers = []
    seen_ids = set()

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for p in data.get("papers", []):
                scopus_id = p["scopus_id"]

                # Skip duplicates
                if scopus_id in seen_ids:
                    continue

                seen_ids.add(scopus_id)

                paper = Paper(
                    scopus_id=scopus_id,
                    title=p["title"],
                    abstract=p["abstract"],
                    authors=p["authors"],
                    publication_name=p["publication_name"],
                    publication_date=p["publication_date"],
                    citation_count=p["citation_count"],
                    doi=p.get("doi"),
                    keywords=p.get("keywords", []),
                    url=p.get("url"),
                )
                all_papers.append(paper)

        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            continue

    print(f"Total unique papers: {len(all_papers)}")

    # Export to CSL JSON
    exporter = CSLExporter(output_dir="data/papers")
    result = exporter.export_papers(all_papers, filename="VersionB_References_CSL.json")

    if result.success:
        print(f"CSL JSON exported to: {result.filepath}")
        print(f"Papers exported: {result.paper_count}")
    else:
        print(f"Export failed: {result.error}")


if __name__ == "__main__":
    main()
