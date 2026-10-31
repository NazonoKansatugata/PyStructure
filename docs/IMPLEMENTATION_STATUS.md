# 実装状況

この文書は、PyStructure コア実装の現在の状態を記録します。

## 配置

- ソースコードは `src/` 直下にフラット配置しています
- 現在の実装レイアウトでは `src/pystructure/` パッケージディレクトリは使っていません
- CLI の入口は `src/cli.py` です
- コア解析は `src/analyzer.py` です
- ファイル探索は `src/scanner.py` です
- import 解決は `src/import_resolver.py` です
- グラフ構築は `src/graph.py` です
- 共通モデルは `src/models.py` です
- メトリクス（fan_in/fan_out、循環、エントリーポイント、depth）は `src/metrics.py` です
- 助言生成は `src/advisor.py` です（ルール: 循環参照、依存集中、巨大モジュール、到達不能、読み進め方）
- 出力は `src/exporter.py` です（テキスト、JSON、Graphviz、Markdown）
- 除外設定（`.pystructure.json`）の読み込みは `src/settings.py`、既定値と閾値は `src/config.py` です
- 公開 API は `src/api.py` です

## 助言機能

- 解析結果（事実）と助言を分離したルールベース実装です
- 助言は `rule_id`、`severity`、`title`、`reason`、`suggestions`、`targets`、`evidence` を持ちます
- 助言は目安であり、必ず修正が必要という意味ではありません
- VS Code 拡張と PyCharm プラグインは、CLI の JSON 出力の `advice` を表示し、Markdown 保存に対応しています

## 配布物

- VS Code 拡張: `vscode-extension/`（`.vsix`）
- PyCharm プラグイン: `pycharm-plugin/`（`.zip`、PyCharm 2026.2 系向け）
- 現在のバージョン: 0.3.0

## 挙動

- `ast` を使った静的解析のみを行います
- 対象コードは実行しません
- 出力は `to_dict()` を持つ Python データクラスとして構造化しています
- テストは `tests/` にあり、`python -m unittest discover -s tests` で実行します

## リポジトリ整理

- `build/`、`dist/`、`*.egg-info/`、キャッシュ、coverage ファイルなどの生成物は `.gitignore` で除外しています
- これにより、ワークスペースはソースとドキュメントに集中できます