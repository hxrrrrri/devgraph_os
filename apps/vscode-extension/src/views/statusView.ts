import * as vscode from "vscode";
import { runDevGraph } from "../client/cli";

export class DevGraphStatusProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  private readonly emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;

  refresh(): void {
    this.emitter.fire();
  }

  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(): Promise<vscode.TreeItem[]> {
    try {
      const output = await runDevGraph(["status", "--json"]);
      const status = JSON.parse(output) as {
        total_files: number;
        total_nodes: number;
        total_edges: number;
        total_chunks: number;
        last_indexed_at: string | null;
        warnings: string[];
      };
      const reviewOutput = await safeRun(["review", "--json"]);
      const review = reviewOutput ? JSON.parse(reviewOutput) as { changed_files?: string[]; impacted_files?: string[]; risk_score?: number; risk_level?: string } : {};
      const memoryOutput = await safeRun(["memories", "--json"]);
      const memories = memoryOutput ? JSON.parse(memoryOutput) as Array<{ kind: string; content: string }> : [];
      return [
        item(`Graph Status: ${status.total_files} files, ${status.total_nodes} nodes`),
        item(`Edges / Chunks: ${status.total_edges} / ${status.total_chunks}`),
        item(`Last indexed: ${status.last_indexed_at ?? "never"}`),
        item(`Changed Files: ${(review.changed_files ?? []).length}`),
        item(`Impacted Files: ${(review.impacted_files ?? []).length}`),
        item(`High Risk Nodes: ${review.risk_score ?? 0}/100 ${review.risk_level ?? "unknown"}`),
        item(`Recent Sessions: use DevGraph handoff`),
        item(`Memories: ${memories.length}`),
        item("Quick Actions: command palette")
      ];
    } catch {
      return [item("Run DevGraph: Initialize Project")];
    }
  }
}

function item(label: string): vscode.TreeItem {
  return new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
}

async function safeRun(args: string[]): Promise<string | null> {
  try {
    return await runDevGraph(args);
  } catch {
    return null;
  }
}
