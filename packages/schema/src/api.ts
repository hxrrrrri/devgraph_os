import { z } from "zod";
import { graphNodeSchema } from "./zod.js";

export const reviewResultSchema = z.object({
  changed_files: z.array(z.string()),
  changed_nodes: z.array(graphNodeSchema),
  impacted_nodes: z.array(graphNodeSchema),
  impacted_files: z.array(z.string()),
  affected_tests: z.array(z.string()),
  missing_tests: z.array(z.string()),
  diff_summary: z.array(z.string()).default([]),
  changed_snippets: z.record(z.string()).default({}),
  risk_score: z.number(),
  risk_level: z.string(),
  risk_explanation: z.array(z.string()),
  review_checklist: z.array(z.string()),
  context_pack: z.string(),
  suggested_commands: z.array(z.string()),
  warnings: z.array(z.string()).default([])
});

export type ReviewResult = z.infer<typeof reviewResultSchema>;
