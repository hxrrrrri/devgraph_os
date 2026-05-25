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
    vscode.commands.registerCommand("devgraph.searchGraph", () => searchGraph()),
    vscode.commands.registerCommand("devgraph.traceFlow", () => traceFlowFromSelection()),
    vscode.commands.registerCommand("devgraph.doctor", () => runAndShow(["doctor", "--json"], refresh)),
    vscode.commands.registerCommand("devgraph.rememberDecision", () => rememberDecision(refresh)),
    vscode.commands.registerCommand("devgraph.showMemories", () => runAndShow(["memories"], refresh)),
    vscode.commands.registerCommand("devgraph.openDashboard", () => openDashboard()),
    vscode.commands.registerCommand("devgraph.handoff", () => runAndShow(["handoff"], refresh)),
    vscode.commands.registerCommand("devgraph.copyHandoffPrompt", () => copyHandoffPrompt(refresh)),
    vscode.commands.registerCommand("devgraph.openReviewReport", () => openGeneratedReport(".devgraph/reports/review.md", ["review"], refresh)),
    vscode.commands.registerCommand("devgraph.openOnboardingGuide", () => openGeneratedReport(".devgraph/reports/onboarding.md", ["onboard"], refresh)),
    vscode.commands.registerCommand("devgraph.explainSymbol", (symbol: string, uri: vscode.Uri) => explainSymbol(symbol, uri)),
    vscode.commands.registerCommand("devgraph.reviewSymbol", (symbol: string, uri: vscode.Uri) => reviewSymbol(symbol, uri, refresh))
  );
}

async function explainSymbol(symbol: string, uri: vscode.Uri): Promise<void> {
  if (!symbol) return;
  const rel = uri ? vscode.workspace.asRelativePath(uri) : undefined;
  const args = rel ? ["explain", `${rel}::${symbol}`] : ["explain", symbol];
  await runAndShow(args);
}

async function reviewSymbol(symbol: string, uri: vscode.Uri, refresh: () => void): Promise<void> {
  if (!uri) {
    await runAndShow(["review", "--json"], refresh);
    return;
  }
  const rel = vscode.workspace.asRelativePath(uri);
  await runAndShow(["review", "--files", rel, "--json"], refresh);
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

async function searchGraph(): Promise<void> {
  const query = await vscode.window.showInputBox({ prompt: "Search DevGraph" });
  if (!query) return;
  await runAndShow(["search", query, "--json"]);
}

async function traceFlowFromSelection(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  const selection = editor?.document.getText(editor.selection).trim();
  const query = selection || editor?.document.fileName;
  if (!query) {
    vscode.window.showWarningMessage("Select a symbol or open a file to trace with DevGraph.");
    return;
  }
  await runAndShow(["trace", query]);
}

async function rememberDecision(refresh: () => void): Promise<void> {
  const decision = await vscode.window.showInputBox({ prompt: "Remember a DevGraph decision" });
  if (!decision) return;
  await runAndShow(["remember", "--kind", "decision", decision], refresh);
}

async function copyHandoffPrompt(refresh: () => void): Promise<void> {
  await runDevGraph(["handoff"]);
  refresh();
  const root = vscode.workspace.workspaceFolders?.[0]?.uri;
  if (!root) return;
  const uri = vscode.Uri.joinPath(root, ".devgraph", "sessions", "handoff.json");
  try {
    const bytes = await vscode.workspace.fs.readFile(uri);
    const payload = JSON.parse(Buffer.from(bytes).toString("utf8")) as { continue_prompt?: string };
    await vscode.env.clipboard.writeText(payload.continue_prompt ?? "");
    vscode.window.showInformationMessage("DevGraph handoff prompt copied.");
  } catch {
    vscode.window.showWarningMessage("DevGraph handoff prompt was not available.");
  }
}

async function openGeneratedReport(path: string, command: string[], refresh: () => void): Promise<void> {
  await runDevGraph(command);
  refresh();
  const root = vscode.workspace.workspaceFolders?.[0]?.uri;
  if (!root) return;
  const uri = vscode.Uri.joinPath(root, ...path.split("/"));
  const doc = await vscode.workspace.openTextDocument(uri);
  await vscode.window.showTextDocument(doc, { preview: true });
}

async function runAndShow(args: string[], refresh?: () => void): Promise<void> {
  try {
    const output = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: `devgraph ${args.join(" ")}` },
      () => runDevGraph(args)
    );
    if (vscode.workspace.getConfiguration("devgraph").get<boolean>("autoRefresh", true)) {
      refresh?.();
    }
    const doc = await vscode.workspace.openTextDocument({ content: output, language: "markdown" });
    await vscode.window.showTextDocument(doc, { preview: true });
  } catch (err) {
    vscode.window.showErrorMessage(err instanceof Error ? err.message : "DevGraph command failed.");
  }
}
