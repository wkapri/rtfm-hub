import { useEffect, useState } from "react";
import { api } from "./api";
import { CheckIcon, CloseIcon } from "./Icons";
import TracePanel from "./TracePanel";
import type { Candidate, ProductDocument, TraceStep } from "./types";

interface Props {
  productId: string;
  onClose: () => void;
  onLinked: (link: ProductDocument) => void;
}

export default function DiscoverModal({ productId, onClose, onLinked }: Props) {
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [searchTrace, setSearchTrace] = useState<TraceStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [approvingUrl, setApprovingUrl] = useState<string | null>(null);
  const [approveError, setApproveError] = useState<string | null>(null);

  useEffect(() => {
    api
      .discoverManual(productId)
      .then((result) => {
        setCandidates(result.candidates);
        setSearchTrace(result.trace);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Search failed."));
  }, [productId]);

  async function handleApprove(candidate: Candidate) {
    setApprovingUrl(candidate.url);
    setApproveError(null);
    try {
      const result = await api.approveCandidate(productId, candidate, "owners_manual");
      onLinked(result.document);
    } catch (err) {
      setApproveError(err instanceof Error ? err.message : "Couldn't ingest that one.");
    } finally {
      setApprovingUrl(null);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Find a manual</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </button>
        </div>

        {error && <p className="form-error">{error}</p>}

        {candidates === null && !error && <p className="loading-text">Searching…</p>}

        {candidates !== null && <TracePanel steps={searchTrace} />}

        {candidates !== null && candidates.length === 0 && (
          <p className="empty-hint">
            No plausible candidates found. Try "Upload PDF" or "Link existing" instead, or
            check back later.
          </p>
        )}

        {candidates !== null && candidates.length > 0 && (
          <div className="item-list">
            {candidates.map((c) => (
              <div className="item-row" key={c.url} style={{ alignItems: "flex-start" }}>
                <div className="item-row-main">
                  <p className="item-row-title" style={{ whiteSpace: "normal" }}>
                    {c.title}
                  </p>
                  <p className="item-row-meta">{c.domain}</p>
                  <div className="badge-row">
                    {c.match_reasons.map((reason) => (
                      <span className="badge" key={reason}>
                        {reason}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  className="button primary"
                  onClick={() => handleApprove(c)}
                  disabled={approvingUrl !== null}
                >
                  {approvingUrl === c.url ? (
                    "Ingesting…"
                  ) : (
                    <>
                      <CheckIcon size={13} /> Use this
                    </>
                  )}
                </button>
              </div>
            ))}
          </div>
        )}

        {approveError && <p className="form-error">{approveError}</p>}
      </div>
    </div>
  );
}
