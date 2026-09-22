from pathlib import Path

from hubapp.config import settings


def save_manual(document_id: str, content: bytes) -> Path:
    """Keep a retained copy of an ingested manual's original PDF bytes, keyed by
    its document_id. Ingestion (ragapp.ingestion.service.ingest_pdf) only stores
    extracted text/chunks/embeddings — the source file itself is otherwise lost
    once the temp directory it was downloaded/uploaded into is cleaned up, which
    means there was no way to view or re-download a manual after linking it.
    """
    directory = Path(settings.manuals_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{document_id}.pdf"
    path.write_bytes(content)
    return path


def manual_path(document_id: str) -> Path | None:
    """The retained copy's path, or None if this document predates manual
    retention (ingested before this feature existed) or was never saved."""
    path = Path(settings.manuals_dir) / f"{document_id}.pdf"
    return path if path.is_file() else None
