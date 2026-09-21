import { useState } from "react";
import { api } from "./api";
import { CloseIcon } from "./Icons";
import type { MaintenanceEntry } from "./types";

interface Props {
  productId: string;
  onClose: () => void;
  onSaved: (entry: MaintenanceEntry) => void;
}

export default function MaintenanceForm({ productId, onClose, onSaved }: Props) {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");
  const [cost, setCost] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) {
      setError("Description is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const entry = await api.addMaintenance(productId, {
        date,
        description,
        cost: cost ? Number(cost) : null,
      });
      onSaved(entry);
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
          <h2>Add maintenance entry</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </button>
        </div>

        <form className="form" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-field">
              <label htmlFor="m-date">Date</label>
              <input id="m-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="form-field">
              <label htmlFor="m-cost">Cost</label>
              <input
                id="m-cost"
                type="number"
                step="0.01"
                value={cost}
                onChange={(e) => setCost(e.target.value)}
                placeholder="15.99"
              />
            </div>
          </div>

          <div className="form-field">
            <label htmlFor="m-desc">Description</label>
            <input
              id="m-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Replaced filter"
              autoFocus
            />
          </div>

          {error && <p className="form-error">{error}</p>}

          <div className="button-row">
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button primary" disabled={saving}>
              {saving ? "Saving…" : "Add entry"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
