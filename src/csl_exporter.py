"""CSL JSON format exporter for Zotero and other reference managers."""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .paper_fetcher import Paper


@dataclass
class ExportResult:
    """Result of a CSL JSON export operation."""
    success: bool
    filepath: Optional[Path] = None
    paper_count: int = 0
    error: Optional[str] = None


class CSLExporter:
    """Exports papers to CSL JSON format for reference managers like Zotero.

    CSL JSON is the recommended format for Zotero as it provides the most
    accurate representation of bibliographic data.
    """

    def __init__(self, output_dir: str = "data/papers"):
        """Initialize CSL JSON exporter.

        Args:
            output_dir: Directory to save CSL JSON files.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _parse_author(self, author_name: str) -> dict:
        """Parse author name into family and given names.

        Scopus provides names in formats like:
        - "LastName F.M."
        - "LastName F."
        - "LastName FirstName"

        Args:
            author_name: Author name string from Scopus.

        Returns:
            Dictionary with 'family' and optionally 'given' keys.
        """
        author_name = author_name.strip()

        # Split by space
        parts = author_name.split()

        if len(parts) == 0:
            return {"literal": author_name}

        # First part is typically the family name
        family = parts[0].rstrip(',')

        # Remaining parts are given names/initials
        given_parts = parts[1:] if len(parts) > 1 else []

        result = {"family": family}

        if given_parts:
            # Join all given name parts
            given = " ".join(given_parts)
            result["given"] = given

        return result

    def _parse_date(self, date_str: str) -> Optional[dict]:
        """Parse date string to CSL JSON date format.

        Args:
            date_str: Date in "YYYY-MM-DD" or "YYYY" format.

        Returns:
            Dictionary with 'date-parts' key containing nested list.
        """
        if not date_str or date_str == "Unknown":
            return None

        date_str = date_str.strip()

        # YYYY-MM-DD format
        if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
            parts = date_str[:10].split('-')
            return {
                "date-parts": [[int(parts[0]), int(parts[1]), int(parts[2])]]
            }

        # YYYY-MM format
        if re.match(r'^\d{4}-\d{2}', date_str):
            parts = date_str[:7].split('-')
            return {
                "date-parts": [[int(parts[0]), int(parts[1])]]
            }

        # YYYY format only
        if re.match(r'^\d{4}$', date_str):
            return {
                "date-parts": [[int(date_str)]]
            }

        # Try to extract year
        year_match = re.search(r'\d{4}', date_str)
        if year_match:
            return {
                "date-parts": [[int(year_match.group())]]
            }

        return None

    def paper_to_csl(self, paper: Paper) -> dict:
        """Convert a Paper object to CSL JSON format.

        Args:
            paper: Paper object to convert.

        Returns:
            Dictionary in CSL JSON format.
        """
        csl_item = {
            "id": paper.scopus_id,
            "type": "article-journal",
        }

        # Title (required)
        if paper.title and paper.title != "No title":
            csl_item["title"] = paper.title

        # Authors
        if paper.authors:
            csl_item["author"] = [
                self._parse_author(author)
                for author in paper.authors
                if author
            ]

        # Abstract
        if paper.abstract and paper.abstract != "No abstract available":
            csl_item["abstract"] = paper.abstract

        # Journal/Publication name
        if paper.publication_name and paper.publication_name != "Unknown":
            csl_item["container-title"] = paper.publication_name

        # Publication date
        issued = self._parse_date(paper.publication_date)
        if issued:
            csl_item["issued"] = issued

        # DOI
        if paper.doi:
            csl_item["DOI"] = paper.doi

        # Keywords
        if paper.keywords:
            # CSL JSON uses comma-separated string for keywords
            csl_item["keyword"] = ", ".join(paper.keywords)

        # URL
        if paper.url:
            csl_item["URL"] = paper.url

        # Citation count (as note)
        if paper.citation_count > 0:
            csl_item["note"] = f"Citation count: {paper.citation_count}"

        return csl_item

    def export_papers(
        self,
        papers: list[Paper],
        filename: Optional[str] = None,
    ) -> ExportResult:
        """Export multiple papers to a single CSL JSON file.

        Args:
            papers: List of Paper objects.
            filename: Custom filename (without extension).

        Returns:
            ExportResult with success status and file path.
        """
        if not papers:
            return ExportResult(
                success=False,
                error="No papers to export"
            )

        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"papers_{timestamp}"

            # Ensure .json extension
            if not filename.endswith('.json'):
                filename = f"{filename}.json"

            filepath = self.output_dir / filename

            # Convert all papers to CSL JSON
            csl_items = [self.paper_to_csl(paper) for paper in papers]

            # Write file with UTF-8 encoding (Zotero compatible)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(csl_items, f, ensure_ascii=False, indent=2)

            return ExportResult(
                success=True,
                filepath=filepath,
                paper_count=len(papers)
            )

        except Exception as e:
            return ExportResult(
                success=False,
                error=str(e)
            )

    def export_from_json(
        self,
        json_filepath: str,
        output_filename: Optional[str] = None
    ) -> ExportResult:
        """Export papers from an existing JSON file to CSL JSON.

        Args:
            json_filepath: Path to JSON file with paper data.
            output_filename: Custom output filename (optional).

        Returns:
            ExportResult with success status and file path.
        """
        try:
            with open(json_filepath, "r", encoding="utf-8") as f:
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

            # Use same base filename if not provided
            if not output_filename:
                json_path = Path(json_filepath)
                output_filename = json_path.stem  # e.g., "papers_20241201_120000"

            return self.export_papers(
                papers=papers,
                filename=output_filename
            )

        except Exception as e:
            return ExportResult(
                success=False,
                error=f"Failed to load JSON: {str(e)}"
            )
