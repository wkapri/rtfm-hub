import { useEffect, useState } from "react";
import { api } from "./api";
import { CloseIcon } from "./Icons";
import type { Document, ProductDocument } from "./types";

interface Props {
  productId: string;
  alreadyLinkedDocumentIds: Set<string>;
  onClose: () => void;
  onLinked: (link: ProductDocument) => void;
}

const KIND_OPTIONS = [
  { value: "owners_manual", label: "Owner's manual" },
  { value: "quick_start", label: "Quick start guide" },
  { value: "service_manual", label: "Service manual" },
];

export default function LinkDocumentModal({ productId, alreadyLinkedDocumentIds, onClose, onLinked }: Props) {
  const [mode, setMode] = useState<"upload" | "existing">("upload");
  const [kind, setKind] = useState("owners_manual");
  const [file, setFile] = useState<File | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode === "existing") {
      api.listDocuments().then(setDocuments).catch(() => setDocuments([]));
    }
  }, [mode]);

  const availableDocuments = documents.filter((d) => !alreadyLinkedDocumentIds.has(d.id));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (mode === "upload") {
        if (!file) {
          setError("Choose a PDF to upload.");
          setSaving(false);
          return;
        }
        const link = await api.uploadDocument(productId, file, kind);
        onLinked(link);
      } else {
        if (!selectedDocId) {
          setError("Pick a document to link.");
          setSaving(false);
          return;
        }
        const link = await api.linkDocument(productId, selectedDocId, kind);
        onLinked(link);
      }
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
          <h2>Add a manual</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </button>
        </div>

        <div className="button-row" style={{ marginBottom: 14 }}>
          <button
            type="button"
            className={`button ${mode === "upload" ? "primary" : ""}`}
            onClick={() => setMode("upload")}
          >
            Upload PDF
          </button>
          <button
            type="button"
            className={`button ${mode === "existing" ? "primary" : ""}`}
            onClick={() => setMode("existing")}
          >
            Link existing
          </button>
        </div>

        <form className="form" onSubmit={handleSubmit}>
          {mode === "upload" ? (
            <div className="form-field">
              <label htmlFor="file">PDF file</label>
              <input
                id="file"
                type="file"
                accept="application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
          ) : (
            <div className="form-field">
              <label htmlFor="existing-doc">Already-ingested document</label>
              {availableDocuments.length === 0 ? (
                <p className="empty-hint">
                  No other ingested documents available — upload a new PDF instead.
                </p>
              ) : (
                <select
                  id="existing-doc"
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                >
                  <option value="">Select a document…</option>
                  {availableDocuments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          <div className="form-field">
            <label htmlFor="kind">Document type</label>
            <select id="kind" value={kind} onChange={(e) => setKind(e.target.value)}>
              {KIND_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {error && <p className="form-error">{error}</p>}

          <div className="button-row">
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button primary" disabled={saving}>
              {saving ? (mode === "upload" ? "Ingesting…" : "Linking…") : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
