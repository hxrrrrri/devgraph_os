import type { ReviewResult } from "@devgraph/schema";
import { AlertTriangle, GitCompare, ListChecks } from "lucide-react";

export function ReviewLens({ review, onLoadReview }: { review: ReviewResult | null; onLoadReview: () => void }) {
  const firstSnippet = review ? Object.entries(review.changed_snippets)[0] : undefined;
  return (
    <section className="lens">
      <div className="lens-header">
        <h2>Review Lens</h2>
        <button className="primary" onClick={onLoadReview}>Review changes</button>
      </div>
      {review ? (
        <div className="review-grid">
          <section className="panel">
            <h3><AlertTriangle size={16} /> Risk</h3>
            <strong className={`risk ${review.risk_level}`}>{review.risk_score}/100 {review.risk_level}</strong>
            {review.risk_explanation.map((item) => <p key={item}>{item}</p>)}
            {review.warnings.map((item) => <p className="warning" key={item}>{item}</p>)}
          </section>
          <section className="panel">
            <h3>Changed files</h3>
            {review.changed_files.map((file) => <p key={file}>{file}</p>)}
          </section>
          <section className="panel">
            <h3><GitCompare size={16} /> Diff summary</h3>
            {review.diff_summary.map((item) => <p key={item}>{item}</p>)}
          </section>
          <section className="panel">
            <h3><ListChecks size={16} /> Checklist</h3>
            {review.review_checklist.map((item) => <label key={item}><input type="checkbox" /> {item}</label>)}
          </section>
          <section className="panel">
            <h3>Impacted files</h3>
            {review.impacted_files.length ? review.impacted_files.map((file) => <p key={file}>{file}</p>) : <p>No impacted files detected.</p>}
          </section>
          <section className="panel">
            <h3>Affected tests</h3>
            {review.affected_tests.length ? review.affected_tests.map((file) => <p key={file}>{file}</p>) : <p>No related tests found.</p>}
          </section>
          {firstSnippet ? (
            <section className="panel wide-panel">
              <h3>{firstSnippet[0]}</h3>
              <pre className="snippet">{firstSnippet[1]}</pre>
            </section>
          ) : null}
        </div>
      ) : (
        <p>No review loaded.</p>
      )}
    </section>
  );
}
