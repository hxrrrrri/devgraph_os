import * as vscode from "vscode";
import { runDevGraph } from "../client/cli";
import { openDashboard } from "../panels/dashboardPanel";

export function registerDevGraphCommands(context: vscode.ExtensionContext, refresh: () => void): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("devgraph.init", () => runAndShow(["init"], refresh)),
    vscode.commands.registerCommand("devgraph.build", () => runAndShow(["build"], refresh)),
    vscode.commands.registerCommand("devgraph.update", () => runAndShow(["update"], refresh)),
    vscode.commands.registerCommand("devgraph.reviewChanges", () => runAndShow(["review"], refresh)),
    vscode.commands.registerCommand("devgraph.explainCurrentFile", () => explainCurrentFile()),
    vscode.commands.registerCommand("devgraph.explainSelection", () => explainSelection()),
    vscode.commands.registerCommand("devgraph.ask", () => askProject()),
    vscode.commands.registerCommand("devgraph.openDashboard", () => openDashboard()),
    vscode.commands.registerCommand("devgraph.handoff", () => runAndShow(["handoff"], refresh))
  );
}

async function explainCurrentFile(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("Open a file to explain with DevGraph.");
    return;
  }
  await runAndShow(["explain", vscode.workspace.asRelativePath(editor.document.uri)]);
}

async function explainSelection(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  const selection = editor?.document.getText(editor.selection).trim();
  if (!selection) {
    vscode.window.showWarningMessage("Select a symbol or text to explain with DevGraph.");
    return;
  }
  await runAndShow(["explain", selection]);
}

async function askProject(): Promise<void> {
  const question = await vscode.window.showInputBox({ prompt: "Ask DevGraph about this project" });
  if (!question) return;
  await runAndShow(["ask", question]);
}

async function runAndShow(args: string[], refresh?: () => void): Promise<void> {
  try {
    const output = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: `devgraph ${args.join(" ")}` },
      () => runDevGraph(args)
    );
    refresh?.();
    const doc = await vscode.workspace.openTextDocument({ content: output, language: "markdown" });
    await vscode.window.showTextDocument(doc, { preview: true });
  } catch (err) {
    vscode.window.showErrorMessage(err instanceof Error ? err.message : "DevGraph command failed.");
  }
}

