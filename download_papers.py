#!/usr/bin/env python3
"""CLI script for downloading PDF papers.

Usage:
    # Interactive mode - select papers to download
    python download_papers.py --load data/papers/papers_20241201_120000.json

    # Download specific papers by index
    python download_papers.py --load data/papers/papers_*.json --select 1,3,5-10

    # Download all papers with DOI
    python download_papers.py --load data/papers/papers_*.json --all

    # Use latest search results
    python download_papers.py --latest --select 1-5
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Fix Windows encoding issues with special characters
os.environ['PYTHONIOENCODING'] = 'utf-8'

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.paper_fetcher import Paper
from src.pdf_downloader import PDFDownloader, DownloadResult


def load_papers_from_json(filepath: str) -> tuple[dict, list[Paper]]:
    """Load papers from JSON file without requiring API key.

    Args:
        filepath: Path to JSON file.

    Returns:
        Tuple of (metadata dict, list of Papers).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    papers = []
    for p in data.get("papers", []):
        papers.append(Paper(
            scopus_id=p["scopus_id"],
            title=p["title"],
            abstract=p["abstract"],
            authors=p["authors"],
            publication_name=p["publication_name"],
            publication_date=p["publication_date"],
            citation_count=p["citation_count"],
            doi=p.get("doi"),
            keywords=p.get("keywords", []),
            url=p.get("url"),
        ))

    metadata = {
        "query": data.get("query"),
        "fetched_at": data.get("fetched_at"),
        "count": data.get("count"),
    }

    return metadata, papers


def get_latest_papers_file(data_dir: str = "data/papers") -> Optional[Path]:
    """Get the most recently created papers file.

    Args:
        data_dir: Directory containing paper JSON files.

    Returns:
        Path to latest file, or None if no files exist.
    """
    papers_dir = Path(data_dir)
    if not papers_dir.exists():
        return None

    files = list(papers_dir.glob("papers_*.json"))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


def print_paper_list(papers: list[Paper], show_doi: bool = True) -> None:
    """Print numbered list of papers.

    Args:
        papers: List of papers to display.
        show_doi: Whether to show DOI availability.
    """
    print("\n" + "=" * 80)
    print("Available Papers")
    print("=" * 80)

    for i, paper in enumerate(papers, 1):
        doi_status = "[DOI]" if paper.doi else "[No DOI]"
        title = paper.title[:60] + "..." if len(paper.title) > 60 else paper.title

        print(f"\n{i:3d}. {title}")
        print(f"     Authors: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}")
        print(f"     {paper.publication_name} ({paper.publication_date[:4]})")
        print(f"     Citations: {paper.citation_count} {doi_status if show_doi else ''}")

    print("\n" + "=" * 80)


def parse_selection(selection_str: str, max_index: int) -> list[int]:
    """Parse selection string like "1,3,5-10" into list of indices.

    Args:
        selection_str: Selection string (e.g., "1,3,5-10,15").
        max_index: Maximum valid index.

    Returns:
        List of 0-based indices.
    """
    indices = set()
    parts = selection_str.replace(" ", "").split(",")

    for part in parts:
        if "-" in part:
            # Range: e.g., "5-10"
            try:
                start, end = part.split("-", 1)
                start_idx = int(start)
                end_idx = int(end)
                for i in range(start_idx, end_idx + 1):
                    if 1 <= i <= max_index:
                        indices.add(i - 1)  # Convert to 0-based
            except ValueError:
                print(f"Warning: Invalid range '{part}', skipping", file=sys.stderr)
        else:
            # Single index
            try:
                idx = int(part)
                if 1 <= idx <= max_index:
                    indices.add(idx - 1)  # Convert to 0-based
                else:
                    print(f"Warning: Index {idx} out of range (1-{max_index}), skipping", file=sys.stderr)
            except ValueError:
                print(f"Warning: Invalid index '{part}', skipping", file=sys.stderr)

    return sorted(indices)


