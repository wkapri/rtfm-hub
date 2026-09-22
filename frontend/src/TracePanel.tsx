import { useState } from "react";
import type { TraceStep } from "./types";

interface Props {
  steps: TraceStep[];
}

// Admin-facing "what happened" panel — shows each backend step (search
// backend used, what it found, verification, ingestion) with its timing.
// Collapsed by default so it stays out of the way for the common case.
export default function TracePanel({ steps }: Props) {
  const [open, setOpen] = useState(false);
  if (steps.length === 0) return null;

  const totalMs = steps.reduce((sum, s) => sum + s.duration_ms, 0);

  return (
    <div className="trace-panel">
      <button type="button" className="trace-panel-toggle" onClick={() => setOpen((o) => !o)}>
        {open ? "▾" : "▸"} What happened ({steps.length} step{steps.length === 1 ? "" : "s"}, {totalMs}ms)
      </button>
      {open && (
        <ul className="trace-panel-list">
          {steps.map((s, i) => (
            <li key={i} className="trace-panel-item">
              <span className="trace-panel-name">{s.name}</span>
              <span className="trace-panel-duration">{s.duration_ms}ms</span>
              {s.detail && <span className="trace-panel-detail">{s.detail}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
