# import_analyzer 仕様書

## 目的

`import_analyzer` は、Python モジュールから import 文を抽出し、構造化データへ正規化する役割を持つ。

## 責務

- AST ノードから `import` と `from ... import ...` を解析する。
- モジュール名、インポートされたシンボル、相対 import の階層、行番号を保持する。
- import の抽出と import 解決を分離する。

## 入力

- モジュールの Python AST。

## 出力

- module、names、level、行番号を含む import レコード群。

## 挙動

- 単純な `import x` は `module=None`、`names=("x", ...)` として保持する。
- `from pkg import a, b` はベースモジュール名と import 名を保持する。
- 後続の解決処理のために相対 import の深さを保持する。

## テスト観点

- 絶対 import と相対 import が混在していても正しく抽出されること。
- 複数の import 名が保持されること。
- 行番号が安定して記録されること。
