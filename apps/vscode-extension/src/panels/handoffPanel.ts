import * as vscode from "vscode";
import { runDevGraph } from "../client/cli";

let current: vscode.WebviewPanel | undefined;

export async function showHandoffPreview(): Promise<void> {
  if (!current) {
    current = vscode.window.createWebviewPanel(
      "devgraph.handoffPreview",
      "DevGraph Handoff",
      vscode.ViewColumn.Beside,
      { enableScripts: true, retainContextWhenHidden: true }
    );
    current.onDidDispose(() => {
      current = undefined;
    });
    current.webview.onDidReceiveMessage(async (message: { command?: string; text?: string }) => {
      if (message?.command === "copy" && typeof message.text === "string") {
        await vscode.env.clipboard.writeText(message.text);
        vscode.window.showInformationMessage("Copied to clipboard.");
      }
    });
  } else {
    current.reveal(vscode.ViewColumn.Beside);
  }
  try {
    await runDevGraph(["handoff"]);
    const root = vscode.workspace.workspaceFolders?.[0]?.uri;
    if (!root) return;
    const uri = vscode.Uri.joinPath(root, ".devgraph", "sessions", "handoff.json");
    const bytes = await vscode.workspace.fs.readFile(uri);
    const payload = JSON.parse(Buffer.from(bytes).toString("utf8")) as Record<string, unknown>;
    current.webview.html = renderHtml(payload);
  } catch (error) {
    current.webview.html = renderError(error);
  }
}

function renderHtml(payload: Record<string, unknown>): string {
  const sections: Array<[string, string]> = [
    ["Continue prompt", String(payload.continue_prompt ?? "")],
    ["Branch", String(payload.branch ?? "")],
    ["Changed symbols", asList(payload.changed_symbols)],
    ["Impacted files", asList(payload.impacted_files)],
    ["Open questions", asList(payload.open_questions)]
  ];
  return `<!doctype html><html><head><meta charset="utf-8" /><style>
    body { font: 13px var(--vscode-font-family); padding: 16px; color: var(--vscode-editor-foreground); }
    h2 { font-size: 13px; opacity: 0.8; text-transform: uppercase; letter-spacing: 0.08em; margin: 14px 0 4px; }
    section { margin-bottom: 14px; }
    pre { background: var(--vscode-textCodeBlock-background); padding: 10px; border-radius: 6px; overflow: auto; white-space: pre-wrap; }
    button { margin-top: 6px; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: 0; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
    .empty { opacity: 0.5; font-style: italic; }
  </style></head><body>
  ${sections.map(([title, body], idx) => `
    <section>
      <h2>${escapeHtml(title)}</h2>
      <pre id="s${idx}">${escapeHtml(body) || "<span class='empty'>Empty</span>"}</pre>
      <button onclick="copy(${idx})">Copy</button>
    </section>
  `).join("")}
  <script>
    const vscode = acquireVsCodeApi();
    function copy(idx) {
      const text = document.getElementById('s' + idx)?.textContent ?? '';
      vscode.postMessage({ command: 'copy', text });
    }
  </script>
  </body></html>`;
}

function asList(value: unknown): string {
  if (!Array.isArray(value)) return "";
  return value.map((entry) => (typeof entry === "string" ? entry : JSON.stringify(entry))).join("\n");
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
