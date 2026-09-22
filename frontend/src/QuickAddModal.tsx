import { useState } from "react";
import { api } from "./api";
import { CloseIcon, SearchIcon } from "./Icons";
import TracePanel from "./TracePanel";
import type { Identification, Product, ProductInput } from "./types";

interface Props {
  onClose: () => void;
  onSaved: (product: Product) => void;
}

const CONFIDENCE_LABEL: Record<string, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence — double-check this",
};

export default function QuickAddModal({ onClose, onSaved }: Props) {
  const [description, setDescription] = useState("");
  const [identifying, setIdentifying] = useState(false);
  const [identifyError, setIdentifyError] = useState<string | null>(null);
  const [identification, setIdentification] = useState<Identification | null>(null);

  const [nickname, setNickname] = useState("");
  const [brand, setBrand] = useState("");
  const [model, setModel] = useState("");
  const [category, setCategory] = useState("");
  const [year, setYear] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function handleIdentify(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) return;
    setIdentifying(true);
    setIdentifyError(null);
    try {
      const result = await api.identifyProduct(description);
      setIdentification(result);
      setBrand(result.brand ?? "");
      setModel(result.model ?? "");
      setCategory(result.category ?? "");
      setYear(result.year ? String(result.year) : "");
      setNickname([result.brand, result.model].filter(Boolean).join(" ") || description);
    } catch (err) {
      setIdentifyError(err instanceof Error ? err.message : "Couldn't identify that.");
      // Fall through to manual entry even on failure — description becomes the
      // nickname, everything else stays blank and editable.
      setNickname(description);
      setIdentification(null);
    } finally {
      setIdentifying(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!nickname.trim()) {
      setSaveError("Nickname is required.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    const input: ProductInput = {
      nickname,
      brand: brand || null,
      model: model || null,
      category: category || null,
      year: year ? Number(year) : null,
      purchase_date: null,
      warranty_expires: null,
      notes: null,
    };
    try {
      const created = await api.createProduct(input);
      onSaved(created);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSaving(false);
    }
  }

  const showConfirmStep = identification !== null || identifyError !== null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add product</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </button>
        </div>

        {!showConfirmStep ? (
          <form className="form" onSubmit={handleIdentify}>
            <div className="form-field">
              <label htmlFor="description">What did you get?</label>
              <input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. roomba, or 2013 Subaru XV"
                autoFocus
              />
            </div>
            <div className="button-row">
              <button type="button" className="button" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="button primary" disabled={identifying || !description.trim()}>
                {identifying ? (
                  "Identifying…"
                ) : (
                  <>
                    <SearchIcon size={13} /> Identify
                  </>
                )}
              </button>
            </div>
          </form>
        ) : (
          <form className="form" onSubmit={handleSave}>
            {identification && (
              <div className="badge-row" style={{ marginBottom: -4 }}>
                <span
                  className={`badge ${identification.confidence === "low" ? "warning" : ""}`}
                >
                  {CONFIDENCE_LABEL[identification.confidence]}
                </span>
              </div>
            )}
            {identification?.reasoning && (
              <p className="empty-hint" style={{ margin: 0 }}>
                {identification.reasoning}
              </p>
            )}
            {identifyError && (
              <p className="form-error">
                Couldn't auto-identify this ({identifyError}) — fill in what you know below.
              </p>
            )}
            {identification && <TracePanel steps={identification.trace} />}

            <div className="form-field">
              <label htmlFor="nickname">Nickname *</label>
              <input
                id="nickname"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                autoFocus
              />
            </div>

            <div className="form-row">
              <div className="form-field">
                <label htmlFor="brand">Brand</label>
                <input id="brand" value={brand} onChange={(e) => setBrand(e.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="model">Model</label>
                <input id="model" value={model} onChange={(e) => setModel(e.target.value)} />
              </div>
            </div>

            <div className="form-row">
              <div className="form-field">
                <label htmlFor="category">Category</label>
                <input id="category" value={category} onChange={(e) => setCategory(e.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="year">Year</label>
                <input
                  id="year"
                  type="number"
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                />
              </div>
            </div>

            {saveError && <p className="form-error">{saveError}</p>}

            <div className="button-row">
              <button
                type="button"
                className="button"
                onClick={() => {
                  setIdentification(null);
                  setIdentifyError(null);
                }}
              >
                Back
              </button>
              <button type="submit" className="button primary" disabled={saving}>
                {saving ? "Saving…" : "Save & find manual"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
