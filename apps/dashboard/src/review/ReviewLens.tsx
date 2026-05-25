import type { ReviewResult } from "@devgraph/schema";
import { AlertTriangle, Clipboard, GitCompare, ListChecks, ShieldAlert } from "lucide-react";

export function ReviewLens({ review, onLoadReview }: { review: ReviewResult | null; onLoadReview: () => void }) {
  const firstSnippet = review ? Object.entries(review.changed_snippets)[0] : undefined;
  const riskOffset = review ? Math.max(0, 283 - (review.risk_score / 100) * 283) : 283;
  return (
    <section className="lens">
      <div className="lens-header">
        <div>
          <h2>Review Lens</h2>
          <p>Changed symbols, blast radius, risk reasons, tests, and diff hunks.</p>
        </div>
        <button className="primary" onClick={onLoadReview}>Review changes</button>
      </div>
      {review ? (
        <div className="review-grid">
          <section className="glass-card risk-board">
            <h3><AlertTriangle size={16} /> Risk</h3>
            <svg viewBox="0 0 120 120" role="img" aria-label={`Risk ${review.risk_score}`}>
              <circle cx="60" cy="60" r="45" />
              <circle cx="60" cy="60" r="45" className={review.risk_level} strokeDashoffset={riskOffset} />
              <text x="60" y="64">{review.risk_score}</text>
            </svg>
            <strong className={`risk ${review.risk_level}`}>{review.risk_level}</strong>
            {review.risk_explanation.map((item) => <p key={item}>{item}</p>)}
          </section>
          <section className="glass-card">
            <h3>Changed symbols</h3>
            <div className="dense-list">
              {review.changed_symbols.length ? review.changed_symbols.slice(0, 12).map((node) => (
                <span key={node.id}><b>{node.type}</b>{node.qualified_name}</span>
              )) : <em>No symbols mapped from diff hunks.</em>}
            </div>
          </section>
          <section className="glass-card">
            <h3><ShieldAlert size={16} /> Sensitive areas</h3>
            <div className="dense-list">
              {[...review.security_sensitive_changes, ...review.public_api_changes, ...review.database_or_schema_changes, ...review.config_or_infra_changes].slice(0, 12).map((item) => <span key={item}>{item}</span>)}
              {!review.security_sensitive_changes.length && !review.public_api_changes.length && !review.database_or_schema_changes.length && !review.config_or_infra_changes.length ? <em>No sensitive areas detected.</em> : null}
            </div>
          </section>
          <section className="glass-card">
            <h3><ListChecks size={16} /> Prioritized items</h3>
            {review.prioritized_review_items.map((item) => <p key={item}>{item}</p>)}
          </section>
          <section className="glass-card">
            <h3>Impacted files</h3>
            <div className="dense-list">
              {review.impacted_files.length ? review.impacted_files.slice(0, 14).map((file) => <span key={file}>{file}</span>) : <em>No impacted files detected.</em>}
            </div>
          </section>
          <section className="glass-card">
            <h3>Affected tests</h3>
            <div className="dense-list">
              {review.affected_tests.length ? review.affected_tests.map((file) => <span key={file}>{file}</span>) : <em>No related tests found.</em>}
              {review.missing_tests.map((item) => <span className="attention" key={item}>{item}</span>)}
            </div>
          </section>
          <section className="glass-card">
            <h3><GitCompare size={16} /> Diff hunks</h3>
            <div className="dense-list">
              {review.changed_hunks.length ? review.changed_hunks.slice(0, 8).map((hunk, index) => (
                <span key={`${hunk.file_path}-${index}`}><b>{String(hunk.file_path)}</b>lines {String(hunk.new_start)}-{Number(hunk.new_start ?? 0) + Number(hunk.new_count ?? 0)}</span>
              )) : <em>No hunks available.</em>}
            </div>
          </section>
          <section className="glass-card">
            <h3><Clipboard size={16} /> Checklist</h3>
            {review.review_checklist.map((item) => <label key={item}><input type="checkbox" /> {item}</label>)}
            <button className="ghost" onClick={() => navigator.clipboard?.writeText(review.context_pack)}>Copy context pack</button>
          </section>
          {firstSnippet ? (
            <section className="glass-card wide-panel">
              <h3>{firstSnippet[0]}</h3>
              <pre className="snippet">{firstSnippet[1]}</pre>
            </section>
          ) : null}
        </div>
      ) : (
        <section className="glass-card empty-state">No review loaded.</section>
      )}
    </section>
  );
}
