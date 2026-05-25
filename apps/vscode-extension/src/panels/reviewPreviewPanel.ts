import * as vscode from "vscode";
import { runDevGraph } from "../client/cli";

let current: vscode.WebviewPanel | undefined;

export async function showReviewPreview(): Promise<void> {
  if (current) {
    current.reveal(vscode.ViewColumn.Beside);
    await refresh();
    return;
  }
  current = vscode.window.createWebviewPanel(
    "devgraph.reviewPreview",
    "DevGraph Review",
    vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true }
  );
  current.onDidDispose(() => {
    current = undefined;
  });
  current.webview.onDidReceiveMessage(async (message: { command?: string; file?: string }) => {
    if (message?.command === "openFile" && message.file) {
      const root = vscode.workspace.workspaceFolders?.[0]?.uri;
      if (!root) return;
      const target = vscode.Uri.joinPath(root, ...message.file.split("/"));
      const doc = await vscode.workspace.openTextDocument(target);
      await vscode.window.showTextDocument(doc, { preview: true });
    }
  });
  await refresh();
}

async function refresh(): Promise<void> {
  if (!current) return;
  try {
    const output = await runDevGraph(["review", "--json"]);
    const data = JSON.parse(output) as Record<string, unknown>;
    current.webview.html = renderHtml(data);
  } catch (error) {
    current.webview.html = renderError(error);
  }
}

function renderHtml(data: Record<string, unknown>): string {
  const severityByFile = (data.severity_by_file ?? {}) as Record<string, string>;
  const changedFiles = (data.changed_files ?? []) as string[];
  const impactedFiles = (data.impacted_files ?? []) as string[];
  const migrationWarnings = (data.migration_warnings ?? []) as Array<Record<string, unknown>>;
  const apiChanges = (data.api_signature_changes ?? []) as Array<Record<string, unknown>>;
  const routeChanges = (data.route_contract_changes ?? []) as Array<Record<string, unknown>>;
  const fanOut = (data.fan_out ?? []) as Array<Record<string, unknown>>;
  const blast = (data.infra_blast_radius ?? []) as Array<Record<string, unknown>>;
  return `<!doctype html>
<html><head><meta charset="utf-8" />
<style>
  body { font: 13px/1.5 var(--vscode-font-family); padding: 18px; color: var(--vscode-editor-foreground); }
  h2 { font-size: 14px; margin: 18px 0 8px; }
  ul { list-style: none; padding: 0; margin: 0; }
  li { padding: 4px 6px; border-radius: 4px; margin-bottom: 2px; cursor: pointer; }
  li:hover { background: var(--vscode-list-hoverBackground); }
  li.sev-high { border-left: 3px solid #fb7185; padding-left: 6px; }
  li.sev-medium { border-left: 3px solid #facc15; padding-left: 6px; }
  li.sev-low { border-left: 3px solid #60a5fa; padding-left: 6px; }
  .meta { opacity: 0.7; font-size: 11px; }
  .empty { opacity: 0.5; font-style: italic; }
</style></head><body>
<h1>Risk: ${escapeHtml(String(data.risk_level ?? "?"))} (${escapeHtml(String(data.risk_score ?? 0))}/100)</h1>

<h2>Changed files</h2>
<ul>${changedFiles.length ? changedFiles.map((f) => fileLi(f, severityByFile[f])).join("") : "<li class='empty'>None</li>"}</ul>

<h2>Impacted files</h2>
<ul>${impactedFiles.length ? impactedFiles.map((f) => fileLi(f, severityByFile[f])).join("") : "<li class='empty'>None</li>"}</ul>

<h2>Migration warnings</h2>
<ul>${migrationWarnings.length ? migrationWarnings.map((w) => `<li class='sev-${escapeHtml(String(w.severity ?? "low"))}'>${escapeHtml(String(w.code ?? ""))} ${escapeHtml(String(w.detail ?? w.file_path ?? ""))}</li>`).join("") : "<li class='empty'>None</li>"}</ul>

<h2>API signature changes</h2>
<ul>${apiChanges.length ? apiChanges.map((w) => `<li class='sev-${escapeHtml(String(w.severity ?? "low"))}'>${escapeHtml(String(w.code ?? ""))} <span class='meta'>${escapeHtml(String(w.qualified_name ?? ""))}</span></li>`).join("") : "<li class='empty'>None</li>"}</ul>

<h2>Route contract changes</h2>
<ul>${routeChanges.length ? routeChanges.map((w) => `<li class='sev-${escapeHtml(String(w.severity ?? "low"))}'>${escapeHtml(String(w.code ?? ""))} ${escapeHtml(String(w.method ?? ""))} ${escapeHtml(String(w.path ?? ""))}</li>`).join("") : "<li class='empty'>None</li>"}</ul>

<h2>Top fan-out</h2>
<ul>${fanOut.length ? fanOut.map((w) => `<li><b>${escapeHtml(String(w.fan_in ?? 0))}→${escapeHtml(String(w.fan_out ?? 0))}</b> <span class='meta'>${escapeHtml(String(w.qualified_name ?? ""))}</span></li>`).join("") : "<li class='empty'>None</li>"}</ul>

<h2>Infra blast radius</h2>
<ul>${blast.length ? blast.map((w) => `<li>${escapeHtml(String(w.category ?? ""))} <span class='meta'>${escapeHtml(String(w.file_path ?? ""))}</span></li>`).join("") : "<li class='empty'>None</li>"}</ul>

<script>
  const vscode = acquireVsCodeApi();
  document.querySelectorAll('li[data-file]').forEach((node) => {
    node.addEventListener('click', () => {
      const file = node.getAttribute('data-file');
      if (file) vscode.postMessage({ command: 'openFile', file });
    });
  });
</script>
</body></html>`;
}

function fileLi(file: string, severity?: string): string {
  const cls = severity ? `sev-${severity}` : "";
  return `<li class="${cls}" data-file="${escapeAttr(file)}">${escapeHtml(file)}</li>`;
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

function escapeAttr(value: string): string {
  return escapeHtml(value).replace(/`/g, "&#96;");
}
