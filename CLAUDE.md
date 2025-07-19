# Chrome自動操作ツール - 開発状況

## プロジェクト概要
AI chat applications（特にGenspark.ai）向けのChrome自動操作ツール。プロンプトを送信し、ストリーミング応答の完了を検出して、応答をMarkdownファイルに自動保存する。サーバー側エラーの自動検出・リトライ機能とGradio Web GUIを搭載。

## 現在の実装状況

### ✅ 完了済み機能
1. **基本的なChrome自動操作**
   - Seleniumによる自動ブラウザ制御
   - Mac M1/M2対応のChromeDriver設定
   - ユーザープロファイル保持によるログイン状態維持

2. **Genspark.ai向け特化機能**
   - 自動ナビゲーション (`https://www.genspark.ai/agents?type=moa_chat`)
   - テキスト入力フィールド自動検出
   - 送信ボタン検出（Enterキー送信対応）

3. **ストリーミング応答検出システム**
   - "Thinking..."インジケーター検出
   - コピーボタン出現による完了判定
   - プロンプト特定コピーボタン検出（古いコピーボタンを除外）
   - Stale element reference対策

4. **継続的プロンプト処理**
   - 無限ループでの複数プロンプト送信
   - 連番ファイル保存 (`output_001_YYYYMMDD_HHMMSS.md`)
   - quit/exit コマンドでの終了

5. **最新応答検出アルゴリズム**
   - `message-content-id` 属性による最新応答特定
   - プロンプト送信前後の応答数比較
   - 応答内容検証（キーワードマッチング）

6. **再生成エラー自動検出・リトライ機能**
   - 「応答を再生成」ボタンの自動検出
   - 最大20回の自動リトライ処理
   - 1-5秒のランダム待機時間
   - JavaScript強制クリック対応

7. **Gradio Web GUI インターフェース**
   - URLナビゲーション機能
   - プロンプト入力・送信
   - フォールバックメッセージ自動送信
   - リアルタイムステータス表示
   - Chrome持続性管理

### 🔧 最近修正した問題
1. **エラーメッセージ誤認識の修正**
   - 「応答の生成中にエラーが発生しま」をエラーメッセージとして正しく識別
   - エラー状態時のストリーミング処理を無効化
   - 60秒タイムアウトと15秒待機を回避

2. **フォールバック処理時のThinking状態除外**
   - `wait_for_streaming=False` 時の「Thinking...」要素を候補から除外
   - フォールバック処理での適切な応答要素選択
   - ストリーミングタイムアウトの防止

3. **連続フォールバック処理の実装**
   - 最大20回の連続フォールバック試行
   - ランダム待機時間（1-5秒）の追加
   - 詳細なリトライ進捗表示

4. **リトライ回数の可視化**
   - ログメッセージに「(X回目)」表示
   - デバッグしやすいリトライ追跡機能
   - GUI での進捗状況表示

### 📁 ファイル構成
```
web-automate/
├── main.py                 # メインプログラム（コアロジック）
├── gradio_gui.py          # Gradio Web GUI インターフェース
├── debug_regenerate.py    # 再生成ボタン検出デバッグツール
├── requirements.txt        # 依存関係（Gradio追加）
├── .gitignore             # Git除外設定
├── README.md              # インストール・使用方法
├── automation.log         # 実行ログ
├── outputs/               # 生成されたMarkdownファイル
│   ├── output_001_YYYYMMDD_HHMMSS.md
│   ├── output_002_YYYYMMDD_HHMMSS.md
│   └── ...
└── CLAUDE.md             # このファイル
```

### 🎯 主要クラス・メソッド

#### ChromeAutomationTool クラス（main.py）
- `launch_chrome()` - Chrome起動・Genspark.ai自動オープン
- `find_text_input()` - テキスト入力フィールド検出
- `find_submit_button()` - 送信ボタン検出
- `find_regenerate_button()` - 再生成ボタン検出・クリック
- `handle_regenerate_with_retry()` - 再生成リトライ処理（最大20回）
- `process_continuous_prompts()` - 継続的プロンプト処理ループ
- `process_single_prompt()` - 単一プロンプト処理
- `get_latest_message_content(wait_for_streaming=True)` - 最新応答取得
- `get_response_text()` - 応答テキスト取得（エラー検出付き）
- `wait_for_streaming_response_complete()` - ストリーミング完了待機
- `clean_response_text()` - 応答テキストクリーンアップ

