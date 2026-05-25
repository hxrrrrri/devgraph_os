import * as vscode from "vscode";

const SYMBOL_PATTERNS: Record<string, RegExp[]> = {
  python: [
    /^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(/,
    /^\s*class\s+([A-Za-z_]\w*)\b/
  ],
  typescript: [
    /^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(/,
    /^\s*(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)\b/,
    /^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)\b/,
    /^\s*(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*=/
  ],
  javascript: [
    /^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(/,
    /^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)\b/
  ]
};

SYMBOL_PATTERNS["typescriptreact"] = SYMBOL_PATTERNS["typescript"];
SYMBOL_PATTERNS["javascriptreact"] = SYMBOL_PATTERNS["javascript"];

export class DevGraphCodeLensProvider implements vscode.CodeLensProvider {
  private readonly emitter = new vscode.EventEmitter<void>();
  readonly onDidChangeCodeLenses = this.emitter.event;

  refresh(): void {
    this.emitter.fire();
  }

  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    if (!vscode.workspace.getConfiguration("devgraph").get<boolean>("codeLens.enabled", true)) {
      return [];
    }
    const patterns = SYMBOL_PATTERNS[document.languageId];
    if (!patterns) return [];

    const lenses: vscode.CodeLens[] = [];
    const totalLines = Math.min(document.lineCount, 2000);
    for (let line = 0; line < totalLines; line += 1) {
      const text = document.lineAt(line).text;
      for (const pattern of patterns) {
        const match = text.match(pattern);
        if (!match) continue;
        const name = match[1];
        const range = new vscode.Range(line, 0, line, text.length);
        lenses.push(
          new vscode.CodeLens(range, {
            title: "$(search-fuzzy) DevGraph: Explain",
            command: "devgraph.explainSymbol",
            arguments: [name, document.uri]
          }),
          new vscode.CodeLens(range, {
            title: "$(git-pull-request) DevGraph: Review impact",
            command: "devgraph.reviewSymbol",
            arguments: [name, document.uri]
          })
        );
        break;
      }
    }
    return lenses;
  }
}
