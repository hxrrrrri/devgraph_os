import { z } from "zod";
import { graphNodeSchema } from "./zod.js";

export const reviewResultSchema = z.object({
  changed_files: z.array(z.string()),
  changed_hunks: z.array(z.record(z.unknown())).default([]),
  changed_symbols: z.array(graphNodeSchema).default([]),
  changed_nodes: z.array(graphNodeSchema),
  impacted_nodes: z.array(graphNodeSchema),
  impacted_files: z.array(z.string()),
  impacted_flows: z.array(z.record(z.unknown())).default([]),
  affected_tests: z.array(z.string()),
  missing_tests: z.array(z.string()),
  public_api_changes: z.array(z.string()).default([]),
  config_or_infra_changes: z.array(z.string()).default([]),
  database_or_schema_changes: z.array(z.string()).default([]),
  security_sensitive_changes: z.array(z.string()).default([]),
  diff_summary: z.array(z.string()).default([]),
  changed_snippets: z.record(z.string()).default({}),
  risk_score: z.number(),
  risk_level: z.string(),
  risk_explanation: z.array(z.string()),
  prioritized_review_items: z.array(z.string()).default([]),
  review_checklist: z.array(z.string()),
  context_pack: z.string(),
  suggested_commands: z.array(z.string()),
  warnings: z.array(z.string()).default([])
});

export type ReviewResult = z.infer<typeof reviewResultSchema>;
