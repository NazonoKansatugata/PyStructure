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

## 挙動

- `ast` を使った静的解析のみを行います
- 対象コードは実行しません
- 出力は `to_dict()` を持つ Python データクラスとして構造化しています
- テストは `tests/` にあり、`python -m unittest discover -s tests` で実行します

## リポジトリ整理

- `build/`、`dist/`、`*.egg-info/`、キャッシュ、coverage ファイルなどの生成物は `.gitignore` で除外しています
- これにより、ワークスペースはソースとドキュメントに集中できます