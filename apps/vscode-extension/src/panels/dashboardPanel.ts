import * as vscode from "vscode";
import { spawn } from "node:child_process";
import { workspaceRoot } from "../client/cli";

export async function openDashboard(): Promise<void> {
  const config = vscode.workspace.getConfiguration("devgraph");
  const port = config.get<number>("dashboardPort", 38987);
  const binary = config.get<string>("binaryPath", "devgraph");
  spawn(binary, ["dashboard", "--port", String(port)], {
    cwd: workspaceRoot(),
    detached: true,
    stdio: "ignore",
    windowsHide: true
  }).unref();
  await vscode.env.openExternal(vscode.Uri.parse(`http://127.0.0.1:${port}`));
}
