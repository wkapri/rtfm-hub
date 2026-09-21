-- Requires ragapp's schema (documents, chunks, query_logs) to already exist in this
-- database, since product_documents.document_id is a real FK into documents.id.
-- hubapp.db.init_schema() enforces that ordering — don't run this file standalone.

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nickname TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    category TEXT,
    year INT,
    purchase_date DATE,
    warranty_expires DATE,
    notes TEXT,
    -- HA add-on mode only: the HA device registry ID this product was imported
    -- from/linked to. NULL for anything added standalone or manually.
    ha_device_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS product_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_kind TEXT NOT NULL DEFAULT 'owners_manual',
    source_url TEXT,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS product_documents_product_id_idx ON product_documents (product_id);
CREATE INDEX IF NOT EXISTS product_documents_document_id_idx ON product_documents (document_id);

CREATE TABLE IF NOT EXISTS maintenance_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    cost NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS maintenance_log_product_id_idx ON maintenance_log (product_id);
