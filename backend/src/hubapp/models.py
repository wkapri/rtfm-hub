from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class Product:
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


@dataclass
class ProductDocument:
    id: str
    product_id: str
    document_id: str
    document_kind: str
    source_url: str | None
    added_at: datetime


@dataclass
class MaintenanceEntry:
    id: str
    product_id: str
    date: date
    description: str
    cost: Decimal | None
    created_at: datetime
