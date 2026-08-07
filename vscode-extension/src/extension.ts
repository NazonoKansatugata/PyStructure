import * as cp from 'node:child_process';
import * as path from 'node:path';

import * as vscode from 'vscode';

import { CliPayload, ResultsViewProvider } from './resultsView';

type CliError = Error & {
  stderr?: string;
  command?: string;
};

async function runPyStructureCli(scriptPath: string, workspacePath: string): Promise<CliPayload> {
  const attempts = [
    { command: 'python', args: [scriptPath, 'analyze', workspacePath, '--json'] },
    { command: 'python3', args: [scriptPath, 'analyze', workspacePath, '--json'] },
    { command: 'py', args: ['-3', scriptPath, 'analyze', workspacePath, '--json'] },
  ];

  let lastError: CliError | undefined;

  for (const attempt of attempts) {
    try {
      const stdout = await new Promise<string>((resolve, reject) => {
        cp.execFile(
          attempt.command,
          attempt.args,
          { maxBuffer: 10 * 1024 * 1024 },
          (error: Error | null, stdoutText: string, stderrText: string) => {
            if (error) {
              const cliError = error as CliError;
              cliError.stderr = stderrText;
              cliError.command = `${attempt.command} ${attempt.args.join(' ')}`;
              reject(cliError);
              return;
            }

            resolve(stdoutText);
          }
        );
      });

      return JSON.parse(stdout) as CliPayload;
    } catch (error) {
      lastError = error as CliError;
    }
  }

  const error: CliError = lastError ?? new Error('PyStructure CLI の起動に失敗しました。');
  const messageLines = ['PyStructure CLI の起動に失敗しました。'];

  if (error.command) {
    messageLines.push(`Command: ${error.command}`);
  }

  if (error.message) {
    messageLines.push(`Message: ${error.message}`);
  }

  if (error.stderr) {
    messageLines.push('stderr:', error.stderr.trim() || '(empty)');
  }

  throw new Error(messageLines.join('\n'));
}

export function activate(context: vscode.ExtensionContext): void {
  const outputChannel = vscode.window.createOutputChannel('PyStructure');
  const cliScriptPath = path.resolve(context.extensionPath, '..', 'src', 'cli.py');
  const resultsProvider = new ResultsViewProvider();
  const resultsView = vscode.window.createTreeView('pystructureResults', {
    treeDataProvider: resultsProvider,
  });

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
      resultsProvider.setResult(payload);
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

  context.subscriptions.push(disposable, outputChannel, resultsView);
}

export function deactivate(): void {
  // VS Code が拡張を解放するときに呼ばれる。
}
