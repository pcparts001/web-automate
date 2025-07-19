# Chrome自動操作ツール - 開発状況

## プロジェクト概要
AI chat applications（特にGenspark.ai）向けのChrome自動操作ツール。プロンプトを送信し、ストリーミング応答の完了を検出して、応答をMarkdownファイルに自動保存する。

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

### 🔧 最近修正した問題
1. **応答検出の精度向上**
   - 古い応答（Reply1）ではなく最新応答（Reply2）を保存
   - `get_latest_message_content()` メソッドによる確実な最新応答取得
   - プロンプト要素と応答要素の区別

2. **コピーボタン検出の改善**
   - 送信したプロンプト後に現れるコピーボタンのみを検出
   - `check_copy_button_after_current_prompt()` による精密な判定

3. **ストリーミング検出の強化**
   - 早期完了を防ぐための厳密な判定条件
   - 3回連続安定・3秒間隔チェック
   - 最低応答長50文字の要件

### 📁 ファイル構成
```
web-automate/
├── main.py                 # メインプログラム
├── requirements.txt        # 依存関係
├── README.md              # インストール・使用方法
├── automation.log         # 実行ログ
├── outputs/               # 生成されたMarkdownファイル
│   ├── output_001_YYYYMMDD_HHMMSS.md
│   ├── output_002_YYYYMMDD_HHMMSS.md
│   └── ...
└── CLAUDE.md             # このファイル
```

### 🎯 主要クラス・メソッド

#### ChromeAutomationTool クラス
- `launch_chrome()` - Chrome起動・Genspark.ai自動オープン
- `find_text_input()` - テキスト入力フィールド検出
- `find_submit_button()` - 送信ボタン検出
- `process_continuous_prompts()` - 継続的プロンプト処理ループ
- `process_single_prompt()` - 単一プロンプト処理
- `get_latest_message_content()` - 最新応答取得（message-content-id基準）
- `wait_for_streaming_response_complete()` - ストリーミング完了待機
- `check_copy_button_after_current_prompt()` - プロンプト後コピーボタン検出
- `clean_response_text()` - 応答テキストクリーンアップ

### 🚀 使用方法
```bash
python main.py
```
1. Chrome自動起動・Genspark.ai自動オープン
2. ページ読み込み完了後Enterキー押下
3. プロンプト入力・送信・応答保存を繰り返し
4. `quit` または `exit` で終了

### 🛠️ 技術的な課題と解決策

#### 1. ストリーミング応答検出
**課題**: AIの応答がリアルタイムで生成されるため、完了タイミングの検出が困難
**解決**: 
- "Thinking..."インジケーター監視
- コピーボタン出現検出
- テキスト安定性チェック（3回連続同一）

#### 2. Stale Element Reference
**課題**: DOMの動的変更によりWebElement参照が無効化
**解決**:
- 要素の再取得メカニズム
- 複数の識別方法（ID, class, xpath, selector）
- フォールバック検索機能

#### 3. 最新応答の特定
**課題**: 複数の応答が存在する中で最新のものを特定
**解決**:
- `message-content-id` 属性による確実な識別
- プロンプト送信前後の要素数比較
- 応答内容の検証

### ⚙️ 設定・環境
- **対象サイト**: Genspark.ai (`https://www.genspark.ai/agents?type=moa_chat`)
- **対応OS**: macOS (M1/M2), Linux, Windows
- **Python**: 3.8+
- **主要依存**: selenium==4.15.2, webdriver-manager==4.0.1

### 🔍 デバッグ・ログ
- `automation.log` に詳細ログ出力
- DEBUG レベルでDOM構造解析
- 要素検出過程の詳細追跡

### 📝 TODO（今後の改善予定）
- [ ] 他のAIチャットサイト対応
- [ ] 応答フォーマットのカスタマイズ
- [ ] エラー時の自動リトライ機能強化
- [ ] GUI インターフェース

### 🎉 現在のステータス
**動作状況**: 基本機能は完全動作。最新応答の正確な取得・保存まで実装完了。継続的なプロンプト処理が可能な状態。

**最終テスト結果**: Prompt2送信後、"塩と砂糖の甘さ比較"で始まる正しいReply2の保存を確認中。

---
*Last updated: 2025-07-19*