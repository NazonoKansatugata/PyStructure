# PyStructure プロジェクト規約 (AI 向け CLAUDE.md)

> このファイルは PyStructure 専用のプロジェクト規約です。
> `Code-Grimoire/` は参照用の既存実装であり、読み取り専用です。

---

# 1. プロジェクト概要

PyStructure は、Pythonプロジェクトの構造を静的解析し、ファイル・モジュール・クラス・関数・依存関係を可視化するツールです。

最終的には PyCharm プラグインとして動作させることを目標とします。

解析機能（Core）とIDE連携機能（Plugin）は分離して実装し、解析コアはCLIや他IDEからも再利用可能なライブラリとして設計します。

---

# 2. 開発方針

- Pythonで書かれたプロジェクトを解析対象とする
- 静的解析のみを扱う（対象コードは実行しない）
- Python標準ライブラリを優先して利用する
- ASTを中心とした解析を行う
- 各機能は責務ごとに分割し、保守性・拡張性を重視する
- 依存関係はグラフ構造として管理する
- UIと解析ロジックを分離する

---

# 3. 参照資料の扱い

- `Code-Grimoire/` は既存実装の参考資料
- 参照元のコードは編集しない
- 実装をそのままコピーしない
- 判断に迷った場合は PyStructure の設計を優先する

---

# 4. ディレクトリ構成

```
src/
    scanner.py              # ファイル探索・モジュール名解決

    analyzer/
        __init__.py
        base.py             # Analyzer基底クラス
        import_analyzer.py
        class_analyzer.py
        function_analyzer.py
        call_analyzer.py

    resolver/
        import_resolver.py

    graph/
        builder.py

    exporter/
        json_exporter.py
        graphviz_exporter.py

    models/
        node.py
        edge.py
        symbol.py
        project.py

    config.py

    cli.py

tests/
```

---

# 5. 実装ルール

## AST解析

ソースコード解析は原則 `ast` を利用すること。

正規表現や文字列検索は補助用途のみとし、
構文解析の代替として使用しない。

---

## 責務

1クラス1責務を基本とする。

新しい解析対象が増える場合は既存クラスへ詰め込まず、
Analyzerを追加する。

例

- ImportAnalyzer
- ClassAnalyzer
- FunctionAnalyzer
- CallAnalyzer

---

## データモデル

解析結果は構造化されたPythonオブジェクトとして保持する。

基本モデル

- Project
- Module
- Symbol
- Node
- Edge

---

## グラフ

依存関係はNodeとEdgeで表現する。

Node例

- File
- Module
- Class
- Function

Edge例

- import
- call
- inherit
- use

---

## エクスポート

グラフ出力はExporter層で行う。

例

- JSON
- Graphviz

将来的にMermaidやCytoscapeなどを追加できる設計にする。

---

## 型

公開APIには型ヒントを付与する。

データモデルには `dataclasses` を積極的に利用する。

---

## ログ

`print()` は使用しない。

デバッグ・情報出力には `logging` を利用する。

---

## 設定

除外ディレクトリ等は `config.py` に集約する。

例

- venv
- .git
- __pycache__
- .pytest_cache

---

# 6. 開発手順

以下の順番で実装を進める。

1. scanner
2. import解析
3. class解析
4. function解析
5. call解析
6. import解決
7. グラフ生成
8. Exporter
9. CLI
10. PyCharm Plugin

各段階で動作確認とテストを行う。

---

# 7. テスト

変更後は可能な限りユニットテストを実行する。

```
python -m unittest discover -s tests
```

解析ロジックを変更した場合は、
最小の再現テストを追加する。

---

# 8. ドキュメント

README.md

- 利用方法
- インストール
- 概要

CLAUDE.md

- 実装ルール
- アーキテクチャ
- AIへの指示

実装判断は CLAUDE.md を優先する。

---