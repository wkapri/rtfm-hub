from typing import Any

from hubapp.db import get_connection
from hubapp.models import MaintenanceEntry, Product, ProductDocument

_PRODUCT_COLUMNS = [
    "id", "nickname", "brand", "model", "category", "year",
    "purchase_date", "warranty_expires", "notes", "ha_device_id", "created_at",
]


def _row_to_product(row: tuple) -> Product:
    return Product(**dict(zip(_PRODUCT_COLUMNS, (str(row[0]), *row[1:]), strict=True)))


class ProductStore:
    def create(
        self,
        nickname: str,
        brand: str | None = None,
        model: str | None = None,
        category: str | None = None,
        year: int | None = None,
        purchase_date: str | None = None,
        warranty_expires: str | None = None,
        notes: str | None = None,
    ) -> Product:
        with get_connection() as conn:
            row = conn.execute(
                f"""
                INSERT INTO products (nickname, brand, model, category, year,
                                       purchase_date, warranty_expires, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {", ".join(_PRODUCT_COLUMNS)}
                """,
                (nickname, brand, model, category, year, purchase_date, warranty_expires, notes),
            ).fetchone()
        return _row_to_product(row)

    def list_all(self) -> list[Product]:
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_PRODUCT_COLUMNS)} FROM products ORDER BY created_at"
            ).fetchall()
        return [_row_to_product(r) for r in rows]

    def get(self, product_id: str) -> Product | None:
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT {', '.join(_PRODUCT_COLUMNS)} FROM products WHERE id = %s", (product_id,)
            ).fetchone()
        return _row_to_product(row) if row else None

    def update(self, product_id: str, fields: dict[str, Any]) -> Product | None:
        if not fields:
            return self.get(product_id)
        set_clause = ", ".join(f"{col} = %({col})s" for col in fields)
        with get_connection() as conn:
            row = conn.execute(
                f"""
                UPDATE products SET {set_clause}
                WHERE id = %(id)s
                RETURNING {", ".join(_PRODUCT_COLUMNS)}
                """,
                {**fields, "id": product_id},
            ).fetchone()
        return _row_to_product(row) if row else None

    def delete(self, product_id: str) -> bool:
        with get_connection() as conn:
            result = conn.execute("DELETE FROM products WHERE id = %s", (product_id,))
        return result.rowcount > 0

    def link_document(
        self, product_id: str, document_id: str, document_kind: str = "owners_manual",
        source_url: str | None = None,
    ) -> ProductDocument:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO product_documents (product_id, document_id, document_kind, source_url)
                VALUES (%s, %s, %s, %s)
                RETURNING id, product_id, document_id, document_kind, source_url, added_at
                """,
                (product_id, document_id, document_kind, source_url),
            ).fetchone()
        return ProductDocument(
            id=str(row[0]), product_id=str(row[1]), document_id=str(row[2]),
            document_kind=row[3], source_url=row[4], added_at=row[5],
        )

    def list_documents(self, product_id: str) -> list[ProductDocument]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, product_id, document_id, document_kind, source_url, added_at
                FROM product_documents WHERE product_id = %s ORDER BY added_at
                """,
                (product_id,),
            ).fetchall()
        return [
            ProductDocument(
                id=str(r[0]), product_id=str(r[1]), document_id=str(r[2]),
                document_kind=r[3], source_url=r[4], added_at=r[5],
            )
            for r in rows
        ]

    def add_maintenance(
        self, product_id: str, date: str, description: str, cost: float | None = None
    ) -> MaintenanceEntry:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO maintenance_log (product_id, date, description, cost)
                VALUES (%s, %s, %s, %s)
                RETURNING id, product_id, date, description, cost, created_at
                """,
                (product_id, date, description, cost),
            ).fetchone()
        return MaintenanceEntry(
            id=str(row[0]), product_id=str(row[1]), date=row[2],
            description=row[3], cost=row[4], created_at=row[5],
        )

    def list_maintenance(self, product_id: str) -> list[MaintenanceEntry]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, product_id, date, description, cost, created_at
                FROM maintenance_log WHERE product_id = %s ORDER BY date DESC
                """,
                (product_id,),
            ).fetchall()
        return [
            MaintenanceEntry(
                id=str(r[0]), product_id=str(r[1]), date=r[2],
                description=r[3], cost=r[4], created_at=r[5],
            )
            for r in rows
        ]
