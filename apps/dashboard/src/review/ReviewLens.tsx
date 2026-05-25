import type { ReviewResult } from "@devgraph/schema";
import { AlertTriangle, Clipboard, Flame, GitCompare, ListChecks, ShieldAlert } from "lucide-react";

const severityClass: Record<string, string> = {
  high: "sev-high",
  medium: "sev-med",
  low: "sev-low"
};

export function ReviewLens({ review, onLoadReview }: { review: ReviewResult | null; onLoadReview: () => void }) {
  const firstSnippet = review ? Object.entries(review.changed_snippets)[0] : undefined;
  const riskOffset = review ? Math.max(0, 283 - (review.risk_score / 100) * 283) : 283;
  const severityEntries = review
    ? Object.entries(review.severity_by_file).sort((a, b) => severityRank(b[1]) - severityRank(a[1]))
    : [];
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
          <section className="glass-card wide-panel">
            <h3><Flame size={16} /> Severity heat map</h3>
            {severityEntries.length ? (
              <div className="severity-grid">
                {severityEntries.slice(0, 24).map(([file, sev]) => (
                  <span key={file} className={`severity-cell ${severityClass[sev] ?? ""}`} title={`${file}: ${sev}`}>
                    <b>{sev}</b>
                    <code>{file}</code>
                  </span>
                ))}
              </div>
            ) : <em>No severity signals (no migrations/API drift/fan-out hotspots).</em>}
            {review.api_signature_changes.length ? (
              <div className="dense-list" style={{ marginTop: 12 }}>
                <em>API compat warnings:</em>
                {review.api_signature_changes.slice(0, 8).map((w, idx) => (
                  <span key={`api-${idx}`}><b>{String(w.code)}</b>{String(w.qualified_name ?? "")}</span>
                ))}
              </div>
            ) : null}
            {review.route_contract_changes.length ? (
              <div className="dense-list" style={{ marginTop: 8 }}>
                <em>Route contract changes:</em>
                {review.route_contract_changes.slice(0, 8).map((w, idx) => (
                  <span key={`route-${idx}`}><b>{String(w.code)}</b>{String(w.method ?? "")} {String(w.path ?? "")}</span>
                ))}
              </div>
            ) : null}
            {review.fan_out.length ? (
              <div className="dense-list" style={{ marginTop: 8 }}>
                <em>Top fan-out symbols:</em>
                {review.fan_out.slice(0, 8).map((entry, idx) => (
                  <span key={`fan-${idx}`}><b>{String(entry.fan_in ?? 0)}→{String(entry.fan_out ?? 0)}</b>{String(entry.qualified_name ?? "")}</span>
                ))}
              </div>
            ) : null}
            {review.infra_blast_radius.length ? (
              <div className="dense-list" style={{ marginTop: 8 }}>
                <em>Infra blast radius:</em>
                {review.infra_blast_radius.slice(0, 8).map((entry, idx) => (
                  <span key={`infra-${idx}`}><b>{String(entry.category ?? "")}</b>{String(entry.file_path ?? "")}</span>
                ))}
              </div>
            ) : null}
          </section>
          {firstSnippet ? (
            <section className="glass-card wide-panel">
              <h3>{firstSnippet[0]}</h3>
              <pre className="snippet">{firstSnippet[1]}</pre>
            </section>
          ) : null}
        </div>
      ) : (
        <ReviewSkeleton />
      )}
    </section>
  );
}

function severityRank(severity: string): number {
  if (severity === "high") return 3;
  if (severity === "medium") return 2;
  if (severity === "low") return 1;
  return 0;
}

function ReviewSkeleton() {
  return (
    <div className="review-grid review-skeleton">
      {Array.from({ length: 6 }).map((_, idx) => (
        <section key={idx} className="glass-card skeleton-card">
          <div className="skeleton-line lg" />
          <div className="skeleton-line" />
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
        </section>
      ))}
    </div>
  );
}
