import {
  architecturePayloadSchema,
  communitiesPayloadSchema,
  graphPayloadSchema,
  graphStatusSchema,
  handoffPayloadSchema,
  layerDetailPayloadSchema,
  pathPayloadSchema,
  type ArchitecturePayload,
  type CommunitiesPayload,
  type GraphPayload,
  type GraphStatus,
  type HandoffPayload,
  type LayerDetailPayload,
  type PathPayload,
  reviewResultSchema,
  type ReviewResult
} from "@devgraph/schema";

export class DevGraphClient {
  constructor(private readonly baseUrl = "") {}

  async status(): Promise<GraphStatus> {
    const payload = await this.getJson("/api/status");
    return graphStatusSchema.parse(payload);
  }

  async graph(): Promise<GraphPayload> {
    const payload = await this.getJson("/api/graph");
    return graphPayloadSchema.parse(payload);
  }

  async review(): Promise<ReviewResult> {
    const payload = await this.getJson("/api/review");
    return reviewResultSchema.parse(payload);
  }

  async debug(issue: string): Promise<unknown> {
    return this.postJson("/api/debug", { issue });
  }

  async onboarding(): Promise<unknown> {
    return this.getJson("/api/onboarding");
  }

  async handoff(): Promise<HandoffPayload> {
    const payload = await this.getJson("/api/handoff");
    return handoffPayloadSchema.parse(payload);
  }

  async memories(): Promise<unknown> {
    return this.getJson("/api/memories");
  }

  async flows(query = ""): Promise<unknown> {
    return this.getJson(`/api/flows?q=${encodeURIComponent(query)}`);
  }

  async communities(): Promise<CommunitiesPayload> {
    const payload = await this.getJson("/api/communities");
    return communitiesPayloadSchema.parse(payload);
  }

  async search(query: string): Promise<unknown> {
    return this.getJson(`/api/search?q=${encodeURIComponent(query)}`);
  }

  async node(id: string): Promise<unknown> {
    return this.getJson(`/api/node/${encodeURIComponent(id)}`);
  }

  async fileContext(path: string): Promise<unknown> {
    return this.getJson(`/api/file-context?path=${encodeURIComponent(path)}`);
  }

  async provenance(entityId: string): Promise<unknown> {
    return this.getJson(`/api/provenance/${encodeURIComponent(entityId)}`);
  }

  async path(source: string, target: string, cutoff = 8): Promise<PathPayload> {
    const payload = await this.getJson(
      `/api/path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}&cutoff=${cutoff}`
    );
    return pathPayloadSchema.parse(payload);
  }

  async architecture(): Promise<ArchitecturePayload> {
    const payload = await this.getJson("/api/architecture");
    return architecturePayloadSchema.parse(payload);
  }

  async layer(id: string): Promise<LayerDetailPayload> {
    const payload = await this.getJson(`/api/layers/${encodeURIComponent(id)}`);
    return layerDetailPayloadSchema.parse(payload);
  }

  private async getJson(path: string): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}${path}`);
    if (!response.ok) {
      throw new Error(`DevGraph request failed: ${response.status}`);
    }
    return response.json() as Promise<unknown>;
  }

  private async postJson(path: string, body: unknown): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!response.ok) {
      throw new Error(`DevGraph request failed: ${response.status}`);
    }
    return response.json() as Promise<unknown>;
  }
}
