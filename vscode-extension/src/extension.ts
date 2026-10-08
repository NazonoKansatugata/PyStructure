import * as path from 'node:path';

import * as vscode from 'vscode';

import { runPyStructureCli } from './cliRunner';
import { GraphPanel } from './graphPanel';
import { CliPayload, ResultsViewProvider } from './resultsView';

export function activate(context: vscode.ExtensionContext): void {
  const outputChannel = vscode.window.createOutputChannel('PyStructure');
  const cliScriptPath = path.resolve(context.extensionPath, '..', 'src', 'cli.py');
  const graphAssetsRoot = vscode.Uri.file(path.join(context.extensionPath, 'media', 'webview'));
  const resultsProvider = new ResultsViewProvider();
  const resultsView = vscode.window.createTreeView('pystructureResults', {
    treeDataProvider: resultsProvider,
  });

  const analyze = async (): Promise<CliPayload | undefined> => {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];

    if (!workspaceFolder) {
      void vscode.window.showWarningMessage('PyStructure: ワークスペースが開かれていません。');
      return undefined;
    }

    outputChannel.show(true);
    outputChannel.appendLine(`PyStructure: analyzing ${workspaceFolder.uri.fsPath}`);

    try {
      const payload = await runPyStructureCli(cliScriptPath, workspaceFolder.uri.fsPath);
      resultsProvider.setResult(payload);
      outputChannel.appendLine(
        `PyStructure: analysis complete (${payload.analysis.modules.length} modules, ${payload.graph.nodes.length} nodes, ${payload.graph.edges.length} edges)`
      );
      return payload;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      outputChannel.appendLine(message);
      void vscode.window.showErrorMessage(`PyStructure: CLI の実行に失敗しました: ${message}`);
      return undefined;
    }
  };

  const analyzeCommand = vscode.commands.registerCommand('pystructure.analyzeWorkspace', async () => {
    const payload = await analyze();
    if (payload) {
      void vscode.window.showInformationMessage(
        `PyStructure: ${payload.analysis.modules.length} modules, ${payload.graph.nodes.length} nodes, ${payload.graph.edges.length} edges`
      );
    }
  });

  const graphCommand = vscode.commands.registerCommand('pystructure.showGraph', async () => {
    const payload = await analyze();
    if (payload) {
      GraphPanel.show(graphAssetsRoot, payload);
    }
  });

  context.subscriptions.push(analyzeCommand, graphCommand, outputChannel, resultsView);
}

export function deactivate(): void {
  // VS Code が拡張を解放するときに呼ばれる。
}
