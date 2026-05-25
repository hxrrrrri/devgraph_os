import {
  graphPayloadSchema,
  graphStatusSchema,
  type GraphPayload,
  type GraphStatus,
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

  async handoff(): Promise<unknown> {
    return this.getJson("/api/handoff");
  }

  async memories(): Promise<unknown> {
    return this.getJson("/api/memories");
  }

  async flows(query = ""): Promise<unknown> {
    return this.getJson(`/api/flows?q=${encodeURIComponent(query)}`);
  }

  async search(query: string): Promise<unknown> {
    return this.getJson(`/api/search?q=${encodeURIComponent(query)}`);
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
