import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from ragapp.ingestion.service import IngestionError, ingest_pdf
from ragapp.retrieval.store import VectorStore

from hubapp.db import init_schema
from hubapp.products.store import ProductStore

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

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / (file.filename or "manual.pdf")
        tmp_path.write_bytes(await file.read())
        try:
            document_id, _chunk_count = ingest_pdf(tmp_path, title=file.filename)
        except IngestionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return products.link_document(product_id, document_id, document_kind)


@app.get("/api/products/{product_id}/maintenance", response_model=list[MaintenanceOut])
def list_maintenance(product_id: str):
    return products.list_maintenance(product_id)


@app.post("/api/products/{product_id}/maintenance", response_model=MaintenanceOut)
def add_maintenance(product_id: str, request: MaintenanceCreate):
    if products.get(product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return products.add_maintenance(product_id, request.date, request.description, request.cost)
