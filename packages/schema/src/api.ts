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
  migration_warnings: z.array(z.record(z.unknown())).default([]),
  api_signature_changes: z.array(z.record(z.unknown())).default([]),
  route_contract_changes: z.array(z.record(z.unknown())).default([]),
  fan_out: z.array(z.record(z.unknown())).default([]),
  infra_blast_radius: z.array(z.record(z.unknown())).default([]),
  severity_by_file: z.record(z.string()).default({}),
  severity_by_symbol: z.record(z.string()).default({}),
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

export const handoffPayloadSchema = z.object({
  markdown_path: z.string(),
  json_path: z.string(),
  markdown: z.string(),
  data: z.record(z.unknown())
});

export type HandoffPayload = z.infer<typeof handoffPayloadSchema>;

export const communitySchema = z.object({
  name: z.string(),
  node_count: z.number()
});

export const communitiesPayloadSchema = z.object({
  communities: z.array(communitySchema)
});

export type Community = z.infer<typeof communitySchema>;
export type CommunitiesPayload = z.infer<typeof communitiesPayloadSchema>;


