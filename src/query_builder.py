"""Scopus query builder for constructing search queries."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueryBuilder:
    """Builder for Scopus search queries.

    Scopus uses a specific query syntax:
    - TITLE-ABS-KEY(term): Search in title, abstract, and keywords
    - TITLE(term): Search in title only
    - ABS(term): Search in abstract only
    - KEY(term): Search in keywords only
    - AUTH(name): Search by author
    - PUBYEAR: Filter by publication year
    - SUBJAREA: Filter by subject area

    Boolean operators: AND, OR, AND NOT
    """

    terms: list[str] = field(default_factory=list)
    exclude_terms: list[str] = field(default_factory=list)
    title_terms: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    subject_areas: list[str] = field(default_factory=list)
    _raw_query: Optional[str] = None

    def add_term(self, term: str) -> "QueryBuilder":
        """Add a search term (searches title, abstract, keywords)."""
        self.terms.append(term)
        return self

    def add_terms(self, terms: list[str]) -> "QueryBuilder":
        """Add multiple search terms."""
        self.terms.extend(terms)
        return self

    def exclude_term(self, term: str) -> "QueryBuilder":
        """Add a term to exclude from results."""
        self.exclude_terms.append(term)
        return self

    def add_title_term(self, term: str) -> "QueryBuilder":
        """Add a term that must appear in the title."""
        self.title_terms.append(term)
        return self

    def add_author(self, author: str) -> "QueryBuilder":
        """Add an author name to filter by."""
        self.authors.append(author)
        return self

    def set_year_range(
        self, year_from: Optional[int] = None, year_to: Optional[int] = None
    ) -> "QueryBuilder":
        """Set publication year range."""
        self.year_from = year_from
        self.year_to = year_to
        return self

    def add_subject_area(self, area: str) -> "QueryBuilder":
        """Add subject area filter.

        Common subject areas:
        - COMP: Computer Science
        - ENGI: Engineering
        - MEDI: Medicine
        - PHYS: Physics
        - CHEM: Chemistry
        - BIOC: Biochemistry
        - MATH: Mathematics
        - MATE: Materials Science
        """
        self.subject_areas.append(area)
        return self

    def set_raw_query(self, query: str) -> "QueryBuilder":
        """Set a raw Scopus query string directly."""
        self._raw_query = query
        return self

    def build(self) -> str:
        """Build the Scopus query string."""
        if self._raw_query:
            return self._raw_query

        parts = []

        # Add main search terms
        if self.terms:
            term_queries = [f'TITLE-ABS-KEY("{t}")' for t in self.terms]
            parts.append(f"({' AND '.join(term_queries)})")

        # Add title-specific terms
        if self.title_terms:
            title_queries = [f'TITLE("{t}")' for t in self.title_terms]
            parts.append(f"({' AND '.join(title_queries)})")

        # Add author filters
        if self.authors:
            auth_queries = [f'AUTH("{a}")' for a in self.authors]
            parts.append(f"({' OR '.join(auth_queries)})")

        # Add subject area filters
        if self.subject_areas:
            area_queries = [f"SUBJAREA({a})" for a in self.subject_areas]
            parts.append(f"({' OR '.join(area_queries)})")

        # Combine with AND
        query = " AND ".join(parts) if parts else ""

        # Add year range
        if self.year_from and self.year_to:
            query += f" AND PUBYEAR > {self.year_from - 1} AND PUBYEAR < {self.year_to + 1}"
        elif self.year_from:
            query += f" AND PUBYEAR > {self.year_from - 1}"
        elif self.year_to:
            query += f" AND PUBYEAR < {self.year_to + 1}"

        # Add exclusions
        if self.exclude_terms:
            for term in self.exclude_terms:
                query += f' AND NOT TITLE-ABS-KEY("{term}")'

        return query.strip()


def build_query_from_topic(
    topic: str,
    additional_terms: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    subject_areas: Optional[list[str]] = None,
) -> str:
    """Convenience function to build a query from a topic description.

    Args:
        topic: Main research topic.
        additional_terms: Additional terms to include.
        exclude: Terms to exclude.
        year_from: Start year for publication filter.
        year_to: End year for publication filter.
        subject_areas: Subject area codes to filter by.

    Returns:
        Scopus query string.
    """
    builder = QueryBuilder()
    builder.add_term(topic)

    if additional_terms:
        builder.add_terms(additional_terms)

    if exclude:
        for term in exclude:
            builder.exclude_term(term)

    if year_from or year_to:
        builder.set_year_range(year_from, year_to)

    if subject_areas:
        for area in subject_areas:
            builder.add_subject_area(area)

    return builder.build()
