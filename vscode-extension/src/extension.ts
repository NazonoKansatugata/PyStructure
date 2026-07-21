import * as cp from 'node:child_process';
import * as path from 'node:path';

import * as vscode from 'vscode';

type CliPayload = {
  analysis: {
    root: string;
    modules: Array<{ module_name: string }>;
  };
  graph: {
    nodes: unknown[];
    edges: unknown[];
  };
};

async function runPyStructureCli(scriptPath: string, workspacePath: string): Promise<CliPayload> {
  const attempts = [
    { command: 'python', args: [scriptPath, 'analyze', workspacePath, '--json'] },
    { command: 'python3', args: [scriptPath, 'analyze', workspacePath, '--json'] },
    { command: 'py', args: ['-3', scriptPath, 'analyze', workspacePath, '--json'] },
  ];

  let lastError: unknown;

  for (const attempt of attempts) {
    try {
      const stdout = await new Promise<string>((resolve, reject) => {
        cp.execFile(
          attempt.command,
          attempt.args,
          { maxBuffer: 10 * 1024 * 1024 },
          (error: Error | null, stdoutText: string) => {
            if (error) {
              reject(error);
              return;
            }

            resolve(stdoutText);
          }
        );
      });

      return JSON.parse(stdout) as CliPayload;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('PyStructure CLI の起動に失敗しました。');
}

export function activate(context: vscode.ExtensionContext): void {
  const outputChannel = vscode.window.createOutputChannel('PyStructure');
  const cliScriptPath = path.resolve(context.extensionPath, '..', 'src', 'cli.py');

  const disposable = vscode.commands.registerCommand('pystructure.analyzeWorkspace', async () => {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];

    if (!workspaceFolder) {
      void vscode.window.showWarningMessage('PyStructure: ワークスペースが開かれていません。');
      return;
    }

    outputChannel.show(true);
    outputChannel.appendLine(`PyStructure: analyzing ${workspaceFolder.uri.fsPath}`);

    try {
      const payload = await runPyStructureCli(cliScriptPath, workspaceFolder.uri.fsPath);
      outputChannel.appendLine(JSON.stringify(payload, null, 2));
      void vscode.window.showInformationMessage(
        `PyStructure: ${payload.analysis.modules.length} modules, ${payload.graph.nodes.length} nodes, ${payload.graph.edges.length} edges`
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      outputChannel.appendLine(message);
      void vscode.window.showErrorMessage(`PyStructure: CLI の実行に失敗しました: ${message}`);
    }
  });

  context.subscriptions.push(disposable, outputChannel);
}

export function deactivate(): void {
  // VS Code が拡張を解放するときに呼ばれる。
}
