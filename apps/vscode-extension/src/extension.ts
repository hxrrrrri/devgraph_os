import * as vscode from "vscode";
import { DevGraphCodeLensProvider } from "./codeLens/devgraphCodeLens";
import { registerDevGraphCommands } from "./commands/devgraphCommands";
import { showGraphStatus } from "./panels/graphStatusPanel";
import { showHandoffPreview } from "./panels/handoffPanel";
import { showNodeDetail } from "./panels/nodeDetailPanel";
import { showReviewPreview } from "./panels/reviewPreviewPanel";
import { runDevGraph } from "./client/cli";
import { DevGraphStatusProvider } from "./views/statusView";
import {
  ChangedFilesProvider,
  ImpactedFilesProvider,
  RiskyNodesProvider
} from "./views/reviewTrees";

export function activate(context: vscode.ExtensionContext): void {
  const status = new DevGraphStatusProvider();
  const changed = new ChangedFilesProvider();
  const impacted = new ImpactedFilesProvider();
  const risky = new RiskyNodesProvider();
  vscode.window.registerTreeDataProvider("devgraph.statusView", status);
  vscode.window.registerTreeDataProvider("devgraph.changedView", changed);
  vscode.window.registerTreeDataProvider("devgraph.impactedView", impacted);
  vscode.window.registerTreeDataProvider("devgraph.riskyView", risky);

  const refreshAll = debounce(() => {
    status.refresh();
    changed.refresh();
    impacted.refresh();
    risky.refresh();
  }, 500);

  const codeLens = new DevGraphCodeLensProvider();
  const codeLensSelector: vscode.DocumentSelector = [
    { language: "python" },
    { language: "typescript" },
    { language: "typescriptreact" },
    { language: "javascript" },
    { language: "javascriptreact" }
  ];

  const watcher = vscode.workspace.createFileSystemWatcher("**/*");
  watcher.onDidChange(refreshAll);
  watcher.onDidCreate(refreshAll);
  watcher.onDidDelete(refreshAll);

  context.subscriptions.push(
    watcher,
    vscode.languages.registerCodeLensProvider(codeLensSelector, codeLens),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("devgraph.codeLens")) {
        codeLens.refresh();
      }
    }),
    vscode.commands.registerCommand("devgraph.showReviewPreview", () => showReviewPreview()),
    vscode.commands.registerCommand("devgraph.showNodeDetail", (symbol?: string) => showNodeDetail(symbol)),
    vscode.commands.registerCommand("devgraph.showHandoffPreview", () => showHandoffPreview()),
    vscode.commands.registerCommand("devgraph.showGraphStatus", () => showGraphStatus()),
    vscode.commands.registerCommand("devgraph.reviewStaged", async () => {
      await runDevGraph(["review", "--staged", "--json"]);
      refreshAll();
      await showReviewPreview();
    }),
    vscode.commands.registerCommand("devgraph.refreshTrees", () => refreshAll())
  );

  registerDevGraphCommands(context, refreshAll);
}

export function deactivate(): void {}

function debounce<T extends (...args: never[]) => void>(fn: T, wait: number): T {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return ((...args: never[]) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  }) as T;
}
