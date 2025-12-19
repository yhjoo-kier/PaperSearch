"""Paper fetcher and data storage for Scopus search results."""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .scopus_client import ScopusClient
from .query_builder import QueryBuilder, build_query_from_topic


@dataclass
class Paper:
    """Represents a paper with its metadata."""

    scopus_id: str
    title: str
    abstract: str
    authors: list[str]
    publication_name: str
    publication_date: str
    citation_count: int
    doi: Optional[str] = None
    keywords: list[str] = None
    url: Optional[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_scopus_entry(cls, entry: dict) -> "Paper":
        """Create Paper from Scopus API entry."""
        # Extract authors
        authors = []
        if "author" in entry:
            for author in entry.get("author", []):
                name = author.get("authname", "")
                if name:
                    authors.append(name)

        # Extract keywords
        keywords = []
        if "authkeywords" in entry:
            kw_str = entry.get("authkeywords", "")
            if kw_str:
                keywords = [k.strip() for k in kw_str.split("|")]

        # Get Scopus ID
        scopus_id = entry.get("dc:identifier", "").replace("SCOPUS_ID:", "")

        return cls(
            scopus_id=scopus_id,
            title=entry.get("dc:title", "No title"),
            abstract=entry.get("dc:description", "No abstract available"),
            authors=authors,
            publication_name=entry.get("prism:publicationName", "Unknown"),
            publication_date=entry.get("prism:coverDate", "Unknown"),
            citation_count=int(entry.get("citedby-count", 0)),
            doi=entry.get("prism:doi"),
            keywords=keywords,
            url=entry.get("prism:url"),
        )


class PaperFetcher:
    """Fetches and stores papers from Scopus."""

    def __init__(
        self,
        data_dir: str = "data/papers",
        api_key: Optional[str] = None
    ):
        """Initialize paper fetcher.

        Args:
            data_dir: Directory to store paper data.
            api_key: Scopus API key (optional, uses env var if not provided).
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.client = ScopusClient(api_key=api_key)

    def fetch_papers(
        self,
        query: str,
        count: int = 50,
        save: bool = True
    ) -> list[Paper]:
        """Fetch papers matching query.

        Args:
            query: Scopus search query.
            count: Number of papers to fetch.
            save: Whether to save results to file.

        Returns:
            List of Paper objects.
        """
        entries = self.client.search_all(query, total_count=count)
        papers = [Paper.from_scopus_entry(entry) for entry in entries]

        if save and papers:
            self._save_papers(papers, query)

        return papers

    def fetch_by_topic(
        self,
        topic: str,
        count: int = 50,
        additional_terms: Optional[list[str]] = None,
        additional_terms_or: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        save: bool = True
    ) -> tuple[str, list[Paper]]:
        """Fetch papers by topic with automatic query building.

        Args:
            topic: Research topic.
            count: Number of papers to fetch.
            additional_terms: Additional search terms with AND operator.
            additional_terms_or: Additional search terms with OR operator.
            exclude: Terms to exclude.
            year_from: Start year filter.
            year_to: End year filter.
            save: Whether to save results.

        Returns:
            Tuple of (query_string, list of Papers).
        """
        query = build_query_from_topic(
            topic=topic,
            additional_terms=additional_terms,
            additional_terms_or=additional_terms_or,
            exclude=exclude,
            year_from=year_from,
            year_to=year_to
        )

        papers = self.fetch_papers(query, count=count, save=save)
        return query, papers

    def _save_papers(self, papers: list[Paper], query: str) -> Path:
        """Save papers to JSON file.

        Args:
            papers: List of papers to save.
            query: Query used to fetch papers.

        Returns:
            Path to saved file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"papers_{timestamp}.json"
        filepath = self.data_dir / filename

        data = {
            "query": query,
            "fetched_at": datetime.now().isoformat(),
            "count": len(papers),
            "papers": [p.to_dict() for p in papers]
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    def load_papers(self, filepath: str) -> tuple[dict, list[Paper]]:
        """Load papers from JSON file.

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

    def get_latest_papers_file(self) -> Optional[Path]:
        """Get the most recently created papers file.

        Returns:
            Path to latest file, or None if no files exist.
        """
        files = list(self.data_dir.glob("papers_*.json"))
        if not files:
            return None
        return max(files, key=lambda f: f.stat().st_mtime)


def generate_review_summary(papers: list[Paper], query: str) -> str:
    """Generate a summary for AI agent review.

    Args:
        papers: List of papers to summarize.
        query: Original search query.

    Returns:
        Formatted summary string for review.
    """
    lines = [
        "# Paper Search Results for Review",
        "",
        f"**Search Query:** `{query}`",
        f"**Total Papers:** {len(papers)}",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "---",
        "",
    ]

    for i, paper in enumerate(papers, 1):
        lines.extend([
            f"## Paper {i}: {paper.title}",
            "",
            f"**Scopus ID:** {paper.scopus_id}",
            f"**Authors:** {', '.join(paper.authors[:5])}{'...' if len(paper.authors) > 5 else ''}",
            f"**Publication:** {paper.publication_name}",
            f"**Date:** {paper.publication_date}",
            f"**Citations:** {paper.citation_count}",
        ])

        if paper.doi:
            lines.append(f"**DOI:** https://doi.org/{paper.doi}")

        if paper.keywords:
            lines.append(f"**Keywords:** {', '.join(paper.keywords[:10])}")

        lines.extend([
            "",
            "### Abstract",
            "",
            paper.abstract if paper.abstract else "No abstract available.",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)
