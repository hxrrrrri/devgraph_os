import { z } from "zod";

export const confidenceTierSchema = z.enum(["extracted", "inferred", "llm", "ambiguous", "user"]);

export const nodeTypeSchema = z.enum([
  "repository",
  "file",
  "module",
  "function",
  "class",
  "type",
  "test",
  "api_endpoint",
  "database_table",
  "schema",
  "config",
  "service",
  "pipeline",
  "resource",
  "document",
  "section",
  "article",
  "claim",
  "entity",
  "domain",
  "flow",
  "step",
  "commit",
  "pull_request",
  "session",
  "decision"
]);

export const edgeTypeSchema = z.enum([
  "contains",
  "imports",
  "calls",
  "inherits",
  "implements",
  "tested_by",
  "depends_on",
  "reads_from",
  "writes_to",
  "routes_to",
  "configures",
  "deploys",
  "documents",
  "belongs_to",
  "cites",
  "contradicts",
  "builds_on",
  "affects",
  "changed_in",
  "discussed_in",
  "similar_to"
]);

export const graphNodeSchema = z.object({
  id: z.string(),
  type: nodeTypeSchema,
  name: z.string(),
  qualified_name: z.string(),
  file_path: z.string().nullable().optional(),
  line_start: z.number().nullable().optional(),
  line_end: z.number().nullable().optional(),
  language: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
  tags: z.array(z.string()).default([]),
  confidence: z.number(),
  confidence_tier: confidenceTierSchema,
  created_at: z.string(),
  updated_at: z.string(),
  content_hash: z.string().nullable().optional(),
  metadata: z.record(z.unknown()).default({})
});

export const graphEdgeSchema = z.object({
  id: z.string(),
  source_id: z.string(),
  target_id: z.string(),
  type: edgeTypeSchema,
  confidence: z.number(),
  confidence_tier: confidenceTierSchema,
  provenance_source: z.string(),
  file_path: z.string().nullable().optional(),
  line: z.number().nullable().optional(),
  metadata: z.record(z.unknown()).default({})
});

export const graphStatusSchema = z.object({
  project: z.string(),
  storage_path: z.string(),
  total_files: z.number(),
  total_nodes: z.number(),
  total_edges: z.number(),
  total_chunks: z.number(),
  languages: z.record(z.number()),
  last_indexed_at: z.string().nullable(),
  warnings: z.array(z.string())
});

export const graphPayloadSchema = z.object({
  nodes: z.array(graphNodeSchema),
  edges: z.array(graphEdgeSchema)
});

