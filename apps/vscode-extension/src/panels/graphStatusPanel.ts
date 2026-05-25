import * as vscode from "vscode";
import { runDevGraph } from "../client/cli";

let current: vscode.WebviewPanel | undefined;

export async function showGraphStatus(): Promise<void> {
  if (!current) {
    current = vscode.window.createWebviewPanel(
      "devgraph.graphStatus",
      "DevGraph Status",
      vscode.ViewColumn.Beside,
      { enableScripts: false, retainContextWhenHidden: true }
    );
    current.onDidDispose(() => {
      current = undefined;
    });
  } else {
    current.reveal(vscode.ViewColumn.Beside);
  }
  try {
    const output = await runDevGraph(["status", "--json"]);
    const data = JSON.parse(output) as Record<string, unknown>;
    current.webview.html = renderHtml(data);
  } catch (error) {
    current.webview.html = renderError(error);
  }
}

function renderHtml(data: Record<string, unknown>): string {
  const languages = (data.languages ?? {}) as Record<string, number>;
  const warnings = (data.warnings ?? []) as string[];
  return `<!doctype html><html><head><meta charset="utf-8" /><style>
    body { font: 13px var(--vscode-font-family); padding: 18px; color: var(--vscode-editor-foreground); }
    h1 { font-size: 15px; margin-top: 0; }
    table { border-collapse: collapse; margin: 8px 0 14px; }
    td { padding: 4px 12px 4px 0; }
    td.k { opacity: 0.7; }
    .warn { color: #fb7185; }
  </style></head><body>
  <h1>${escapeHtml(String(data.project ?? "unknown"))}</h1>
  <table>
    <tr><td class="k">Files</td><td>${escapeHtml(String(data.total_files ?? 0))}</td></tr>
    <tr><td class="k">Nodes</td><td>${escapeHtml(String(data.total_nodes ?? 0))}</td></tr>
    <tr><td class="k">Edges</td><td>${escapeHtml(String(data.total_edges ?? 0))}</td></tr>
    <tr><td class="k">Chunks</td><td>${escapeHtml(String(data.total_chunks ?? 0))}</td></tr>
    <tr><td class="k">Last indexed</td><td>${escapeHtml(String(data.last_indexed_at ?? "never"))}</td></tr>
  </table>
  <h2>Languages</h2>
  <table>
    ${Object.entries(languages).map(([lang, count]) => `<tr><td class="k">${escapeHtml(lang)}</td><td>${escapeHtml(String(count))}</td></tr>`).join("")}
  </table>
  ${warnings.length ? `<h2>Warnings</h2><ul>${warnings.map((w) => `<li class="warn">${escapeHtml(w)}</li>`).join("")}</ul>` : ""}
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
