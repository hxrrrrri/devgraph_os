import type { z } from "zod";
import { graphEdgeSchema, graphNodeSchema, graphPayloadSchema, graphStatusSchema } from "./zod.js";

export type GraphNode = z.infer<typeof graphNodeSchema>;
export type GraphEdge = z.infer<typeof graphEdgeSchema>;
export type GraphPayload = z.infer<typeof graphPayloadSchema>;
export type GraphStatus = z.infer<typeof graphStatusSchema>;

