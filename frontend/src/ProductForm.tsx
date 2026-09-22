import { useState } from "react";
import { api } from "./api";
import { CloseIcon } from "./Icons";
import type { Product, ProductInput } from "./types";

interface Props {
  product: Product | null; // null = creating a new product
  onClose: () => void;
  onSaved: (product: Product) => void;
}

const emptyInput: ProductInput = {
  nickname: "",
  brand: null,
  model: null,
  category: null,
  year: null,
  purchase_date: null,
  warranty_expires: null,
  notes: null,
};

export default function ProductForm({ product, onClose, onSaved }: Props) {
  const [values, setValues] = useState<ProductInput>(
    product
      ? {
          nickname: product.nickname,
          brand: product.brand,
          model: product.model,
          category: product.category,
          year: product.year,
          purchase_date: product.purchase_date,
          warranty_expires: product.warranty_expires,
          notes: product.notes,
        }
      : emptyInput,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof ProductInput>(key: K, value: ProductInput[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!values.nickname.trim()) {
      setError("Nickname is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const saved = product
        ? await api.updateProduct(product.id, values)
        : await api.createProduct(values);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{product ? "Edit product" : "Add product"}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </button>
        </div>

        <form className="form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="nickname">Nickname *</label>
            <input
              id="nickname"
              value={values.nickname}
              onChange={(e) => set("nickname", e.target.value)}
              placeholder="e.g. Kitchen vacuum"
              autoFocus
            />
          </div>

          <div className="form-row">
            <div className="form-field">
              <label htmlFor="brand">Brand</label>
              <input
                id="brand"
                value={values.brand ?? ""}
                onChange={(e) => set("brand", e.target.value || null)}
                placeholder="Roborock"
              />
            </div>
            <div className="form-field">
              <label htmlFor="model">Model</label>
              <input
                id="model"
                value={values.model ?? ""}
                onChange={(e) => set("model", e.target.value || null)}
                placeholder="S7"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label htmlFor="category">Category</label>
              <input
                id="category"
                value={values.category ?? ""}
                onChange={(e) => set("category", e.target.value || null)}
                placeholder="vacuum"
              />
            </div>
            <div className="form-field">
              <label htmlFor="year">Year</label>
              <input
                id="year"
                type="number"
                value={values.year ?? ""}
                onChange={(e) => set("year", e.target.value ? Number(e.target.value) : null)}
                placeholder="2022"
              />
            </div>
          </div>

          {/* purchase_date / warranty_expires hidden for now — not removed from
              the data model, just not editable via this form yet. */}

          <div className="form-field">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              value={values.notes ?? ""}
              onChange={(e) => set("notes", e.target.value || null)}
              placeholder="Anything worth remembering about this item"
            />
          </div>

          {error && <p className="form-error">{error}</p>}

          <div className="button-row">
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button primary" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
