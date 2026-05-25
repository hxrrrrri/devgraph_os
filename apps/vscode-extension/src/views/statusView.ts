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
        last_indexed_at: string | null;
      };
      return [
        item(`Files: ${status.total_files}`),
        item(`Nodes: ${status.total_nodes}`),
        item(`Edges: ${status.total_edges}`),
        item(`Last indexed: ${status.last_indexed_at ?? "never"}`)
      ];
    } catch {
      return [item("Run DevGraph: Initialize Project")];
    }
  }
}

function item(label: string): vscode.TreeItem {
  return new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
}

