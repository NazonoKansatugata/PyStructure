# PyStructure VS Code Extension Scaffold

これは PyStructure の VS Code 拡張の最小 scaffold です。

## 含まれるもの

- `pystructure.analyzeWorkspace` コマンド
- 拡張ホスト起動用の `launch.json`
- TypeScript のビルド設定

## 状態

現時点では解析コアとの連携は行っていません。まずは VS Code 拡張の起動とコマンド登録だけを確認できる最小構成です。

## 開発

```bash
npm install
npm run compile
```

VS Code から `Run Extension` を起動すると、拡張ホスト内でコマンドを確認できます。
