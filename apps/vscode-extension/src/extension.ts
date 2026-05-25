import * as vscode from "vscode";
import { registerDevGraphCommands } from "./commands/devgraphCommands";
import { DevGraphStatusProvider } from "./views/statusView";

export function activate(context: vscode.ExtensionContext): void {
  const provider = new DevGraphStatusProvider();
  vscode.window.registerTreeDataProvider("devgraph.statusView", provider);
  registerDevGraphCommands(context, () => provider.refresh());
}

export function deactivate(): void {}
