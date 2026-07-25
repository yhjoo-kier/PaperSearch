"""Full-text and figure extraction for academic papers (beyond PDF download).

Why this exists
---------------
`pdf_downloader.py` gives you a PDF or nothing. That is the wrong abstraction for
two common situations:

1. **The PDF is entitlement-blocked but the text is not.** Elsevier grants
   text-and-data-mining (TDM) access separately from PDF download. The very same
   API key that returns ``X-ELS-Status: WARNING - Response limited to first page``
   for ``Accept: application/pdf`` often returns ``X-ELS-Status: OK`` with the
   complete article for ``Accept: text/xml``. Verified 2026-07-25 on 23/23
   Elsevier papers whose PDFs were all blocked.

2. **You want figures, not pages.** For figure/caption analysis, page renders are
   strictly worse than the publisher's original images: you lose resolution, and
   captions have to be OCR'd out of the page instead of read from the XML.

So this module fetches *content* — full text, figure captions, and original
figure images — rather than a document container.

Gotchas encoded here (each cost real debugging time)
----------------------------------------------------
- The ``/article/entitlement/`` endpoint can return **403 while the actual
  content endpoints work**. Never use it as a gate; probe the real endpoint.
- Figure image locators live in the XML as ``pii:<PII>/gr1``; the object endpoint
  wants only the trailing ``gr1``. The ``_lrg`` (large) variant 404s — request
  the bare reference.
- Elsevier echoes your API key back in the ``X-ELS-APIKey`` response header.
  Never log raw response headers.
- Springer needs no API for the PDF itself: ``link.springer.com/content/pdf/<DOI>.pdf``
  honours institutional IP directly.
"""

import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import requests

# Elsevier full-text XML namespaces
NS = {
    "ce": "http://www.elsevier.com/xml/common/dtd",
    "xocs": "http://www.elsevier.com/xml/xocs/dtd",
    "xlink": "http://www.w3.org/1999/xlink",
}
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


@dataclass
class FigureRef:
    """One figure in an article: its label, caption text, and image locators."""

    label: str
    caption: str
    refs: List[str] = field(default_factory=list)  # e.g. ["gr1"]
    saved: List[Path] = field(default_factory=list)


@dataclass
class FullTextResult:
    """Outcome of a full-text fetch attempt."""

    doi: str
    success: bool
    source: Optional[str] = None  # "elsevier-xml" | "springer-pdf"
    pii: Optional[str] = None
    path: Optional[Path] = None
    figures: List[FigureRef] = field(default_factory=list)
    els_status: Optional[str] = None
    error: Optional[str] = None

    @property
    def n_images(self) -> int:
        return sum(len(f.saved) for f in self.figures)


