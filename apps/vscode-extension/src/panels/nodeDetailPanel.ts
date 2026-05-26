import * as vscode from "vscode";
import { runDevGraph } from "../client/cli";

let current: vscode.WebviewPanel | undefined;

export async function showNodeDetail(symbol?: string): Promise<void> {
  const target = symbol ?? (await pickSymbol());
  if (!target) return;
  if (!current) {
    current = vscode.window.createWebviewPanel(
      "devgraph.nodeDetail",
      "DevGraph Node Detail",
      vscode.ViewColumn.Beside,
      { enableScripts: false, retainContextWhenHidden: true }
    );
    current.onDidDispose(() => {
      current = undefined;
    });
  } else {
    current.reveal(vscode.ViewColumn.Beside);
  }
  current.title = `DevGraph: ${target}`;
  try {
    const output = await runDevGraph(["explain", target, "--json"]);
    const data = JSON.parse(output) as Record<string, unknown>;
    current.webview.html = renderHtml(target, data);
  } catch (error) {
    current.webview.html = renderError(error);
  }
}

async function pickSymbol(): Promise<string | undefined> {
  const editor = vscode.window.activeTextEditor;
  if (editor && !editor.selection.isEmpty) {
    return editor.document.getText(editor.selection).trim();
  }
  return vscode.window.showInputBox({ prompt: "Symbol or file to inspect" });
}

function renderHtml(symbol: string, data: Record<string, unknown>): string {
  const summary = String(data.summary ?? data.description ?? "");
  const callers = (data.callers ?? data.referenced_by ?? []) as Array<Record<string, unknown>>;
  const callees = (data.callees ?? data.calls ?? []) as Array<Record<string, unknown>>;
  const tests = (data.tests ?? []) as Array<Record<string, unknown>>;
  const excerpt = String(data.excerpt ?? data.snippet ?? "");
  return `<!doctype html><html><head><meta charset="utf-8" /><style>
    body { font: 13px var(--vscode-font-family); padding: 16px; color: var(--vscode-editor-foreground); }
    h1 { font-size: 16px; margin-top: 0; }
    h2 { font-size: 13px; margin: 14px 0 4px; opacity: 0.8; text-transform: uppercase; letter-spacing: 0.08em; }
    ul { list-style: none; padding: 0; margin: 0; }
    li { padding: 3px 0; }
    pre { background: var(--vscode-textCodeBlock-background); padding: 10px; border-radius: 6px; overflow: auto; font-size: 12px; }
    .empty { opacity: 0.5; font-style: italic; }
  </style></head><body>
  <h1>${escapeHtml(symbol)}</h1>
  <p>${escapeHtml(summary) || "<span class='empty'>No summary available.</span>"}</p>
  <h2>Callers</h2>
  <ul>${callers.length ? callers.map((c) => `<li>${escapeHtml(String(c.qualified_name ?? c.name ?? ""))}</li>`).join("") : "<li class='empty'>None</li>"}</ul>
  <h2>Callees</h2>
  <ul>${callees.length ? callees.map((c) => `<li>${escapeHtml(String(c.qualified_name ?? c.name ?? ""))}</li>`).join("") : "<li class='empty'>None</li>"}</ul>
  <h2>Tests</h2>
  <ul>${tests.length ? tests.map((c) => `<li>${escapeHtml(String(c.qualified_name ?? c.name ?? ""))}</li>`).join("") : "<li class='empty'>None</li>"}</ul>
  <h2>Source</h2>
  <pre>${escapeHtml(excerpt) || "<span class='empty'>No excerpt available.</span>"}</pre>
  </body></html>`;
}

function renderError(error: unknown): string {
  const msg = error instanceof Error ? error.message : String(error);
  return `<!doctype html><html><body><pre>${escapeHtml(msg)}</pre></body></html>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  } as Record<string, string>)[char] ?? char);
}