def interactive_select(papers: list[Paper]) -> list[int]:
    """Interactively select papers to download.

    Args:
        papers: List of available papers.

    Returns:
        List of 0-based indices of selected papers.
    """
    print_paper_list(papers)

    print("\nSelection Options:")
    print("  - Enter paper numbers: 1,3,5 or 1-5,10,15-20")
    print("  - Enter 'all' to download all papers with DOI")
    print("  - Enter 'q' or 'quit' to cancel")
    print()

    while True:
        try:
            user_input = input("Select papers to download: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return []

        if user_input in ('q', 'quit', 'exit'):
            print("Download cancelled.")
            return []

        if user_input == 'all':
            # Select all papers with DOI
            return [i for i, p in enumerate(papers) if p.doi]

        if user_input:
            indices = parse_selection(user_input, len(papers))
            if indices:
                return indices
            print("No valid selections. Please try again.")


def print_progress(current: int, total: int, paper: Paper, result: DownloadResult) -> None:
    """Print download progress.

    Args:
        current: Current paper number (1-based).
        total: Total number of papers.
        paper: Paper being processed.
        result: Download result.
    """
    status = "OK" if result.success else "FAILED"
    title = paper.title[:50] + "..." if len(paper.title) > 50 else paper.title

    if result.success:
        source_info = f" ({result.source})" if result.source else ""
        print(f"[{current}/{total}] {status}{source_info}: {title}")
    else:
        error_info = f" - {result.error}" if result.error else ""
        print(f"[{current}/{total}] {status}{error_info}: {title}")


def print_summary(results: list[DownloadResult], download_dir: Path) -> None:
    """Print download summary.

    Args:
        results: List of download results.
        download_dir: Directory where PDFs were saved.
    """
    downloader = PDFDownloader()
    stats = downloader.get_download_stats(results)

    print("\n" + "=" * 80)
    print("Download Summary")
    print("=" * 80)
    print(f"Total requested: {stats['total']}")
    print(f"Successfully downloaded: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")

    if stats['sources']:
        print("\nDownload sources:")
        for source, count in sorted(stats['sources'].items()):
            print(f"  - {source}: {count}")

    if stats['errors']:
        print("\nFailure reasons:")
        for error, count in sorted(stats['errors'].items()):
            print(f"  - {error}: {count}")

    print(f"\nDownload directory: {download_dir.absolute()}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Download PDF papers from search results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode - select papers to download
  python download_papers.py --load data/papers/papers_20241201_120000.json

  # Download specific papers by index
  python download_papers.py --load data/papers/papers_*.json --select 1,3,5-10

  # Download all papers with DOI
  python download_papers.py --load data/papers/papers_*.json --all

  # Use latest search results
  python download_papers.py --latest --select 1-5

  # Specify output directory
  python download_papers.py --latest --all --output-dir ./my_pdfs
        """
    )

    # Input options
    parser.add_argument(
        "--load", "-l",
        help="Load papers from JSON file"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use the latest search results file"
    )

    # Selection options
    parser.add_argument(
        "--select", "-s",
        help="Paper indices to download (e.g., '1,3,5-10')"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        dest="download_all",
        help="Download all papers with DOI"
    )

    # Output options
    parser.add_argument(
        "--output-dir", "-o",
        default="data/pdfs",
        help="Directory to save PDFs (default: data/pdfs)"
    )
    parser.add_argument(
        "--email",
        help="Email for Unpaywall API (or set UNPAYWALL_EMAIL env var)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between downloads in seconds (default: 1.0)"
    )

    # Source options
    parser.add_argument(
        "--no-elsevier",
        action="store_true",
        help="Disable Elsevier ScienceDirect API (uses SCOPUS_API_KEY)"
    )
    parser.add_argument(
        "--no-unpaywall",
        action="store_true",
        help="Disable Unpaywall API (open access)"
    )

    # Display options
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list papers, don't download"
    )

    args = parser.parse_args()

    # Validate input arguments
    if not args.load and not args.latest:
        parser.error("One of --load or --latest is required")

    # Load papers
    if args.latest:
        latest_file = get_latest_papers_file()
        if not latest_file:
            print("Error: No saved papers found in data/papers/", file=sys.stderr)
            sys.exit(1)
        print(f"Using latest file: {latest_file}", file=sys.stderr)
        metadata, papers = load_papers_from_json(str(latest_file))
    else:
        print(f"Loading papers from: {args.load}", file=sys.stderr)
        metadata, papers = load_papers_from_json(args.load)

    print(f"Loaded {len(papers)} papers", file=sys.stderr)

    if not papers:
        print("No papers to process.", file=sys.stderr)
        sys.exit(0)

    # List only mode
    if args.list_only:
        print_paper_list(papers)
        sys.exit(0)

    # Determine which papers to download
    if args.download_all:
        # All papers with DOI
        selected_indices = [i for i, p in enumerate(papers) if p.doi]
        if not selected_indices:
            print("No papers have DOI available for download.", file=sys.stderr)
            sys.exit(0)
    elif args.select:
        # Specific selection
        selected_indices = parse_selection(args.select, len(papers))
        if not selected_indices:
            print("No valid paper indices selected.", file=sys.stderr)
            sys.exit(1)
    else:
        # Interactive mode
        selected_indices = interactive_select(papers)
        if not selected_indices:
            sys.exit(0)

    # Get selected papers
    selected_papers = [papers[i] for i in selected_indices]

    # Count papers with DOI
    papers_with_doi = [p for p in selected_papers if p.doi]
    papers_without_doi = [p for p in selected_papers if not p.doi]

    print(f"\nSelected {len(selected_papers)} papers:")
    print(f"  - {len(papers_with_doi)} with DOI (downloadable)")
    print(f"  - {len(papers_without_doi)} without DOI (will be skipped)")

    if not papers_with_doi:
        print("\nNo papers with DOI to download.", file=sys.stderr)
        sys.exit(0)

    # Confirm before download
    try:
        confirm = input(f"\nProceed to download {len(papers_with_doi)} papers? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(0)

    if confirm and confirm not in ('y', 'yes'):
        print("Download cancelled.")
        sys.exit(0)

    # Initialize downloader
    use_elsevier = not args.no_elsevier
    use_unpaywall = not args.no_unpaywall

    downloader = PDFDownloader(
        download_dir=args.output_dir,
        email=args.email,
        use_elsevier=use_elsevier,
        use_unpaywall=use_unpaywall
    )

    # Show download sources status
    print(f"\nDownloading to: {Path(args.output_dir).absolute()}")
    print("Download sources:")
    if downloader.use_elsevier:
        print("  - Elsevier ScienceDirect API: ENABLED (using SCOPUS_API_KEY)")
    else:
        if use_elsevier and not downloader.api_key:
            print("  - Elsevier ScienceDirect API: DISABLED (no API key found)")
        else:
            print("  - Elsevier ScienceDirect API: DISABLED")
    if downloader.use_unpaywall:
        print("  - Unpaywall (open access): ENABLED")
    else:
        print("  - Unpaywall (open access): DISABLED")
    print("-" * 80)

    # Download papers
    results = downloader.download_papers(
        papers_with_doi,
        delay=args.delay,
        progress_callback=print_progress
    )

    # Print summary
    print_summary(results, Path(args.output_dir))

    # Exit with error code if any downloads failed
    if any(not r.success for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
