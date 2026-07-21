# PyStructure PyCharm Plugin Scaffold

これは PyStructure の PyCharm プラグイン最小 scaffold です。

## 含まれるもの

- Tools メニューから実行できる `Analyze with PyStructure` アクション
- PyStructure CLI を `pystructure analyze <project> --json` で呼び出す実装
- 解析結果と stderr を表示する PyCharm の Tool Window
- 成功/失敗を通知する通知グループ

## 前提

- `pystructure` コマンドが PATH 上で実行できること
- Gradle と IntelliJ Platform Plugin 環境が使えること

## 開発

```bash
# このフォルダで Gradle プロジェクトとして開く
# その後、IDE からプラグインを実行/デバッグする
```

## 状態

まだ最小実装です。結果の JSON を構造化してツリー表示する段階までは入れていません。
