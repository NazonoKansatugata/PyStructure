# PyStructure for VS Code

PyStructure は Python プロジェクトを静的解析し、モジュール一覧と依存グラフを表示する VS Code 拡張です。解析対象の Python コードは実行しません。

## 必要環境

- VS Code 1.90 以上
- Python 3.11 以上。`python`、`python3`、または Windows の `py -3` コマンドで起動できること
- VSIX を自分で作る場合は Node.js と npm

拡張パッケージには PyStructure の Python CLI とグラフ表示用ファイルが含まれます。別途 PyStructure を pip でインストールする必要はありません。

## VSIX の作成

リポジトリ内の `vscode-extension` ディレクトリで実行します。

Windows PowerShell で npm の実行ポリシーにより `npm.ps1` が拒否される場合は、`npm.cmd` を使ってください。

```powershell
cd vscode-extension
& 'C:\Program Files\nodejs\npm.cmd' install
& 'C:\Program Files\nodejs\npm.cmd' run package
```

他のターミナルでは通常の `npm install` と `npm run package` を使えます。VSIX は次の場所に生成されます。

```text
vscode-extension/pystructure-vscode-0.3.0.vsix
```

`package` スクリプトは拡張をコンパイルし、共有 Webview ファイルと Python CLI を拡張内にコピーしてから VSIX を作成します。これらのコピー先は生成物なので、リポジトリにはコミットしません。

## VS Code へのインストール

### VS Code の画面から

1. VS Code の「拡張機能」ビューを開きます。
2. 拡張機能ビュー右上の `...` メニューから「VSIX からのインストール」を選びます。
3. `pystructure-vscode-0.3.0.vsix` を選択します。
4. インストール後、VS Code を再読み込みします。

### コマンドから

リポジトリのルートで実行します。

```powershell
code --install-extension .\vscode-extension\pystructure-vscode-0.3.0.vsix
```

同じバージョンを入れ直す場合は `--force` を付けます。

```powershell
code --install-extension .\vscode-extension\pystructure-vscode-0.3.0.vsix --force
```

## 使い方

1. 解析したい Python プロジェクトのフォルダーを VS Code で開きます。
2. `Ctrl+Shift+P`（macOS は `Cmd+Shift+P`）でコマンドパレットを開きます。
3. `PyStructure: Analyze Workspace` を実行します。

このコマンド1つで、Explorer の `PyStructure Results` に解析結果をツリー表示し、依存グラフのパネルも開きます。

ツリーの先頭の `Advice` には、解析結果に基づく助言（問題の理由・改善案・対象）が表示されます。現在は循環参照を検出します。助言をクリックすると、依存グラフ上の対象モジュールが強調表示されます（`Esc` で解除）。助言はルールに基づく目安であり、必ず修正が必要という意味ではありません。

助言は Markdown ファイルとして保存できます。PyStructure Results ビューのタイトルバーにある保存アイコン、またはコマンドパレットの `PyStructure: Export Advice as Markdown` を使います。

グラフでは、ノードのドラッグで位置調整、背景ドラッグで移動、ホイールでズームできます。ノードをクリックすると隣接モジュールを強調表示し、ホバーすると行数・依存数・深度などを表示します。ダブルクリックすると対応する Python ファイルを開きます。検索、色分け、`Fit`、`Re-layout` も利用できます。

現在の拡張は、開いているワークスペースの先頭フォルダーを解析対象にします。

## 更新

新しいコードから `npm run package` で VSIX を作成し、同じ手順で再インストールします。コマンドで更新する場合は `--force` を付けてください。

## トラブルシューティング

- **Python が起動できない**: VS Code を起動した環境から `python --version` または `py -3 --version` が実行できるか確認します。必要なバージョンは Python 3.11 以上です。
- **解析に失敗する**: VS Code の「出力」ビューで `PyStructure` チャンネルを選び、CLI のエラーと `stderr` を確認します。
- **グラフが表示されない**: `PyStructure: Analyze Workspace` を再実行し、`PyStructure` 出力チャンネルに解析エラーがないか確認します。
- **起動時に NLS や Node.js の警告が出る**: VS Code 本体由来の警告であれば、それだけで PyStructure の解析失敗を意味するものではありません。上記の出力チャンネルを確認してください。

## 開発者向け

```powershell
cd vscode-extension
npm install
npm run compile
```

VS Code で `vscode-extension` を開き、「実行とデバッグ」から `Run Extension` を起動すると、Extension Development Host で動作確認できます。

## 配布に関する注意

ローカルでの VSIX 作成ではライセンスファイルの確認をスキップします。Marketplace で公開する前に、プロジェクトのライセンスを決定して manifest とライセンスファイルを整えてください。
