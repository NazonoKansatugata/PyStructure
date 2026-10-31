# PyStructure PyCharm Plugin

PyStructure の解析結果を PyCharm から確認するプラグインです。

## 含まれるもの

- Tools メニューから実行できる `Analyze with PyStructure` アクション
- PyStructure CLI を `pystructure analyze <project> --json` で呼び出す実装
- Tool Window の解析結果ツリーと依存グラフ
- グラフの検索、ズーム、パン、ノード移動、隣接関係の強調表示、指標のツールチップ、再配置、ファイルを開く操作
- 助言の Markdown 保存。PyStructure Tool Window のタイトルバーの保存アイコン、または `Tools | Export PyStructure Advice as Markdown` から、問題・理由・改善案・根拠をファイルに保存できます
- 解析結果に基づく助言（循環参照・依存集中・読み進め方）の表示。助言を選択すると、グラフ上の対象モジュールを強調表示し、ダブルクリックで Dependency Graph タブへ切り替えます（`Esc` で解除）
- 成功/失敗を通知する通知グループ

## 前提

- `pystructure` コマンドが PATH 上で実行できること
- PyCharm 2026.2 系列（ビルド対象: 2026.2.4 / build 262.11879.98）
- JDK 17 以降（Gradle Wrapper は Gradle 9.7.0）

## 開発

プラグインのビルドや実行には Gradle Wrapper を使います。

```powershell
cd pycharm-plugin
.\gradlew.bat compileKotlin
.\gradlew.bat runIde
```

`platformVersion` は `gradle.properties` で指定します。PyCharmの新しい系列に対応する場合は、対象プラットフォームのバージョンと `build.gradle.kts` の `sinceBuild` / `untilBuild` を合わせて更新してください。

## ビルドとインストール

`pycharm-plugin` ディレクトリで次のコマンドを実行すると、配布用プラグインをビルドできます。

```powershell
.\gradlew.bat buildPlugin
```

プラグインパッケージは次の場所に生成されます。

```text
pycharm-plugin\build\distributions\pystructure-pycharm-0.3.0.zip
```

PyCharmで **Settings | Plugins** を開き、歯車メニューから **Install Plugin from Disk...** を選択して、生成されたZIPファイルを指定してください。インストール後、PyCharmを再起動します。

このZIPにはプラグイン本体と実行時依存ライブラリが含まれます。ZIPを展開したり、中のJARを個別にインストールしたりする必要はありません。

## 現在の状態

解析・結果ツリー・import依存グラフを利用できます。グラフにはモジュール間の `imports` エッジを表示し、ノードの色で循環依存、到達不能、エントリーポイントを示します。ノードをクリックすると隣接モジュールと関連するエッジを強調し、ホバーすると行数・サイズ・fan-in/out・深度を確認できます。「Re-layout」でグラフを再配置できます。ノードをダブルクリックすると対応するソースファイルを開きます。

グラフはネイティブな PyCharm UI で描画します。ノードの大きさは行数に比例し、色は status / package / depth から切り替えられます。検索・選択時は無関係なノードを減光し、Esc で選択と検索をクリアします。解析結果ツリーには件数、行番号、継承元を表示し、項目をダブルクリックすると対応するソース位置を開きます。Webview版にあるすべての視覚効果や配置アルゴリズムを共有するものではありません。
