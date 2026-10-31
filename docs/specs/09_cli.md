# cli 仕様書

## 目的

`cli` は、プロジェクト解析のためのコマンドライン入口を提供する。

## 責務

- コマンドライン引数を解析する。
- 指定されたルートパスに対してプロジェクト解析を実行する。
- 人間可読なテキスト、JSON、Graphviz DOT、または助言の Markdown を出力する。

## 入力

- コマンドライン引数。

## 出力

- 終了ステータスコード。
- 標準出力に書き出されるテキスト、JSON、DOT、または Markdown。

## 挙動

- `analyze` コマンドを主な入口とする。
- `--json` によって構造化 JSON 出力（`analysis`、`graph`、`advice`）へ切り替える。
- `--graphviz` で Graphviz DOT、`--markdown` で助言（理由・対象・改善案・根拠）の Markdown へ切り替える。
- 解析対象直下の `.pystructure.json` の `exclude` を読み、除外ディレクトリを追加できる（不正な場合は警告のみで既定設定を使う）。
- 未知のコマンドは引数解析エラーとして失敗する。

## テスト観点

- 引数解析が analyze コマンドを受け付けること。
- JSON 出力に analysis、graph、advice が含まれること。
- Markdown 出力に理由・対象・改善案・根拠の節が含まれること。
