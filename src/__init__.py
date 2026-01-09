"""PaperSearch - Scopus paper search and review framework."""

from .scopus_client import ScopusClient
from .query_builder import QueryBuilder, build_query_from_topic
from .paper_fetcher import Paper, PaperFetcher, generate_review_summary
from .pdf_downloader import PDFDownloader, DownloadResult
from .csl_exporter import CSLExporter, ExportResult

__all__ = [
    "ScopusClient",
    "QueryBuilder",
    "build_query_from_topic",
    "Paper",
    "PaperFetcher",
    "generate_review_summary",
    "PDFDownloader",
    "DownloadResult",
    "CSLExporter",
    "ExportResult",
]
