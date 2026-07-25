#!/usr/bin/env python3
"""CLI for fetching article full text and figure images (not just PDFs).

Use this when `download_papers.py` fails with "journal not in institutional
subscription". PDF entitlement and text-and-data-mining (TDM) entitlement are
granted separately, so the full text is often still reachable.

Usage:
    # Diagnose which content routes work for one DOI
    python fetch_fulltext.py --probe 10.1016/j.ijthermalsci.2023.108376

    # Fetch full text + original figure images for one DOI
    python fetch_fulltext.py --doi 10.1016/j.ijthermalsci.2023.108376

    # Batch from a saved search result (only papers with a DOI)
    python fetch_fulltext.py --load data/papers/papers_20260725_155604.json

    # Batch from an explicit DOI list, text only (much faster: 1 request/paper)
    python fetch_fulltext.py --doi-file dois.txt --no-figures

    # Screening aid: print section titles so you can spot an experimental section
    python fetch_fulltext.py --doi 10.1016/... --sections
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Fix Windows encoding issues with special characters
os.environ['PYTHONIOENCODING'] = 'utf-8'

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.fulltext_fetcher import FullTextFetcher


def collect_dois(args) -> list[str]:
    """Gather DOIs from --doi, --doi-file, or a saved search-result JSON."""
    if args.doi:
        return [args.doi]
    if args.doi_file:
        return [ln.strip() for ln in Path(args.doi_file).read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.startswith("#")]
    if args.load:
        data = json.loads(Path(args.load).read_text(encoding="utf-8"))
        papers = data if isinstance(data, list) else data.get("papers", [])
        return [p["doi"] for p in papers if p.get("doi")]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch article full text and figures via publisher content APIs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--doi", help="Single DOI to fetch")
    src.add_argument("--doi-file", help="File with one DOI per line")
    src.add_argument("--load", help="Saved search-result JSON (uses every paper with a DOI)")
    src.add_argument("--probe", metavar="DOI", help="Diagnose available routes, save nothing")

    parser.add_argument("--output-dir", default="data/fulltext", help="Output directory")
    parser.add_argument("--no-figures", action="store_true",
                        help="Skip figure images (1 request per paper instead of ~1 per figure)")
    parser.add_argument("--sections", action="store_true",
                        help="Print section titles of each fetched article (screening aid)")
    parser.add_argument("--pause", type=float, default=2.0,
                        help="Seconds between figure-image requests (default: 2.0)")
    args = parser.parse_args()

    fetcher = FullTextFetcher(output_dir=args.output_dir, object_pause=args.pause)

    if args.probe:
        print(f"Probing routes for {args.probe}\n")
        for name, verdict in fetcher.probe(args.probe):
            print(f"  {name:16s} {verdict}")
        print("\nNote: the /entitlement/ endpoint is NOT authoritative — it can return 403")
        print("      while these content endpoints work. Trust this probe, not entitlement.")
        return 0

    dois = collect_dois(args)
    if not dois:
        print("No DOIs found in the given source.")
        return 1

    print(f"Fetching full text for {len(dois)} paper(s) -> {args.output_dir}\n")
    ok = 0
    for i, doi in enumerate(dois, 1):
        result = fetcher.fetch(doi, with_figures=not args.no_figures)
        if result.success:
            ok += 1
            bits = [f"source={result.source}"]
            if result.figures:
                bits.append(f"figures={len(result.figures)}")
            if result.n_images:
                bits.append(f"images={result.n_images}")
            print(f"[{i}/{len(dois)}] OK   {doi}  ({', '.join(bits)})")
            if args.sections and result.path and result.path.suffix == ".xml":
                for title in fetcher.sections(result.path.read_bytes()):
                    print(f"           - {title}")
        else:
            print(f"[{i}/{len(dois)}] FAIL {doi}  ({result.error})")

    print(f"\nDone: {ok}/{len(dois)} succeeded. Output in {args.output_dir}/")
    if ok < len(dois):
        print("Failures are usually title-level entitlement. Try --probe on one to confirm,")
        print("and check green OA (OpenAlex/Unpaywall) for the rest.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
