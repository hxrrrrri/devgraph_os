import * as vscode from "vscode";

export async function openDashboard(): Promise<void> {
  await vscode.env.openExternal(vscode.Uri.parse("http://127.0.0.1:38987"));
}

