import * as crypto from 'node:crypto';

import * as vscode from 'vscode';

import { CliPayload } from './resultsView';

export class GraphPanel {
  private static current: GraphPanel | undefined;

  private allowedPaths = new Set<string>();

  private constructor(
    private readonly panel: vscode.WebviewPanel,
    private payload: CliPayload
  ) {
    this.panel.onDidDispose(() => {
      GraphPanel.current = undefined;
    });
    this.panel.webview.onDidReceiveMessage((message: { type?: string; path?: string }) => {
      if (message.type === 'ready') {
        this.sendData();
      } else if (message.type === 'open' && typeof message.path === 'string') {
        void this.openFile(message.path);
      }
    });
  }

  static show(assetsRoot: vscode.Uri, payload: CliPayload): void {
    if (GraphPanel.current) {
      GraphPanel.current.update(payload);
      GraphPanel.current.panel.reveal(undefined, true);
      return;
    }

    const panel = vscode.window.createWebviewPanel('pystructureGraph', 'PyStructure Graph', vscode.ViewColumn.Beside, {
      enableScripts: true,
      retainContextWhenHidden: true,
      localResourceRoots: [assetsRoot],
    });
    const instance = new GraphPanel(panel, payload);
    GraphPanel.current = instance;
    panel.webview.html = instance.renderHtml(assetsRoot);
  }

  private update(payload: CliPayload): void {
    this.payload = payload;
    this.sendData();
  }

  private sendData(): void {
    this.allowedPaths = new Set(this.payload.analysis.modules.map((module) => module.path));
    void this.panel.webview.postMessage({ type: 'data', payload: this.payload });
  }

  private async openFile(filePath: string): Promise<void> {
    // webview からの入力なので、解析結果に含まれるファイルだけ開く。
    if (!this.allowedPaths.has(filePath)) {
      return;
    }

    const document = await vscode.workspace.openTextDocument(vscode.Uri.file(filePath));
    await vscode.window.showTextDocument(document, { viewColumn: vscode.ViewColumn.One, preview: true });
  }

  private renderHtml(assetsRoot: vscode.Uri): string {
    const webview = this.panel.webview;
    const nonce = crypto.randomBytes(16).toString('hex');
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(assetsRoot, 'graph.js'));
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(assetsRoot, 'graph.css'));

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';">
  <link rel="stylesheet" href="${styleUri}">
  <title>PyStructure Graph</title>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const graph = PyStructureGraph.mount(document.getElementById('root'), {
      onOpen: (node) => vscode.postMessage({ type: 'open', path: node.path }),
    });
    window.addEventListener('message', (event) => {
      if (event.data.type === 'data') {
        graph.setData(event.data.payload);
      }
    });
    vscode.postMessage({ type: 'ready' });
  </script>
</body>
</html>`;
  }
}
