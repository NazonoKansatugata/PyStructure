# PyStructure PyCharm Plugin

PyStructure の解析結果を PyCharm から確認するプラグインです。

## 含まれるもの

- Tools メニューから実行できる `Analyze with PyStructure` アクション
- PyStructure CLI を `pystructure analyze <project> --json` で呼び出す実装
- Tool Window の解析結果ツリーと依存グラフ
- グラフの検索、ズーム、パン、ノード移動、ファイルを開く操作
- 成功/失敗を通知する通知グループ

## 前提

- `pystructure` コマンドが PATH 上で実行できること
- PyCharm 2026.2 系列（ビルド対象: 2026.2.4 / build 262.11879.98）
- JDK 17 以降（Gradle Wrapper は Gradle 9.7.0）

## 開発

プラグインのビルドや実行には Gradle Wrapper を使います。

```powershell
.\gradlew.bat compileKotlin
.\gradlew.bat runIde
```

`platformVersion` は `gradle.properties` で指定します。PyCharmの新しい系列に対応する場合は、対象プラットフォームのバージョンと `build.gradle.kts` の `sinceBuild` / `untilBuild` を合わせて更新してください。

## 現在の状態

解析・結果ツリー・import依存グラフを利用できます。グラフにはモジュール間の `imports` エッジを表示し、ノードの色で循環依存、到達不能、エントリーポイントを示します。グラフをダブルクリックすると対応するソースファイルを開きます。

グラフはネイティブな PyCharm UI で描画します。Webview版にあるすべての視覚効果や配置アルゴリズムを共有するものではありません。
