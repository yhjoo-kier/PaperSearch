"""PDF downloader for academic papers using Unpaywall API."""

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from .paper_fetcher import Paper


@dataclass
class DownloadResult:
    """Result of a PDF download attempt."""

    paper: Paper
    success: bool
    filepath: Optional[Path] = None
    error: Optional[str] = None
    source: Optional[str] = None  # e.g., "unpaywall", "doi_redirect"


class PDFDownloader:
    """Downloads PDF files for academic papers."""

    # Unpaywall API endpoint
    UNPAYWALL_API = "https://api.unpaywall.org/v2"

    def __init__(
        self,
        download_dir: str = "data/pdfs",
        email: Optional[str] = None,
        timeout: int = 60
    ):
        """Initialize PDF downloader.

        Args:
            download_dir: Directory to save downloaded PDFs.
            email: Email for Unpaywall API (required for API access).
            timeout: Request timeout in seconds.
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.email = email or os.environ.get("UNPAYWALL_EMAIL", "user@example.com")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PaperSearch/1.0 (Academic Research Tool)"
        })

    def sanitize_filename(self, title: str, max_length: int = 100) -> str:
        """Create a safe filename from paper title.

        Args:
            title: Paper title.
            max_length: Maximum filename length.

        Returns:
            Sanitized filename string.
        """
        # Remove or replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = re.sub(r'\s+', '_', filename)
        filename = re.sub(r'[^\w\-_.]', '', filename)

        # Truncate if too long
        if len(filename) > max_length:
            filename = filename[:max_length]

        return filename.strip('_')

    def get_unpaywall_pdf_url(self, doi: str) -> Optional[dict]:
        """Get PDF URL from Unpaywall API.

        Args:
            doi: Digital Object Identifier.

        Returns:
            Dict with pdf_url and source info, or None if not found.
        """
        if not doi:
            return None

        url = f"{self.UNPAYWALL_API}/{doi}"
        params = {"email": self.email}

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            # Check for best open access location
            best_oa = data.get("best_oa_location")
            if best_oa and best_oa.get("url_for_pdf"):
                return {
                    "pdf_url": best_oa["url_for_pdf"],
                    "source": best_oa.get("host_type", "unknown"),
                    "version": best_oa.get("version", "unknown"),
                    "license": best_oa.get("license", "unknown")
                }

            # Check all OA locations
            for location in data.get("oa_locations", []):
                if location.get("url_for_pdf"):
                    return {
                        "pdf_url": location["url_for_pdf"],
                        "source": location.get("host_type", "unknown"),
                        "version": location.get("version", "unknown"),
                        "license": location.get("license", "unknown")
                    }

            return None

        except requests.exceptions.RequestException as e:
            return None

    def download_pdf(self, url: str, filepath: Path) -> bool:
        """Download PDF from URL.

        Args:
            url: URL to download from.
            filepath: Path to save the PDF.

        Returns:
            True if download succeeded, False otherwise.
        """
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                stream=True,
                allow_redirects=True
            )
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
                # Try to detect PDF magic bytes
                first_bytes = next(response.iter_content(chunk_size=8), b"")
                if not first_bytes.startswith(b"%PDF"):
                    return False

                # Write the first bytes we read
                with open(filepath, "wb") as f:
                    f.write(first_bytes)
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            else:
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            # Verify file is not empty
            if filepath.stat().st_size < 1000:
                filepath.unlink()
                return False

            return True

        except Exception as e:
            if filepath.exists():
                filepath.unlink()
            return False

    def download_paper(self, paper: Paper, filename: Optional[str] = None) -> DownloadResult:
        """Download PDF for a single paper.

        Args:
            paper: Paper object with metadata.
            filename: Optional custom filename (without extension).

        Returns:
            DownloadResult with success status and file path.
        """
        if not paper.doi:
            return DownloadResult(
                paper=paper,
                success=False,
                error="No DOI available"
            )

        # Generate filename
        if filename:
            safe_filename = self.sanitize_filename(filename)
        else:
            safe_filename = self.sanitize_filename(paper.title)

        filepath = self.download_dir / f"{safe_filename}.pdf"

        # Check if already downloaded
        if filepath.exists():
            return DownloadResult(
                paper=paper,
                success=True,
                filepath=filepath,
                source="cached"
            )

        # Try Unpaywall first
        unpaywall_result = self.get_unpaywall_pdf_url(paper.doi)

        if unpaywall_result:
            pdf_url = unpaywall_result["pdf_url"]
            if self.download_pdf(pdf_url, filepath):
                return DownloadResult(
                    paper=paper,
                    success=True,
                    filepath=filepath,
                    source=f"unpaywall:{unpaywall_result['source']}"
                )

        return DownloadResult(
            paper=paper,
            success=False,
            error="PDF not available via open access"
        )

    def download_papers(
        self,
        papers: list[Paper],
        delay: float = 1.0,
        progress_callback: callable = None
    ) -> list[DownloadResult]:
        """Download PDFs for multiple papers.

        Args:
            papers: List of Paper objects.
            delay: Delay between downloads (seconds) to be polite to servers.
            progress_callback: Optional callback function(current, total, paper, result).

        Returns:
            List of DownloadResult objects.
        """
        results = []
        total = len(papers)

        for i, paper in enumerate(papers):
            result = self.download_paper(paper)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total, paper, result)

            # Rate limiting (skip if cached)
            if result.source != "cached" and i < total - 1:
                time.sleep(delay)

        return results

    def get_download_stats(self, results: list[DownloadResult]) -> dict:
        """Get statistics from download results.

        Args:
            results: List of DownloadResult objects.

        Returns:
            Dictionary with download statistics.
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        # Count by source
        sources = {}
        for r in successful:
            source = r.source or "unknown"
            sources[source] = sources.get(source, 0) + 1

        # Count failure reasons
        errors = {}
        for r in failed:
            error = r.error or "unknown"
            errors[error] = errors.get(error, 0) + 1

        return {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100 if results else 0,
            "sources": sources,
            "errors": errors
        }
