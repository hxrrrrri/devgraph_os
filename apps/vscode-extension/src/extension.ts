import * as vscode from "vscode";
import { DevGraphCodeLensProvider } from "./codeLens/devgraphCodeLens";
import { registerDevGraphCommands } from "./commands/devgraphCommands";
import { DevGraphStatusProvider } from "./views/statusView";

export function activate(context: vscode.ExtensionContext): void {
  const provider = new DevGraphStatusProvider();
  vscode.window.registerTreeDataProvider("devgraph.statusView", provider);

  const codeLens = new DevGraphCodeLensProvider();
  const codeLensSelector: vscode.DocumentSelector = [
    { language: "python" },
    { language: "typescript" },
    { language: "typescriptreact" },
    { language: "javascript" },
    { language: "javascriptreact" }
  ];
  context.subscriptions.push(
    vscode.languages.registerCodeLensProvider(codeLensSelector, codeLens),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("devgraph.codeLens")) {
        codeLens.refresh();
      }
    })
  );

  registerDevGraphCommands(context, () => provider.refresh());
}

export function deactivate(): void {}
