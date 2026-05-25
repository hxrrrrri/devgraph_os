import type { ReviewResult } from "@devgraph/schema";

export function ReviewLens({ review, onLoadReview }: { review: ReviewResult | null; onLoadReview: () => void }) {
  return (
    <section className="lens">
      <div className="lens-header">
        <h2>Review Lens</h2>
        <button className="primary" onClick={onLoadReview}>Review changes</button>
      </div>
      {review ? (
        <div className="review-grid">
          <section className="panel">
            <h3>Risk</h3>
            <strong className={`risk ${review.risk_level}`}>{review.risk_score}/100 {review.risk_level}</strong>
            {review.risk_explanation.map((item) => <p key={item}>{item}</p>)}
          </section>
          <section className="panel">
            <h3>Changed files</h3>
            {review.changed_files.map((file) => <p key={file}>{file}</p>)}
          </section>
          <section className="panel">
            <h3>Impacted files</h3>
            {review.impacted_files.map((file) => <p key={file}>{file}</p>)}
          </section>
          <section className="panel">
            <h3>Checklist</h3>
            {review.review_checklist.map((item) => <label key={item}><input type="checkbox" /> {item}</label>)}
          </section>
        </div>
      ) : (
        <p>No review loaded.</p>
      )}
    </section>
  );
}

