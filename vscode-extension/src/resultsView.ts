import * as vscode from 'vscode';

export type CliModule = {
  module_name: string;
  imports: Array<{
    module: string | null;
    names: string[];
    bindings: Array<{ name: string; asname?: string | null }>;
    level: number;
    lineno: number;
  }>;
  classes: Array<{
    name: string;
    lineno: number;
    bases: string[];
    methods: Array<{ name: string; lineno: number; is_async: boolean; kind: string }>;
  }>;
  functions: Array<{ name: string; lineno: number; is_async: boolean; kind: string }>;
  calls: Array<{
    caller: string;
    callee: string;
    resolved_callee?: string | null;
    lineno: number;
  }>;
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

function toCallLabel(call: CliModule['calls'][number]): string {
  const target = call.resolved_callee ?? call.callee;
  return `${call.caller} -> ${target}`;
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
                (module) =>
                  new ResultNode(
                    module.module_name,
                    vscode.TreeItemCollapsibleState.Expanded,
                    [
                      new ResultNode(
                        `Imports: ${module.imports.length}`,
                        vscode.TreeItemCollapsibleState.Expanded,
                        module.imports.map((item) => {
                          const bindings = item.bindings
                            .map((binding) => (binding.asname ? `${binding.name} as ${binding.asname}` : binding.name))
                            .join(', ');
                          const source = item.module ?? '(absolute)';
                          return new ResultNode(`${source}: ${bindings}`, vscode.TreeItemCollapsibleState.None);
                        })
                      ),
                      new ResultNode(
                        `Classes: ${module.classes.length}`,
                        vscode.TreeItemCollapsibleState.Expanded,
                        module.classes.map(
                          (classInfo) =>
                            new ResultNode(
                              classInfo.name,
                              vscode.TreeItemCollapsibleState.Expanded,
                              classInfo.methods.map(
                                (method) =>
                                  new ResultNode(
                                    `${method.kind} ${method.name}`,
                                    vscode.TreeItemCollapsibleState.None,
                                    [],
                                    `line ${method.lineno}`
                                  )
                              ),
                              classInfo.bases.length > 0 ? `bases: ${classInfo.bases.join(', ')}` : undefined
                            )
                        )
                      ),
                      new ResultNode(
                        `Functions: ${module.functions.length}`,
                        vscode.TreeItemCollapsibleState.Expanded,
                        module.functions.map(
                          (functionInfo) =>
                            new ResultNode(
                              `${functionInfo.kind} ${functionInfo.name}`,
                              vscode.TreeItemCollapsibleState.None,
                              [],
                              `line ${functionInfo.lineno}`
                            )
                        )
                      ),
                      new ResultNode(`Calls: ${module.calls.length}`, vscode.TreeItemCollapsibleState.Expanded, module.calls.map((call) => {
                        return new ResultNode(
                          toCallLabel(call),
                          vscode.TreeItemCollapsibleState.None,
                          [],
                          `line ${call.lineno}`
                        );
                      })),
                    ]
                  )
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