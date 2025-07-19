# Chrome自動操作ツール

MacのChromeブラウザを自動で操作し、特定のサイトのボタンを自動で押し、出力されたテキストを保存するツール。

## 機能

1. Chromeブラウザを自動オープン
2. 特定のプロンプトをテキストフィールドに入力し送信
3. エラーメッセージの検出と再試行
4. 出力テキストのMarkdown形式での保存

## 必要な環境

- Python 3.8+
- Chrome ブラウザ
- macOS（Mac M1/M2対応）

## インストール・セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. ChromeDriverのセットアップ

このツールは自動的にChromeDriverをダウンロードしますが、キャッシュの破損やバージョン問題が発生することがあります。その場合は手動インストールを推奨します。

#### 方法1: Homebrew（推奨）

```bash
# Homebrewでインストール
brew install chromedriver

# セキュリティ設定を解除
xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver
```

#### 方法2: 手動ダウンロード

1. Chromeのバージョンを確認：
   - Chromeブラウザで `chrome://version/` にアクセス
   - バージョン番号をメモ（例：138.0.7204.157）

2. ChromeDriverをダウンロード：
   - [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/) にアクセス
   - Mac ARM64用のChromeDriverをダウンロード
   - zipファイルを解凍

3. ChromeDriverを配置：
   ```bash
   # ダウンロードフォルダから移動（パスは実際のダウンロード場所に合わせて調整）
   sudo mv ~/Downloads/chromedriver-mac-arm64/chromedriver /usr/local/bin/
   sudo chmod +x /usr/local/bin/chromedriver
   ```

4. Gatekeeperの警告を解除：
   ```bash
   sudo xattr -d com.apple.quarantine /usr/local/bin/chromedriver
   ```

#### トラブルシューティング

キャッシュの破損が発生した場合：

```bash
# 破損したキャッシュをクリア
rm -rf ~/.wdm/drivers/chromedriver
```

## 使用方法

```bash
python main.py
```

1. プログラムが起動し、Chromeブラウザが自動で開きます
2. 手動で目的のサイト（ChatGPTなど）にアクセスします
3. Enterキーを押してプログラムに制御を渡します
4. 送信したいプロンプトを入力します
5. 自動でフォームに入力・送信され、結果がMarkdownファイルに保存されます

## 出力ファイル

生成された応答は `outputs/` ディレクトリに以下の形式で保存されます：

```
outputs/output_YYYYMMDD_HHMMSS.md
```

## 対応サイト

- ChatGPT
- Claude
- その他のテキスト入力フィールドと送信ボタンがあるサイト

## 注意事項

- 初回実行時はChromeDriverのダウンロードに時間がかかる場合があります
- サイトの構造変更により動作しない場合があります
- 利用規約に従ってご使用ください