import * as vscode from 'vscode';

export type CliModule = {
  module_name: string;
};

export type CliPayload = {
  analysis: {
    root: string;
    modules: CliModule[];
  };
  graph: {
    nodes: unknown[];
    edges: unknown[];
  };
};

class ResultNode extends vscode.TreeItem {
  constructor(
    label: string,
    collapsibleState: vscode.TreeItemCollapsibleState,
    readonly children: ResultNode[] = [],
    description?: string
  ) {
    super(label, collapsibleState);
    this.description = description;
  }
}

export class ResultsViewProvider implements vscode.TreeDataProvider<ResultNode> {
  private readonly changeEmitter = new vscode.EventEmitter<void>();

  private latestResult: CliPayload | undefined;

  readonly onDidChangeTreeData = this.changeEmitter.event;

  setResult(result: CliPayload): void {
    this.latestResult = result;
    this.changeEmitter.fire();
  }

  getTreeItem(element: ResultNode): vscode.TreeItem {
    return element;
  }

  getChildren(element?: ResultNode): Thenable<ResultNode[]> {
    if (!this.latestResult) {
      if (element) {
        return Promise.resolve([]);
      }

      return Promise.resolve([
        new ResultNode('PyStructure', vscode.TreeItemCollapsibleState.None, [], '解析結果を待機しています'),
      ]);
    }

    if (!element) {
      return Promise.resolve([
        new ResultNode(
          'Analysis',
          vscode.TreeItemCollapsibleState.Expanded,
          [
            new ResultNode(`Root: ${this.latestResult.analysis.root}`, vscode.TreeItemCollapsibleState.None),
            new ResultNode(
              `Modules: ${this.latestResult.analysis.modules.length}`,
              vscode.TreeItemCollapsibleState.Expanded,
              this.latestResult.analysis.modules.map(
                (module) => new ResultNode(module.module_name, vscode.TreeItemCollapsibleState.None)
              )
            ),
            new ResultNode(`Graph nodes: ${this.latestResult.graph.nodes.length}`, vscode.TreeItemCollapsibleState.None),
            new ResultNode(`Graph edges: ${this.latestResult.graph.edges.length}`, vscode.TreeItemCollapsibleState.None),
          ]
        ),
      ]);
    }

    return Promise.resolve(element.children);
  }
}