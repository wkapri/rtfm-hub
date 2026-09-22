import logging
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from ragapp.ingestion.service import IngestionError, ingest_pdf
from ragapp.retrieval.store import VectorStore

from hubapp.db import init_schema
from hubapp.discovery.identify import IdentifyError, identify_product
from hubapp.discovery.service import DiscoveryError, ingest_candidate, search_manual
from hubapp.observability import Trace
from hubapp.products.store import ProductStore
from hubapp.storage import manual_path, save_manual

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")

app = FastAPI(title="rtfm-hub")
init_schema()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_origin_regex=r"http://192\.168\.\d{1,3}\.\d{1,3}:5174",
    allow_methods=["*"],
    allow_headers=["*"],
)

products = ProductStore()
documents = VectorStore()


class ProductCreate(BaseModel):
    nickname: str
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    year: int | None = None
    purchase_date: date | None = None
    warranty_expires: date | None = None
    notes: str | None = None


class ProductUpdate(BaseModel):
    nickname: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    year: int | None = None
    purchase_date: date | None = None
    warranty_expires: date | None = None
    notes: str | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nickname: str
    brand: str | None
    model: str | None
    category: str | None
    year: int | None
    purchase_date: date | None
    warranty_expires: date | None
    notes: str | None
    ha_device_id: str | None
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    title: str


class ProductDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    document_id: str
    document_kind: str
    source_url: str | None
    added_at: datetime


class LinkDocumentRequest(BaseModel):
    document_id: str
    document_kind: str = "owners_manual"
    source_url: str | None = None


class MaintenanceCreate(BaseModel):
    date: date
    description: str
    cost: Decimal | None = None


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    date: date
    description: str
    cost: Decimal | None
    created_at: datetime


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    url: str
    domain: str
    source: str
    match_reasons: list[str]


class ApproveCandidateRequest(BaseModel):
    url: str
    title: str
    document_kind: str = "owners_manual"


class IdentifyRequest(BaseModel):
    description: str


class TraceStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    detail: str
    duration_ms: int


class IdentificationOut(BaseModel):
    brand: str | None
    model: str | None
    category: str | None
    year: int | None
    confidence: str
    reasoning: str
    trace: list[TraceStepOut]


class DiscoverResponse(BaseModel):
    candidates: list[CandidateOut]
    trace: list[TraceStepOut]


class ApproveResponse(BaseModel):
    document: ProductDocumentOut
    trace: list[TraceStepOut]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/documents", response_model=list[DocumentOut])
def list_documents():
    return documents.list_documents()


@app.get("/api/products", response_model=list[ProductOut])
def list_products():
    return products.list_all()


@app.post("/api/products", response_model=ProductOut)
def create_product(request: ProductCreate):
    return products.create(**request.model_dump())


@app.post("/api/products/identify", response_model=IdentificationOut)
def identify(request: IdentifyRequest):
    """Search the web for the description, then have the LLM extract brand/model
    from real results. No side effects — doesn't create a product; the frontend
    shows this as a suggestion to confirm/edit before actually saving one.
    """
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="description is required")
    trace = Trace()
    try:
        result = identify_product(request.description, trace=trace)
    except IdentifyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IdentificationOut(
        brand=result.brand,
        model=result.model,
        category=result.category,
        year=result.year,
        confidence=result.confidence,
        reasoning=result.reasoning,
        trace=trace.steps,
    )


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str):
    product = products.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.patch("/api/products/{product_id}", response_model=ProductOut)
def update_product(product_id: str, request: ProductUpdate):
    fields = request.model_dump(exclude_unset=True)
    product = products.update(product_id, fields)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.delete("/api/products/{product_id}")
def delete_product(product_id: str):
    if not products.delete(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return {"status": "ok"}


@app.get("/api/products/{product_id}/documents", response_model=list[ProductDocumentOut])
def list_product_documents(product_id: str):
    return products.list_documents(product_id)


@app.post("/api/products/{product_id}/documents", response_model=ProductDocumentOut)
def link_document(product_id: str, request: LinkDocumentRequest):
    if products.get(product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return products.link_document(
        product_id, request.document_id, request.document_kind, request.source_url
    )


@app.post("/api/products/{product_id}/documents/upload", response_model=ProductDocumentOut)
async def upload_and_link_document(
    product_id: str, file: UploadFile, document_kind: str = "owners_manual"
):
    if products.get(product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")

    content = await file.read()
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / (file.filename or "manual.pdf")
        tmp_path.write_bytes(content)
        try:
            document_id, _chunk_count = ingest_pdf(tmp_path, title=file.filename)
        except IngestionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    save_manual(document_id, content)
    return products.link_document(product_id, document_id, document_kind)


@app.get("/api/documents/{document_id}/file")
def get_document_file(document_id: str):
    """Serve the retained copy of an ingested manual's original PDF — for
    viewing/downloading after linking, and for verifying a discovery candidate
    before approving it. Returns 404 for documents ingested before manual
    retention existed, or if the file was otherwise never saved.
    """
    path = manual_path(document_id)
    if path is None:
        raise HTTPException(status_code=404, detail="No retained file for this document.")
    return FileResponse(path, media_type="application/pdf")


@app.get("/api/products/{product_id}/maintenance", response_model=list[MaintenanceOut])
def list_maintenance(product_id: str):
    return products.list_maintenance(product_id)


@app.post("/api/products/{product_id}/maintenance", response_model=MaintenanceOut)
def add_maintenance(product_id: str, request: MaintenanceCreate):
    if products.get(product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return products.add_maintenance(product_id, request.date, request.description, request.cost)


@app.get("/api/products/{product_id}/discover", response_model=DiscoverResponse)
def discover_manual(product_id: str):
    """Search + rank candidate manuals. No side effects — nothing is downloaded
    until a specific candidate is approved via the endpoint below.
    """
    product = products.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    trace = Trace()
    try:
        candidates = search_manual(product.brand, product.model, product.category, trace=trace)
    except DiscoveryError:
        # The agent loop failing to reach a clean answer (rambled instead of
        # calling its terminal tool, hit the iteration cap) degrades to the
        # same "nothing found" empty state as a genuinely empty search — not
        # an error dialog. The trace (already populated up to the failure)
        # still shows what was tried, so it's not opaque, just empty-handed.
        candidates = []
    return DiscoverResponse(candidates=candidates, trace=trace.steps)


@app.post("/api/products/{product_id}/discover/approve", response_model=ApproveResponse)
def approve_candidate(product_id: str, request: ApproveCandidateRequest):
    """Download, verify, ingest, and link ONE candidate the user has explicitly
    approved. Never called automatically — see the standing rule in
    docs/specs/03-manual-discovery.md.
    """
    if products.get(product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    trace = Trace()
    try:
        document = ingest_candidate(
            request.url, request.title, product_id, request.document_kind, products, trace=trace
        )
    except DiscoveryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApproveResponse(document=document, trace=trace.steps)
