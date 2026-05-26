import { useMemo } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Compass, X } from "lucide-react";
import { useDashboardStore, type LayerId } from "../store/dashboardStore";

interface TourStep {
  title: string;
  body: string;
  /** Layer to drill into when this step activates. */
  layerId?: LayerId;
  /** Optional CTA action. */
  cta?: { label: string; action: "openReview" | "openHandoff" | "overview" };
}

const STEPS: TourStep[] = [
  { title: "Entry points", body: "These are the doors into the system — endpoints, CLIs, routes. Start here when tracing user flows.", layerId: "entry" },
  { title: "UI / Frontend", body: "Where the user touches the system. Components and pages live here.", layerId: "ui" },
  { title: "Application services", body: "Where work coordination happens — services, orchestrators, use-cases.", layerId: "app" },
  { title: "Domain logic", body: "Pure business rules. Stays away from I/O.", layerId: "domain" },
  { title: "Data layer", body: "Tables, schemas, queries, migrations. Highest-risk layer for review.", layerId: "data" },
  { title: "Review hotspots", body: "Toggle diff mode in the toolbar to see what changed and what's affected.", cta: { label: "Open review lens", action: "openReview" } },
  { title: "Tests", body: "What protects each layer. Missing tests get flagged in the inspector.", layerId: "tests" },
  { title: "Docs & knowledge", body: "Markdown, ADRs, and stale-doc signals.", layerId: "docs" },
  { title: "Handoff", body: "Generate a context pack with memories + risk + review state for the next agent.", cta: { label: "Open handoff", action: "openHandoff" } },
];

interface Props {
  onCta?: (action: NonNullable<TourStep["cta"]>["action"]) => void;
}

export function GuidedTour({ onCta }: Props) {
  const active = useDashboardStore((s) => s.tourActive);
  const step = useDashboardStore((s) => s.tourStep);
  const stopTour = useDashboardStore((s) => s.stopTour);
  const nextTourStep = useDashboardStore((s) => s.nextTourStep);
  const prevTourStep = useDashboardStore((s) => s.prevTourStep);
  const drillIntoLayer = useDashboardStore((s) => s.drillIntoLayer);
  const navigateToOverview = useDashboardStore((s) => s.navigateToOverview);
  const layers = useDashboardStore((s) => s.layers);

  const current = useMemo(() => STEPS[Math.min(step, STEPS.length - 1)], [step]);
  const layerKnown = current.layerId
    ? layers.some((l) => l.id === current.layerId)
    : true;

  if (!active) return null;

  function handleNext() {
    if (current.layerId && layerKnown) drillIntoLayer(current.layerId);
    else navigateToOverview();
    nextTourStep();
  }

  function handlePrev() {
    prevTourStep();
  }

  function handleCta() {
    if (!current.cta) return;
    if (current.cta.action === "overview") navigateToOverview();
    onCta?.(current.cta.action);
  }

  return (
    <motion.div
      className="dg-tour-overlay"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="dg-tour-head">
        <span className="eyebrow"><Compass size={12} /> guided tour · {step + 1} / {STEPS.length}</span>
        <button className="icon-button" onClick={stopTour} aria-label="Close tour"><X size={14} /></button>
      </div>
      <h2 className="dg-tour-title">{current.title}</h2>
      <p className="dg-tour-body">{current.body}</p>
      {current.cta ? (
        <button className="btn btn-coral-soft btn-tiny" onClick={handleCta}>
          {current.cta.label}
        </button>
      ) : null}
      <div className="dg-tour-foot">
        <button className="btn btn-secondary btn-tiny" onClick={handlePrev} disabled={step === 0}>
          <ChevronLeft size={12} /> prev
        </button>
        <button className="btn btn-primary btn-tiny" onClick={handleNext} disabled={step >= STEPS.length - 1}>
          next <ChevronRight size={12} />
        </button>
      </div>
    </motion.div>
  );
}
