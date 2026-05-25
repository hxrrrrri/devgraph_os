import clsx from "clsx";

export function SkeletonLine({ width = "100%", height = 10 }: { width?: number | string; height?: number }) {
  return <span className="skeleton-line" style={{ width, height }} />;
}

export function SkeletonCard({ lines = 4, className }: { lines?: number; className?: string }) {
  return (
    <section className={clsx("glass-card skeleton-card", className)}>
      <div className="skeleton-line lg" />
      {Array.from({ length: lines }).map((_, idx) => (
        <div key={idx} className={clsx("skeleton-line", idx === lines - 1 && "short")} />
      ))}
    </section>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <section className="glass-card error-state">
      <strong>{message}</strong>
      {onRetry ? <button className="ghost" onClick={onRetry}>Retry</button> : null}
    </section>
  );
}

export function EmptyPanel({ title, hint }: { title: string; hint?: string }) {
  return (
    <section className="glass-card empty-state-panel">
      <h3>{title}</h3>
      {hint ? <p>{hint}</p> : null}
    </section>
  );
}
