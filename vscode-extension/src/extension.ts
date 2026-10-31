import * as path from 'node:path';

import * as vscode from 'vscode';

import { runPyStructureCli, runPyStructureCliText } from './cliRunner';
import { GraphPanel } from './graphPanel';
import { CliPayload, ResultsViewProvider } from './resultsView';

export function activate(context: vscode.ExtensionContext): void {
  const outputChannel = vscode.window.createOutputChannel('PyStructure');
  const cliScriptPath = path.join(context.extensionPath, 'python', 'cli.py');
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
      GraphPanel.show(graphAssetsRoot, payload);
      void vscode.window.showInformationMessage(
        `PyStructure: ${payload.analysis.modules.length} modules, ${payload.graph.nodes.length} nodes, ${payload.graph.edges.length} edges`
      );
    }
  });

  const highlightCommand = vscode.commands.registerCommand('pystructure.highlightAdvice', (targets: string[]) => {
    GraphPanel.highlight(targets);
  });

  const exportCommand = vscode.commands.registerCommand('pystructure.exportAdviceMarkdown', async () => {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
      void vscode.window.showWarningMessage('PyStructure: ワークスペースが開かれていません。');
      return;
    }

    const target = await vscode.window.showSaveDialog({
      defaultUri: vscode.Uri.file(path.join(workspaceFolder.uri.fsPath, 'pystructure-advice.md')),
      filters: { Markdown: ['md'] },
      saveLabel: 'Save Advice',
    });
    if (!target) {
      return;
    }

    try {
      const markdown = await runPyStructureCliText(cliScriptPath, workspaceFolder.uri.fsPath, '--markdown');
      await vscode.workspace.fs.writeFile(target, Buffer.from(markdown, 'utf-8'));
      const choice = await vscode.window.showInformationMessage(
        `PyStructure: 助言を保存しました (${path.basename(target.fsPath)})`,
        '開く'
      );
      if (choice === '開く') {
        await vscode.window.showTextDocument(target);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      outputChannel.appendLine(message);
      void vscode.window.showErrorMessage(`PyStructure: 助言の保存に失敗しました: ${message}`);
    }
  });

  context.subscriptions.push(analyzeCommand, highlightCommand, exportCommand, outputChannel, resultsView);
}

export function deactivate(): void {
  // VS Code が拡張を解放するときに呼ばれる。
}
