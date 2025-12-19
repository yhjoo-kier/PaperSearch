#!/usr/bin/env python3
"""CLI script for searching papers on Scopus.

Usage:
    python search_papers.py --topic "machine learning" --count 30
    python search_papers.py --topic "deep learning" --additional "transformer,attention" --year-from 2020
    python search_papers.py --query 'TITLE-ABS-KEY("neural network")' --count 50
    python search_papers.py --load data/papers/papers_20241201_120000.json
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.paper_fetcher import PaperFetcher, generate_review_summary
from src.query_builder import build_query_from_topic


def main():
    parser = argparse.ArgumentParser(
        description="Search Scopus for academic papers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search by topic
  python search_papers.py --topic "machine learning" --count 30

  # Search with additional terms and year filter
  python search_papers.py --topic "deep learning" --additional "transformer" --year-from 2020

  # Use raw Scopus query
  python search_papers.py --query 'TITLE-ABS-KEY("neural network") AND PUBYEAR > 2019'

  # Load and review previously saved results
  python search_papers.py --load data/papers/papers_20241201_120000.json
        """
    )

    # Search options
    parser.add_argument(
        "--topic", "-t",
        help="Research topic to search for"
    )
    parser.add_argument(
        "--query", "-q",
        help="Raw Scopus query string (advanced)"
    )
    parser.add_argument(
        "--additional", "-a",
        help="Additional search terms (comma-separated)"
    )
    parser.add_argument(
        "--exclude", "-e",
        help="Terms to exclude (comma-separated)"
    )
    parser.add_argument(
        "--year-from",
        type=int,
        help="Start year for publication filter"
    )
    parser.add_argument(
        "--year-to",
        type=int,
        help="End year for publication filter"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=30,
        help="Number of papers to fetch (default: 30)"
    )

    # Load option
    parser.add_argument(
        "--load", "-l",
        help="Load papers from existing JSON file"
    )

    # Output options
    parser.add_argument(
        "--output", "-o",
        help="Output file for review summary (default: stdout)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to JSON file"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.topic and not args.query and not args.load:
        parser.error("One of --topic, --query, or --load is required")

    fetcher = PaperFetcher()

    if args.load:
        # Load existing papers
        print(f"Loading papers from: {args.load}", file=sys.stderr)
        metadata, papers = fetcher.load_papers(args.load)
        query = metadata.get("query", "loaded from file")
        print(f"Loaded {len(papers)} papers", file=sys.stderr)
    elif args.query:
        # Use raw query
        print(f"Searching with query: {args.query}", file=sys.stderr)
        papers = fetcher.fetch_papers(
            args.query,
            count=args.count,
            save=not args.no_save
        )
        query = args.query
        print(f"Found {len(papers)} papers", file=sys.stderr)
    else:
        # Build query from topic
        additional = args.additional.split(",") if args.additional else None
        exclude = args.exclude.split(",") if args.exclude else None

        query, papers = fetcher.fetch_by_topic(
            topic=args.topic,
            count=args.count,
            additional_terms=additional,
            exclude=exclude,
            year_from=args.year_from,
            year_to=args.year_to,
            save=not args.no_save
        )
        print(f"Generated query: {query}", file=sys.stderr)
        print(f"Found {len(papers)} papers", file=sys.stderr)

    # Generate review summary
    summary = generate_review_summary(papers, query)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"Summary written to: {args.output}", file=sys.stderr)
    else:
        print(summary)


if __name__ == "__main__":
    main()