class FullTextFetcher:
    """Fetches article full text and figure images from publisher content APIs.

    Routes, in the order :meth:`fetch` tries them:

    1. Elsevier TDM full-text XML  (needs SCOPUS_API_KEY + institutional IP)
    2. Springer direct PDF          (needs institutional IP only)

    Both are independent of PDF entitlement, so this often succeeds where
    :class:`~src.pdf_downloader.PDFDownloader` returns nothing.
    """

    ELSEVIER_ARTICLE = "https://api.elsevier.com/content/article"
    ELSEVIER_OBJECT = "https://api.elsevier.com/content/object/pii"
    SPRINGER_PDF_BASE = "https://link.springer.com/content/pdf"

    def __init__(
        self,
        output_dir: str = "data/fulltext",
        api_key: Optional[str] = None,
        timeout: int = 90,
        object_pause: float = 2.0,
    ):
        """Initialize the fetcher.

        Args:
            output_dir: Directory for XML, PDF, and figure image output.
            api_key: Elsevier API key (uses SCOPUS_API_KEY env var if omitted).
            timeout: Per-request timeout in seconds.
            object_pause: Seconds to sleep between figure-image requests. Figure
                fetches are one request per image, so a paper can be 30 requests;
                keep this non-zero to stay polite to the API.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key or os.environ.get("SCOPUS_API_KEY")
        self.timeout = timeout
        self.object_pause = object_pause

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PaperSearch/1.0 (Academic Research Tool)"
        })

    # ------------------------------------------------------------------ helpers

    def _els_get(self, url: str, accept: Optional[str] = None) -> requests.Response:
        headers = {"X-ELS-APIKey": self.api_key or ""}
        if accept:
            headers["Accept"] = accept
        return self.session.get(url, headers=headers, timeout=self.timeout)

    @staticmethod
    def _is_entitled(els_status: str) -> bool:
        """True unless Elsevier says the response was truncated for entitlement."""
        s = (els_status or "").lower()
        return not ("not entitled" in s or "first page" in s)

    # -------------------------------------------------------------- elsevier xml

    def fetch_elsevier_xml(self, doi: str) -> FullTextResult:
        """Fetch Elsevier TDM full-text XML for a DOI.

        Succeeds for many articles whose PDF endpoint is entitlement-blocked,
        because TDM entitlement is granted separately.
        """
        if not self.api_key:
            return FullTextResult(doi=doi, success=False, error="SCOPUS_API_KEY not set")

        url = f"{self.ELSEVIER_ARTICLE}/doi/{doi}"
        try:
            resp = self._els_get(url, accept="text/xml")
        except requests.RequestException as exc:
            return FullTextResult(doi=doi, success=False, error=f"{type(exc).__name__}: {exc}")

        els_status = resp.headers.get("X-ELS-Status", "")
        if resp.status_code != 200:
            return FullTextResult(doi=doi, success=False, els_status=els_status,
                                  error=f"HTTP {resp.status_code}")
        if not self._is_entitled(els_status):
            return FullTextResult(doi=doi, success=False, els_status=els_status,
                                  error="TDM access not entitled for this title")
        if len(resp.content) < 5000:
            return FullTextResult(doi=doi, success=False, els_status=els_status,
                                  error=f"suspiciously small body ({len(resp.content)} B)")

        pii_match = re.search(rb"<xocs:pii-unformatted>([^<]+)<", resp.content)
        pii = pii_match.group(1).decode() if pii_match else None
        path = self.output_dir / f"{(pii or doi).replace('/', '_')}.xml"
        path.write_bytes(resp.content)

        try:
            figures = self.parse_figures(resp.content)
        except ET.ParseError as exc:
            figures = []
            return FullTextResult(doi=doi, success=True, source="elsevier-xml", pii=pii,
                                  path=path, figures=figures, els_status=els_status,
                                  error=f"saved but unparseable: {exc}")

        return FullTextResult(doi=doi, success=True, source="elsevier-xml", pii=pii,
                              path=path, figures=figures, els_status=els_status)

    @staticmethod
    def parse_figures(xml_bytes: bytes) -> List[FigureRef]:
        """Extract figure labels, captions, and image locators from full-text XML."""
        root = ET.fromstring(xml_bytes)
        out: List[FigureRef] = []
        for fig in root.findall(".//ce:figure", NS):
            label_el = fig.find("ce:label", NS)
            cap_el = fig.find("ce:caption", NS)
            label = "".join(label_el.itertext()).strip() if label_el is not None else (fig.get("id") or "?")
            caption = re.sub(r"\s+", " ", "".join(cap_el.itertext()).strip()) if cap_el is not None else ""
            refs = []
            for link in fig.findall(".//ce:link", NS):
                href = link.get(XLINK_HREF) or link.get("locator") or ""
                if href:
                    refs.append(href.split("/")[-1])  # "pii:S123.../gr1" -> "gr1"
            out.append(FigureRef(label=label, caption=caption, refs=refs))
        return out

    @staticmethod
    def sections(xml_bytes: bytes) -> List[str]:
        """Return section titles, useful for screening (e.g. 'is there an experiment?')."""
        root = ET.fromstring(xml_bytes)
        return [re.sub(r"\s+", " ", "".join(t.itertext())).strip()
                for t in root.findall(".//ce:section-title", NS)]

    @staticmethod
    def body_text(xml_bytes: bytes) -> str:
        """Full text with the bibliography stripped.

        Dropping references matters for keyword screening: otherwise every paper
        that *cites* an experimental study looks like it *contains* one.
        """
        root = ET.fromstring(xml_bytes)
        for bib in root.findall(".//ce:bibliography", NS):
            for child in list(bib):
                bib.remove(child)
        return re.sub(r"\s+", " ", "".join(root.itertext()))

    def download_figures(self, pii: str, figures: List[FigureRef],
                         outdir: Optional[Path] = None) -> int:
        """Download original figure images via the Elsevier object endpoint.

        Note the ``_lrg`` variant 404s; request the bare reference.

        Returns:
            Number of images saved (also recorded on each FigureRef.saved).
        """
        outdir = Path(outdir) if outdir else (self.output_dir / f"figs_{pii}")
        outdir.mkdir(parents=True, exist_ok=True)
        saved = 0
        for fig in figures:
            for ref in fig.refs:
                time.sleep(self.object_pause)
                try:
                    resp = self._els_get(f"{self.ELSEVIER_OBJECT}/{pii}/ref/{ref}")
                except requests.RequestException:
                    continue
                if resp.status_code != 200:
                    continue
                if not resp.headers.get("Content-Type", "").startswith("image"):
                    continue
                ext = "png" if resp.content[:4] == b"\x89PNG" else "jpg"
                path = outdir / f"{pii}_{ref}.{ext}"
                path.write_bytes(resp.content)
                fig.saved.append(path)
                saved += 1
        return saved

    # ------------------------------------------------------------- springer pdf

    def fetch_springer_pdf(self, doi: str) -> FullTextResult:
        """Fetch a Springer PDF directly. Institutional IP is enough; no API key."""
        url = f"{self.SPRINGER_PDF_BASE}/{doi}.pdf"
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        except requests.RequestException as exc:
            return FullTextResult(doi=doi, success=False, error=f"{type(exc).__name__}: {exc}")
        if resp.status_code != 200 or resp.content[:4] != b"%PDF":
            return FullTextResult(doi=doi, success=False,
                                  error=f"HTTP {resp.status_code}, not a PDF body")
        path = self.output_dir / f"{doi.replace('/', '_')}.pdf"
        path.write_bytes(resp.content)
        return FullTextResult(doi=doi, success=True, source="springer-pdf", path=path)

    # ------------------------------------------------------------------- driver

    def fetch(self, doi: str, with_figures: bool = True) -> FullTextResult:
        """Try every content route for a DOI and return the first success."""
        if doi.startswith("10.1016") or doi.startswith("10.1006"):
            result = self.fetch_elsevier_xml(doi)
            if result.success:
                if with_figures and result.pii and result.figures:
                    self.download_figures(result.pii, result.figures)
                return result
            elsevier_error = result.error
        else:
            elsevier_error = None

        if doi.startswith("10.1007") or doi.startswith("10.1038") or doi.startswith("10.1140"):
            result = self.fetch_springer_pdf(doi)
            if result.success:
                return result

        # Last resort: Elsevier XML for a non-Elsevier-looking DOI costs one call.
        if elsevier_error is None:
            result = self.fetch_elsevier_xml(doi)
            if result.success:
                if with_figures and result.pii and result.figures:
                    self.download_figures(result.pii, result.figures)
                return result
            elsevier_error = result.error

        return FullTextResult(doi=doi, success=False, error=elsevier_error or "no route succeeded")

    def probe(self, doi: str) -> List[Tuple[str, str]]:
        """Diagnose which routes work for one DOI, without saving anything.

        Useful when a whole batch fails and you need to know whether it is the
        key, the network, or the specific title.
        """
        findings: List[Tuple[str, str]] = []
        if self.api_key:
            for accept, name in (("text/xml", "elsevier-xml"), ("application/pdf", "elsevier-pdf")):
                try:
                    resp = self._els_get(f"{self.ELSEVIER_ARTICLE}/doi/{doi}", accept=accept)
                    status = resp.headers.get("X-ELS-Status", "")
                    verdict = "OK" if (resp.status_code == 200 and self._is_entitled(status)) else "BLOCKED"
                    findings.append((name, f"HTTP {resp.status_code} | {status or '-'} | {verdict}"))
                except requests.RequestException as exc:
                    findings.append((name, f"ERROR {type(exc).__name__}"))
        else:
            findings.append(("elsevier", "skipped: SCOPUS_API_KEY not set"))
        try:
            resp = self.session.get(f"{self.SPRINGER_PDF_BASE}/{doi}.pdf",
                                    timeout=self.timeout, stream=True)
            ok = resp.status_code == 200 and resp.raw.read(4) == b"%PDF"
            findings.append(("springer-pdf", f"HTTP {resp.status_code} | {'OK' if ok else 'BLOCKED'}"))
        except requests.RequestException as exc:
            findings.append(("springer-pdf", f"ERROR {type(exc).__name__}"))
        return findings
