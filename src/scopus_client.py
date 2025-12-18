"""Scopus API client for paper search."""

import os
import requests
from typing import Optional


class ScopusClient:
    """Client for interacting with Scopus API."""

    BASE_URL = "https://api.elsevier.com/content/search/scopus"
    ABSTRACT_URL = "https://api.elsevier.com/content/abstract/scopus_id"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Scopus client.

        Args:
            api_key: Scopus API key. If not provided, reads from SCOPUS_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("SCOPUS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Scopus API key is required. "
                "Set SCOPUS_API_KEY environment variable or pass api_key parameter."
            )

        self.headers = {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json"
        }

    def search(
        self,
        query: str,
        count: int = 25,
        start: int = 0,
        sort: str = "-citedby-count"
    ) -> dict:
        """Search Scopus for papers matching query.

        Args:
            query: Scopus search query string.
            count: Number of results to return (max 25 per request).
            start: Starting index for pagination.
            sort: Sort order. Default is by citation count descending.

        Returns:
            Search results as dictionary.
        """
        params = {
            "query": query,
            "count": min(count, 25),
            "start": start,
            "sort": sort,
            "view": "COMPLETE"
        }

        response = requests.get(
            self.BASE_URL,
            headers=self.headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def get_abstract(self, scopus_id: str) -> dict:
        """Get full abstract for a paper by Scopus ID.

        Args:
            scopus_id: Scopus ID of the paper.

        Returns:
            Abstract data as dictionary.
        """
        url = f"{self.ABSTRACT_URL}/{scopus_id}"
        params = {"view": "FULL"}

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def search_all(self, query: str, total_count: int = 100) -> list[dict]:
        """Search and retrieve multiple pages of results.

        Args:
            query: Scopus search query string.
            total_count: Total number of results to retrieve.

        Returns:
            List of all search result entries.
        """
        all_results = []
        start = 0

        while len(all_results) < total_count:
            remaining = total_count - len(all_results)
            count = min(25, remaining)

            result = self.search(query, count=count, start=start)
            entries = result.get("search-results", {}).get("entry", [])

            if not entries:
                break

            all_results.extend(entries)
            start += len(entries)

            total_available = int(
                result.get("search-results", {}).get("opensearch:totalResults", 0)
            )
            if start >= total_available:
                break

        return all_results[:total_count]
