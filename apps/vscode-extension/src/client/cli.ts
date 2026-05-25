import { execFile } from "node:child_process";
import * as vscode from "vscode";

export function workspaceRoot(): string {
  const folder = vscode.workspace.workspaceFolders?.[0];
  if (!folder) {
    throw new Error("Open a workspace folder before running DevGraph.");
  }
  return folder.uri.fsPath;
}

export function runDevGraph(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    execFile("devgraph", args, { cwd: workspaceRoot(), maxBuffer: 1024 * 1024 * 10 }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(stderr || error.message));
        return;
      }
      resolve(stdout || stderr);
    });
  });
}

