# PyStructure

PyStructure は、Python プロジェクトの構造と依存関係を可視化するための静的解析コアです。

Python ソースを `ast` で解析し、次の情報を抽出します。

- ファイルとモジュール
- クラスと関数
- import 関係
- 後続の可視化に使うノードとエッジ

## 現在の実装状況

実装本体は `src/` 直下にフラットに配置しています。

- `src/cli.py`: CLI の入口
- `src/analyzer.py`: AST 解析とシンボル抽出
- `src/scanner.py`: ファイル探索とモジュール名の解決
- `src/import_resolver.py`: import の正規化と解決
- `src/graph.py`: 依存グラフの構築とシリアライズ
- `src/models.py`: 共通データクラス

現時点では `src/` 配下にパッケージディレクトリは置いていません。コアがまだ小さいうちは、この方が全体を見通しやすいためです。

## 目的

- 実行せず、静的解析のみを行う
- 標準ライブラリを優先し、特に `ast` を使う
- 責務を小さく分けて保守しやすくする
- 将来の PyCharm プラグイン UI に接続しやすくする

## 構成

- `src/cli.py`: CLI の入口
- `src/analyzer.py`: AST 解析とシンボル抽出
- `src/scanner.py`: ファイル探索とモジュール名の解決
- `src/import_resolver.py`: import の正規化と解決
- `src/graph.py`: 依存グラフの構築とシリアライズ
- `src/models.py`: 共通データクラス

## 実行方法

```bash
pystructure analyze path/to/project --json
```

新規クローン直後で未インストールの場合は、`src/` を Python の検索パスに追加するか、編集可能インストールを行ってください。

助言（問題・理由・改善案・根拠）を Markdown で出力するには `--markdown` を使います。

```bash
pystructure analyze path/to/project --markdown > advice.md
```

## 設定（除外ディレクトリ）

解析対象のプロジェクト直下に `.pystructure.json` を置くと、解析から除外するディレクトリを指定できます。`venv`、`.git`、`__pycache__` などは設定なしでも除外されます。

```json
{
  "exclude": ["generated", "vscode-extension/python"]
}
```

- `"generated"` のようにディレクトリ名だけを書くと、階層を問わず一致します。
- `"vscode-extension/python"` のように `/` を含めると、プロジェクト直下からのパスとして一致します。
- ファイルが無い、または形式が不正な場合は、警告をログに出して既定の設定で解析します。

## テスト

```bash
python -m unittest discover -s tests
```

## 補足

このリポジトリは、現時点では解析コアのひな形のみを含みます。ソースは見通しを重視して `src/` 直下にフラット配置しており、`build/`、`dist/`、`*.egg-info/` などの生成物は `.gitignore` で除外しています。

PyCharm 連携は、この解析コアの上に後から追加できます。
