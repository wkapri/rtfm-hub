import { useEffect, useState } from "react";
import { api } from "./api";
import { categoryIcon } from "./categoryIcon";
import DiscoverModal from "./DiscoverModal";
import { BackIcon, EditIcon, LinkIcon, SearchIcon, TrashIcon, WrenchIcon } from "./Icons";
import LinkDocumentModal from "./LinkDocumentModal";
import MaintenanceForm from "./MaintenanceForm";
import ProductForm from "./ProductForm";
import type { MaintenanceEntry, Product, ProductDocument } from "./types";

interface Props {
  product: Product;
  onBack: () => void;
  onUpdated: (product: Product) => void;
  onDeleted: (productId: string) => void;
}

const KIND_LABELS: Record<string, string> = {
  owners_manual: "Owner's manual",
  quick_start: "Quick start guide",
  service_manual: "Service manual",
};

export default function ProductDetail({ product, onBack, onUpdated, onDeleted }: Props) {
  const [documents, setDocuments] = useState<ProductDocument[] | null>(null);
  const [maintenance, setMaintenance] = useState<MaintenanceEntry[] | null>(null);
  const [editing, setEditing] = useState(false);
  const [linkingDocument, setLinkingDocument] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [addingMaintenance, setAddingMaintenance] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.listProductDocuments(product.id).then(setDocuments).catch(() => setDocuments([]));
    api.listMaintenance(product.id).then(setMaintenance).catch(() => setMaintenance([]));
  }, [product.id]);

  async function handleDelete() {
    if (!confirm(`Delete "${product.nickname}"? This can't be undone.`)) return;
    setDeleting(true);
    try {
      await api.deleteProduct(product.id);
      onDeleted(product.id);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="content">
      <button className="icon-button" onClick={onBack} aria-label="Back" style={{ marginBottom: 16 }}>
        <BackIcon />
      </button>

      <div className="detail-header">
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <span className="product-icon large" aria-hidden="true">
            {categoryIcon(product.category)}
          </span>
          <div>
            <h1 className="detail-title">{product.nickname}</h1>
            {(product.brand || product.model) && (
              <p className="detail-subtitle">
                {[product.brand, product.model].filter(Boolean).join(" ")}
                {product.year ? ` · ${product.year}` : ""}
              </p>
            )}
          </div>
        </div>
        <div className="button-row">
          <button className="icon-button" onClick={() => setEditing(true)} aria-label="Edit">
            <EditIcon />
          </button>
          <button className="icon-button" onClick={handleDelete} disabled={deleting} aria-label="Delete">
            <TrashIcon />
          </button>
        </div>
      </div>

      <div className="detail-fields">
        {product.category && (
          <div>
            <p className="detail-field-label">Category</p>
            <p className="detail-field-value">{product.category}</p>
          </div>
        )}
        {product.purchase_date && (
          <div>
            <p className="detail-field-label">Purchased</p>
            <p className="detail-field-value">{product.purchase_date}</p>
          </div>
        )}
        {product.warranty_expires && (
          <div>
            <p className="detail-field-label">Warranty expires</p>
            <p className="detail-field-value">{product.warranty_expires}</p>
          </div>
        )}
      </div>

      {product.notes && (
        <div className="section">
          <p className="section-title">Notes</p>
          <p style={{ fontSize: 14, margin: 0 }}>{product.notes}</p>
        </div>
      )}

      <div className="section">
        <div className="section-header">
          <p className="section-title">Manuals</p>
          <div className="button-row">
            <button className="button" onClick={() => setDiscovering(true)}>
              <SearchIcon size={13} /> Discover
            </button>
            <button className="button" onClick={() => setLinkingDocument(true)}>
              <LinkIcon size={13} /> Add
            </button>
          </div>
        </div>
        {documents === null ? (
          <p className="loading-text">Loading…</p>
        ) : documents.length === 0 ? (
          <p className="empty-hint">No manuals linked yet.</p>
        ) : (
          <div className="item-list">
            {documents.map((d) => (
              <div className="item-row" key={d.id}>
                <div className="item-row-main">
                  <p className="item-row-title">{KIND_LABELS[d.document_kind] ?? d.document_kind}</p>
                  <p className="item-row-meta">Added {new Date(d.added_at).toLocaleDateString()}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="section">
        <div className="section-header">
          <p className="section-title">Maintenance log</p>
          <button className="button" onClick={() => setAddingMaintenance(true)}>
            <WrenchIcon size={13} /> Add
          </button>
        </div>
        {maintenance === null ? (
          <p className="loading-text">Loading…</p>
        ) : maintenance.length === 0 ? (
          <p className="empty-hint">No maintenance entries yet.</p>
        ) : (
          <div className="item-list">
            {maintenance.map((m) => (
              <div className="item-row" key={m.id}>
                <div className="item-row-main">
                  <p className="item-row-title">{m.description}</p>
                  <p className="item-row-meta">{m.date}</p>
                </div>
                {m.cost && <span className="badge">${m.cost}</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {editing && (
        <ProductForm
          product={product}
          onClose={() => setEditing(false)}
          onSaved={(updated) => {
            setEditing(false);
            onUpdated(updated);
          }}
        />
      )}

      {linkingDocument && (
        <LinkDocumentModal
          productId={product.id}
          alreadyLinkedDocumentIds={new Set((documents ?? []).map((d) => d.document_id))}
          onClose={() => setLinkingDocument(false)}
          onLinked={(link) => {
            setLinkingDocument(false);
            setDocuments((prev) => [...(prev ?? []), link]);
          }}
        />
      )}

      {discovering && (
        <DiscoverModal
          productId={product.id}
          onClose={() => setDiscovering(false)}
          onLinked={(link) => {
            setDiscovering(false);
            setDocuments((prev) => [...(prev ?? []), link]);
          }}
        />
      )}

      {addingMaintenance && (
        <MaintenanceForm
          productId={product.id}
          onClose={() => setAddingMaintenance(false)}
          onSaved={(entry) => {
            setAddingMaintenance(false);
            setMaintenance((prev) => [entry, ...(prev ?? [])]);
          }}
        />
      )}
    </div>
  );
}