#### AutomationGUI クラス（gradio_gui.py）
- `start_automation()` - GUI からの自動化開始
- `_run_automation()` - バックグラウンド自動化実行
- `stop_automation()` - 自動化停止・Chrome終了
- `get_status_update()` - リアルタイムステータス更新
- `get_response_update()` - 応答内容更新

### 🚀 使用方法

#### コマンドライン版
```bash
python main.py
```
1. Chrome自動起動・Genspark.ai自動オープン
2. ページ読み込み完了後Enterキー押下
3. プロンプト入力・送信・応答保存を繰り返し
4. `quit` または `exit` で終了

#### Web GUI版（推奨）
```bash
python gradio_gui.py
```
1. ブラウザで `http://127.0.0.1:7860` にアクセス
2. URL・プロンプト・フォールバックメッセージを設定
3. 「🚀 プロンプト送信」をクリック
4. リアルタイムでステータス・応答を確認
5. 「🛑 停止」でChrome終了

### 🛠️ 技術的な課題と解決策

#### 1. 再生成エラーの自動検出・処理
**課題**: サーバー側エラーで「応答を再生成」ボタンが表示される
**解決**: 
- XPath・CSS セレクターによる再生成ボタン検出
- JavaScript強制クリック（通常クリック・MouseEvent）
- 最大20回の自動リトライ・ランダム待機時間

#### 2. フォールバック処理の信頼性
**課題**: エラー時のフォールバックメッセージ送信とThinking状態の混在
**解決**:
- `wait_for_streaming=False` でThinking状態を除外
- エラーメッセージの正確な識別
- 連続フォールバック処理（最大20回）

#### 3. ストリーミングタイムアウトの回避
**課題**: エラー状態時の60秒タイムアウトと15秒待機
**解決**:
- エラー検出時のストリーミング処理無効化
- デッドコード除去による即座のフォールバック移行
- 適切な要素選択ロジック分離

#### 4. GUI とコアロジックの統合
**課題**: リアルタイム状態表示とバックグラウンド処理の同期
**解決**:
- Queue ベースのステータス・応答管理
- Chrome持続性によるセッション維持
- 詳細な進捗表示とエラーハンドリング

### ⚙️ 設定・環境
- **対象サイト**: Genspark.ai (`https://www.genspark.ai/agents?type=moa_chat`)
- **対応OS**: macOS (M1/M2), Linux, Windows
- **Python**: 3.8+
- **主要依存**: selenium==4.15.2, gradio>=4.0.0, webdriver-manager==4.0.1
- **GUI アクセス**: http://127.0.0.1:7860 (localhost のみ)

### 🔍 デバッグ・ログ
- `automation.log` に詳細ログ出力
- DEBUG レベルでDOM構造解析
- リトライ回数・進捗の可視化
- `debug_regenerate.py` で再生成ボタン検出テスト

### 📝 TODO（今後の改善予定）
- [ ] 他のAIチャットサイト対応
- [ ] 応答フォーマットのカスタマイズ
- [x] ~~エラー時の自動リトライ機能強化~~
- [x] ~~GUI インターフェース~~
- [ ] バッチ処理モード（複数プロンプト一括実行）
- [ ] 応答品質評価・フィルタリング機能

### 🎉 現在のステータス
**動作状況**: 完全機能実装完了。再生成エラー自動検出・リトライ、Gradio Web GUI、フォールバック処理まですべて実装済み。

**主要機能**:
- ✅ 基本的な自動化処理
- ✅ 再生成エラー自動検出・リトライ（最大20回）
- ✅ Gradio Web GUI インターフェース
- ✅ 連続フォールバック処理
- ✅ ストリーミングタイムアウト回避
- ✅ エラーメッセージ正確識別

**最新の改善**: フォールバック処理時のThinking状態除外、連続リトライ処理の強化、詳細なデバッグログ実装。

---
*Last updated: 2025-07-19*