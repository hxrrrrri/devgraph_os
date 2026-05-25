import * as vscode from "vscode";
import { runDevGraph } from "../client/cli";

type ReviewJson = {
  changed_files?: string[];
  impacted_files?: string[];
  migration_warnings?: Array<{ code?: string; severity?: string; file_path?: string }>;
  api_signature_changes?: Array<{ code?: string; severity?: string; qualified_name?: string; file_path?: string }>;
  route_contract_changes?: Array<{ code?: string; severity?: string; method?: string; path?: string }>;
  severity_by_file?: Record<string, string>;
  fan_out?: Array<{ qualified_name?: string; fan_in?: number; fan_out?: number; file_path?: string }>;
};

async function loadReview(): Promise<ReviewJson> {
  try {
    const output = await runDevGraph(["review", "--json"]);
    return JSON.parse(output) as ReviewJson;
  } catch {
    return {};
  }
}

abstract class BaseTreeProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  protected readonly emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.emitter.event;

  refresh(): void {
    this.emitter.fire();
  }

  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  abstract getChildren(): Promise<vscode.TreeItem[]>;
}

export class ChangedFilesProvider extends BaseTreeProvider {
  async getChildren(): Promise<vscode.TreeItem[]> {
    const review = await loadReview();
    const files = review.changed_files ?? [];
    if (!files.length) return [leaf("No changed files detected.")];
    return files.map((file) => fileLeaf(file, review.severity_by_file?.[file]));
  }
}

export class ImpactedFilesProvider extends BaseTreeProvider {
  async getChildren(): Promise<vscode.TreeItem[]> {
    const review = await loadReview();
    const files = review.impacted_files ?? [];
    if (!files.length) return [leaf("No impacted files in current diff.")];
    return files.map((file) => fileLeaf(file, review.severity_by_file?.[file]));
  }
}

export class RiskyNodesProvider extends BaseTreeProvider {
  async getChildren(): Promise<vscode.TreeItem[]> {
    const review = await loadReview();
    const items: vscode.TreeItem[] = [];
    for (const warning of review.migration_warnings ?? []) {
      if ((warning.severity ?? "").toLowerCase() === "high") {
        items.push(leaf(`migration:${warning.code ?? "warn"} (${warning.file_path ?? "?"})`));
      }
    }
    for (const change of review.api_signature_changes ?? []) {
      if ((change.severity ?? "").toLowerCase() === "high") {
        items.push(leaf(`api:${change.code ?? "warn"} ${change.qualified_name ?? ""}`));
      }
    }
    for (const change of review.route_contract_changes ?? []) {
      if ((change.severity ?? "").toLowerCase() === "high") {
        items.push(leaf(`route:${change.code ?? "warn"} ${change.method ?? ""} ${change.path ?? ""}`));
      }
    }
    for (const entry of review.fan_out ?? []) {
      const total = (entry.fan_in ?? 0) + (entry.fan_out ?? 0);
      if (total >= 10) {
        items.push(leaf(`fan-out:${total} ${entry.qualified_name ?? "?"}`));
      }
    }
    if (!items.length) return [leaf("No high-severity warnings found.")];
    return items;
  }
}

function leaf(label: string): vscode.TreeItem {
  return new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
}

function fileLeaf(file: string, severity?: string): vscode.TreeItem {
  const item = new vscode.TreeItem(severity ? `[${severity}] ${file}` : file, vscode.TreeItemCollapsibleState.None);
  const root = vscode.workspace.workspaceFolders?.[0]?.uri;
  if (root) {
    item.resourceUri = vscode.Uri.joinPath(root, ...file.split("/"));
    item.command = {
      command: "vscode.open",
      title: "Open File",
      arguments: [item.resourceUri]
    };
  }
  return item;
}
