#!/usr/bin/env python3
"""
Chrome自動操作ツール
MacのChromeブラウザを自動で操作し、特定のサイトのボタンを自動で押し、
出力されたテキストを保存する
"""

import time
import logging
import os
import platform
import random
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class ChromeAutomationTool:
    """Chrome自動操作ツールクラス"""
    
    def __init__(self, debug=True):
        """初期化"""
        self.driver = None
        self.wait = None
        self.debug = debug
        self.prompt_counter = 0  # プロンプトカウンター
        self.existing_response_count = 0  # プロンプト送信前の既存応答数
        self.existing_copy_button_count = 0  # プロンプト送信前の既存コピーボタン数
        self.current_retry_count = 0  # 現在のリトライ回数
        self.max_regenerate_retries = 5  # 最大リトライ回数
        self.original_user_prompt = ""  # ユーザーが最初に送信したプロンプト（フォールバック時の区別用）
        self.setup_logging()
    
    def mask_text_for_debug(self, text, max_preview=6):
        """テキストをデバッグ用にマスキング（プライバシー保護強化）"""
        if not text:
            return "None"
        
        text = str(text).strip()
        if len(text) <= max_preview:
            # 短いテキストは全体を表示
            return f"[{len(text)}文字] '{text}'"
        else:
            # 長いテキストは先頭6文字のみ表示
            start = text[:max_preview]
            return f"[{len(text)}文字] '{start}...(({len(text) - max_preview}文字省略))'"
        
    def setup_logging(self):
        """ログ設定"""
        log_level = logging.DEBUG if self.debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('automation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def launch_chrome(self):
        """Chromeブラウザを起動"""
        try:
            # プラットフォーム情報を詳細にログ出力
            system = platform.system()
            machine = platform.machine()
            release = platform.release()
            version = platform.version()
            
            self.logger.info(f"=== プラットフォーム情報 ===")
            self.logger.info(f"システム: {system}")
            self.logger.info(f"アーキテクチャ: {machine}")
            self.logger.info(f"リリース: {release}")
            self.logger.info(f"バージョン: {version}")
            self.logger.info(f"Pythonバージョン: {platform.python_version()}")
            
            chrome_options = Options()
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # ユーザープロファイルディレクトリを設定してログイン状態を保持
            profile_dir = Path.home() / ".chrome_automation_profile"
            profile_dir.mkdir(exist_ok=True)
            chrome_options.add_argument(f"--user-data-dir={profile_dir}")
            
            # プロファイル名を指定
            chrome_options.add_argument("--profile-directory=AutomationProfile")
            
            self.logger.info(f"Chromeプロファイルディレクトリ: {profile_dir}")
            self.logger.info("ログイン状態は次回起動時も保持されます")
            
            # webdriver-managerのバージョンを確認
            try:
                import webdriver_manager
                self.logger.info(f"webdriver-manager バージョン: {webdriver_manager.__version__}")
            except:
                self.logger.warning("webdriver-managerバージョンが取得できませんでした")
            
            # ChromeDriverのパスを取得（手動インストール優先）
            chrome_driver_path = None
            
            # 1. 手動インストールされたChromeDriverを確認
            manual_paths = [
                "/usr/local/bin/chromedriver",
                "/opt/homebrew/bin/chromedriver",
                "/usr/bin/chromedriver"
            ]
            
            for path in manual_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    chrome_driver_path = path
                    self.logger.info(f"手動インストールされたChromeDriverを使用: {chrome_driver_path}")
                    break
            
            # 2. 手動インストールが見つからない場合はwebdriver-managerを使用
            if not chrome_driver_path:
                self.logger.info("ChromeDriverをダウンロード中...")
                
                try:
                    # 新しいバージョンのwebdriver-managerを試す
                    if system == "Darwin" and machine == "arm64":
                        self.logger.info("Mac M1/M2用のChromeDriverを取得します")
                        chrome_driver_path = ChromeDriverManager(os_type="mac-arm64").install()
                    elif system == "Darwin":
                        self.logger.info("Intel Mac用のChromeDriverを取得します")
                        chrome_driver_path = ChromeDriverManager(os_type="mac64").install()
                    elif system == "Linux":
                        self.logger.info("Linux用のChromeDriverを取得します")
                        chrome_driver_path = ChromeDriverManager(os_type="linux64").install()
                    else:
                        self.logger.info("自動検出でChromeDriverを取得します")
                        chrome_driver_path = ChromeDriverManager().install()
                        
                except TypeError as e:
                    # 古いバージョンのwebdriver-managerの場合
                    self.logger.warning(f"os_typeパラメータが使用できません: {e}")
                    self.logger.info("互換性モードでChromeDriverを取得します")
                    chrome_driver_path = ChromeDriverManager().install()
            
            self.logger.info(f"ChromeDriverManagerが返したパス: {chrome_driver_path}")
            
            # ChromeDriverの実際の実行ファイルパスを探す
            
            driver_path = Path(chrome_driver_path)
            self.logger.info(f"パスの詳細: {driver_path}")
            self.logger.info(f"ファイルが存在: {driver_path.exists()}")
            self.logger.info(f"実行可能: {os.access(driver_path, os.X_OK)}")
            
            # 正しいChromeDriver実行ファイルを探す
            if driver_path.name == "THIRD_PARTY_NOTICES.chromedriver" or not os.access(driver_path, os.X_OK):
                # 親ディレクトリでchromedriver実行ファイルを探す
                parent_dir = driver_path.parent
                self.logger.info(f"親ディレクトリを検索: {parent_dir}")
                
                possible_names = ["chromedriver", "chromedriver.exe"]
                actual_driver_path = None
                
                for name in possible_names:
                    candidate = parent_dir / name
                    self.logger.info(f"候補ファイルをチェック: {candidate}")
                    if candidate.exists() and os.access(candidate, os.X_OK):
                        actual_driver_path = candidate
                        self.logger.info(f"実行可能なChromeDriverを発見: {actual_driver_path}")
                        break
                
                if actual_driver_path:
                    chrome_driver_path = str(actual_driver_path)
                else:
                    # 再帰的に検索
                    self.logger.info("再帰的にChromeDriverを検索中...")
                    for file_path in parent_dir.rglob("chromedriver*"):
                        if file_path.is_file() and os.access(file_path, os.X_OK):
                            if "THIRD_PARTY" not in file_path.name:
                                chrome_driver_path = str(file_path)
                                self.logger.info(f"再帰検索で発見: {chrome_driver_path}")
                                break
            
            self.logger.info(f"最終的なChromeDriverパス: {chrome_driver_path}")
            
            service = Service(chrome_driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 10)
            
            # 自動的にGenspark.aiのチャットページを開く
            target_url = "https://www.genspark.ai/agents?type=moa_chat"
            self.logger.info(f"Genspark.aiチャットページを開いています: {target_url}")
            self.driver.get(target_url)
            
            self.logger.info("Chromeブラウザを起動しました")
            return True
            
        except Exception as e:
            self.logger.error(f"Chromeブラウザの起動に失敗: {e}")
            self.logger.error(f"エラータイプ: {type(e).__name__}")
            import traceback
            self.logger.error(f"詳細なエラー情報:\n{traceback.format_exc()}")
            return False
    
    def wait_for_user_navigation(self):
        """ユーザーがページの準備完了を確認するまで待機"""
        current_url = self.driver.current_url
        self.logger.info(f"現在のURL: {current_url}")
        
        print("\nGenspark.aiチャットページが開きました。")
        print("ページが完全に読み込まれたらEnterキーを押してください: ")
        input()
        
    def find_text_input(self):
        """テキスト入力フィールドを探す（実際の構造に基づく）"""
        selectors = [
            # 実際の構造に完全対応
            "textarea[name='query'].search-input",
            "textarea.search-input",
            "textarea[name='query']",
            "textarea[placeholder='Message']",
            # フォールバック
            "textarea",
            "input[type='text']",
            "[contenteditable='true']"
        ]
        
        for selector in selectors:
            try:
                element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                self.logger.debug(f"テキスト入力フィールドを発見: {selector}")
                return element
            except TimeoutException:
                continue
                
        self.logger.warning("テキスト入力フィールドが見つかりません")
        return None
    
    def find_submit_button(self):
        """送信ボタンを探す（デバッグ強化版）"""
        self.logger.info("=== 送信ボタン検索開始 ===")
        
        # --- 新しい戦略：textareaを基準に探す ---
        try:
            # まずテキスト入力フィールドを見つける
            text_input = self.find_text_input()
            if text_input:
                self.logger.info("テキスト入力フィールドを基準に送信ボタンを検索します")
                
                # 親要素をいくつか遡りながら、その中にボタンがないか探す
                parent = text_input
                for i in range(3): # 3階層上まで見る
                    # 兄弟要素にボタンがないか探す (SVGアイコンなどを含む)
                    # 一般的に送信ボタンはdivやbuttonタグで、特定のクラスやSVGを持つ
                    sibling_selectors = [
                        "./following-sibling::button",
                        "./following-sibling::div[contains(@class, 'send') or contains(@class, 'submit')]",
                        "./following-sibling::div//button",
                        "./following-sibling::*[//svg]" # SVGを持つ兄弟要素
                    ]
                    for selector in sibling_selectors:
                        try:
                            sibling_button = parent.find_element(By.XPATH, selector)
                            if sibling_button.is_displayed() and sibling_button.is_enabled():
                                outer_html = sibling_button.get_attribute('outerHTML')
                                self.logger.info(f"✓ textareaの兄弟要素として送信ボタンを発見 (セレクター: {selector})")
                                self.logger.debug(f"  [HTML]: {outer_html}")
                                return sibling_button
                        except NoSuchElementException:
                            continue
                    
                    # 親要素に移動
                    parent = parent.find_element(By.XPATH, "..")

        except Exception as e:
            self.logger.error(f"textarea基準のボタン検索でエラー: {e}")
        
        self.logger.info("--- 従来の検索方法にフォールバック ---")

        # 一般的なボタンセレクター
        selectors = [
            "button[type='submit']",
            "button[aria-label*='Send']", # アクセシビリティ属性
            "button[aria-label*='送信']",
            "input[type='submit']",
            ".submit-button",
            ".send-button"
        ]
        
        # テキストベースのボタン検索
        text_searches = [
            "送信", "生成", "実行", "Send", "Submit", "Generate", "Run", "Ask", "Chat"
        ]
        
        # まず一般的なセレクターを試す
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.is_enabled():
                    outer_html = element.get_attribute('outerHTML')
                    self.logger.info(f"✓ 送信ボタンを発見 (セレクター: {selector})")
                    self.logger.debug(f"  [HTML]: {outer_html}")
                    return element
            except NoSuchElementException:
                continue
        
        # テキストベースで検索
        for text in text_searches:
            try:
                element = self.driver.find_element(By.XPATH, f"//button[contains(text(), '{text}')]")
                if element.is_displayed() and element.is_enabled():
                    outer_html = element.get_attribute('outerHTML')
                    self.logger.info(f"✓ 送信ボタンを発見 (テキスト: {text})")
                    self.logger.debug(f"  [HTML]: {outer_html}")
                    return element
            except NoSuchElementException:
                continue
        
        # より広範囲な検索 - すべてのボタンをチェック
        try:
            self.logger.info("すべてのボタンを検索して適切なものを探します...")
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                if not (button.is_displayed() and button.is_enabled()):
                    continue

                button_text = button.text.strip().lower()
                button_classes = button.get_attribute("class") or ""
                button_id = button.get_attribute("id") or ""
                
                # ボタンの詳細をログ出力
                self.logger.debug(f"ボタン発見 - テキスト: '{button_text}', クラス: '{button_classes}', ID: '{button_id}'")
                
                # 送信系のキーワードをチェック
                submit_keywords = ["send", "submit", "chat", "ask", "generate", "run", "送信", "生成", "実行"]
                if any(keyword in button_text for keyword in submit_keywords) or \
                   any(keyword in button_classes.lower() for keyword in submit_keywords) or \
                   any(keyword in button_id.lower() for keyword in submit_keywords):
                    outer_html = button.get_attribute('outerHTML')
                    self.logger.info(f"✓ 適切な送信ボタンを発見: テキスト='{button_text}', クラス='{button_classes}'")
                    self.logger.debug(f"  [HTML]: {outer_html}")
                    return button
                    
            # Enterキーでの送信を試すため、Noneではなく代替手段を提供
            self.logger.warning("明確な送信ボタンが見つかりません。Enterキー送信を試します。")
            return "ENTER_KEY"  # 特別な値を返す
            
        except Exception as e:
            self.logger.error(f"ボタン検索中にエラー: {e}")
                
        self.logger.warning("送信ボタンが見つかりません")
        return None
    
    def debug_page_structure(self):
        """ページ構造をデバッグ出力（トラブルシューティング用）"""
        try:
            self.logger.info("=== ページ構造デバッグ ===")
            
            # ページタイトルとURL
            self.logger.info(f"URL: {self.driver.current_url}")
            self.logger.info(f"タイトル: {self.driver.title}")
            
            # 最近追加された要素（テキストを持つ）
            elements_with_text = self.driver.find_elements(By.XPATH, "//*[string-length(text()) > 20]")
            self.logger.info(f"テキストを持つ要素数: {len(elements_with_text)}")
            
            # 最新の10個の要素を表示
            for i, element in enumerate(elements_with_text[-10:]):
                try:
                    tag = element.tag_name
                    class_attr = element.get_attribute("class") or ""
                    id_attr = element.get_attribute("id") or ""
                    text_preview = element.text.strip()[:100] + "..." if len(element.text.strip()) > 100 else element.text.strip()
                    
                    self.logger.info(f"要素 {i+1}: <{tag}> class='{class_attr}' id='{id_attr}' テキスト='{text_preview}'")
                except:
                    continue
                    
        except Exception as e:
            self.logger.error(f"ページ構造デバッグエラー: {e}")

    def check_for_error_message(self):
        """エラーメッセージをチェック"""
        error_selectors = [
            "//*[contains(text(), '応答の生成中にエラーが発生しました')]",
            "//*[contains(text(), 'エラーが発生しました')]",
            ".error-message",
            ".alert-error"
        ]
        
        for selector in error_selectors:
            try:
                if selector.startswith("//"):
                    element = self.driver.find_element(By.XPATH, selector)
                else:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                if element.is_displayed():
                    self.logger.warning(f"エラーメッセージを検出: {element.text}")
                    return True
            except NoSuchElementException:
                continue
                
        return False
    
    def is_thinking_state(self, text, context=""):
        """
        Thinking状態を判定する統一メソッド
        
        Args:
            text (str): 判定対象のテキスト
            context (str): 呼び出し元の識別用（ログ出力で使用）
            
        Returns:
            bool: Thinking状態の場合True
        """
        if not text:
            return False
        
        thinking_indicators = ['thinking', '█']
        text_lower = text.lower()
        
        matched_indicators = [indicator for indicator in thinking_indicators if indicator in text_lower]
        
        if matched_indicators:
            context_info = f"[{context}] " if context else ""
            self.logger.info(f"{context_info}Thinking状態検出: マッチしたキーワード = {matched_indicators}")
            return True
        else:
            if context:
                self.logger.debug(f"[{context}] Thinking状態未検出")
            return False
    
    def find_regenerate_button(self):
        """応答を再生成ボタンを探す（軽量版と同じAND条件ロジック使用）"""
        # グローバルカウンターを初期化（なければ）
        if not hasattr(self, '_regenerate_button_call_count'):
            self._regenerate_button_call_count = 0
        self._regenerate_button_call_count += 1
        
        self.logger.info(f"=== 再生成ボタン検索開始 (呼び出し{self._regenerate_button_call_count}回目) ===")
        
        try:
            # 軽量版と同じAND条件ロジックを使用
            # 条件1: 「応答を再生成」テキストを含むdiv要素
            regenerate_divs = self.driver.find_elements(By.XPATH, "//div[contains(text(), '応答を再生成')]")
            self.logger.info(f"条件1チェック: 「応答を再生成」テキストを含むdiv = {len(regenerate_divs)}個")
            
            # 条件2: div.buttonクラス要素
            button_divs = self.driver.find_elements(By.CSS_SELECTOR, "div.button")
            self.logger.info(f"条件2チェック: div.buttonクラス要素 = {len(button_divs)}個")
            
            # AND条件: 両方の条件を満たす要素を探す
            for regenerate_div in regenerate_divs:
                if regenerate_div.is_displayed():
                    for button_div in button_divs:
                        if button_div.is_displayed() and regenerate_div == button_div:
                            self.logger.info(f"✅ AND条件で再生成ボタン検出: 「応答を再生成」テキスト含むdiv.button要素")
                            self.logger.info("=== 再生成ボタン検出終了（成功）===")
                            return regenerate_div
                            
            # 個別条件での検出状況をログ出力
            displayed_regenerate = [d for d in regenerate_divs if d.is_displayed()]
            displayed_buttons = [d for d in button_divs if d.is_displayed()]
            
            self.logger.info(f"表示中の「応答を再生成」div: {len(displayed_regenerate)}個")
            self.logger.info(f"表示中のdiv.button: {len(displayed_buttons)}個")
            self.logger.info(f"AND条件を満たす要素: 0個")
            
        except Exception as e:
            self.logger.warning(f"再生成ボタン検索エラー: {e}")
                
        self.logger.warning(f"再生成ボタンが見つかりません (呼び出し{self._regenerate_button_call_count}回目)")
        self.logger.info("=== 再生成ボタン検出終了（未検出）===")
        return None

    def check_regenerate_button_lightweight(self):
        """軽量版再生成ボタンチェック（ストリーミング監視用）"""
        try:
            # 条件1: 「応答を再生成」テキストを含むdiv要素
            regenerate_divs = self.driver.find_elements(By.XPATH, "//div[contains(text(), '応答を再生成')]")
            self.logger.debug(f"条件1チェック: 「応答を再生成」テキストを含むdiv = {len(regenerate_divs)}個")
            
            # 条件2: div.buttonクラス要素
            button_divs = self.driver.find_elements(By.CSS_SELECTOR, "div.button")
            self.logger.debug(f"条件2チェック: div.buttonクラス要素 = {len(button_divs)}個")
            
            # AND条件: 両方の条件を満たす要素を探す
            for regenerate_div in regenerate_divs:
                if regenerate_div.is_displayed():
                    for button_div in button_divs:
                        if button_div.is_displayed() and regenerate_div == button_div:
                            self.logger.info(f"✅ AND条件で再生成ボタン検出: 「応答を再生成」テキスト含むdiv.button要素")
                            return True
                            
            # 個別条件での検出状況をログ出力
            displayed_regenerate = [d for d in regenerate_divs if d.is_displayed()]
            displayed_buttons = [d for d in button_divs if d.is_displayed()]
            
            self.logger.debug(f"表示中の「応答を再生成」div: {len(displayed_regenerate)}個")
            self.logger.debug(f"表示中のdiv.button: {len(displayed_buttons)}個")
            self.logger.debug(f"AND条件を満たす要素: 0個")
            
            return False
        except Exception as e:
            self.logger.debug(f"軽量版再生成ボタンチェックエラー: {e}")
            return False

    def handle_regenerate_with_retry(self, max_retries=5):
        """再生成ボタンの自動リトライ処理"""
        self.logger.info("=== 再生成ボタン自動リトライ処理開始 ===")
        self.current_retry_count = 0
        
        while self.current_retry_count < max_retries:
            self.logger.info(f"リトライループ {self.current_retry_count + 1}/{max_retries} を開始")
            
            # 再生成ボタンが表示されているかチェック
            regenerate_button = self.find_regenerate_button()
            
            if not regenerate_button:
                # 再生成ボタンがない場合は正常な応答が生成されたと判断
                self.logger.info("再生成ボタンが見つからないため、正常な応答と判断します")
                return True
                
            self.current_retry_count += 1
            self.logger.warning(f"再生成ボタンを検出しました。リトライ {self.current_retry_count}/{max_retries}")
            
            # ランダムな待機時間（1-5秒）
            wait_time = random.uniform(1, 5)
            self.logger.info(f"ランダム待機: {wait_time:.1f}秒")
            time.sleep(wait_time)
            
            try:
                # まず通常のクリックを試す
                success = False
                try:
                    regenerate_button.click()
                    self.logger.info(f"通常クリックで再生成ボタンをクリックしました (試行 {self.current_retry_count})")
                    success = True
                except Exception as click_error:
                    self.logger.warning(f"通常クリック失敗: {click_error}")
                    
                    # JavaScript クリックを試す
                    try:
                        self.driver.execute_script("arguments[0].click();", regenerate_button)
                        self.logger.info(f"JavaScriptクリックで再生成ボタンをクリックしました (試行 {self.current_retry_count})")
                        success = True
                    except Exception as js_error:
                        self.logger.error(f"JavaScriptクリック失敗: {js_error}")
                        
                        # さらに強制的なクリックを試す
                        try:
                            # 要素にフォーカスを当ててからクリック
                            self.driver.execute_script("arguments[0].focus();", regenerate_button)
                            self.driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));", regenerate_button)
                            self.logger.info(f"強制イベントで再生成ボタンをクリックしました (試行 {self.current_retry_count})")
                            success = True
                        except Exception as force_error:
                            self.logger.error(f"強制クリック失敗: {force_error}")
                
                if success:
                    # クリック後、少し待機して新しい応答の生成を待つ
                    time.sleep(3)
                else:
                    self.logger.error(f"すべてのクリック方法が失敗しました (試行 {self.current_retry_count})")
                    continue
                
            except Exception as e:
                self.logger.error(f"再生成ボタンクリック処理中にエラー: {e}")
                # エラーでもリトライを続行
                continue
        
        # 最大リトライ回数に達した場合
        self.logger.error(f"再生成ボタンが{max_retries}回連続で表示されました。サーバーに問題がある可能性があります。")
        print(f"\n❌ エラー: 再生成ボタンが{max_retries}回連続で表示されました。")
        print("サーバー側に問題がある可能性があります。しばらく時間をおいてから再試行してください。")
        print("ツールを終了します。")
        return False
    
    def wait_for_streaming_response_complete(self, response_element_selector, timeout=120):
        """ストリーミング応答が完了するまで待機（Stale Element対策）"""
        self.logger.info("ストリーミング応答の完了を待機中...")
        
        previous_text = ""
        stable_count = 0
        required_stable_count = 3  # 3回連続でテキストが変わらなければ完了と判定
        check_interval = 3  # 3秒間隔でチェック（少し長めに）
        max_checks = timeout // check_interval
        minimum_response_length = 50  # 最低限の応答長
        
        # 要素を特定するための情報を保存
        element_info = {
            'tag': None,
            'class': None,
            'id': None,
            'xpath': None
        }
        
        # 初回要素情報を取得
        try:
            if isinstance(response_element_selector, str):
                # セレクター文字列が渡された場合
                self.logger.debug(f"セレクターを使用: {response_element_selector}")
            else:
                # WebElement が渡された場合、情報を抽出
                element = response_element_selector
                element_info['tag'] = element.tag_name
                element_info['class'] = element.get_attribute("class")
                element_info['id'] = element.get_attribute("id")
                
                # XPathを生成
                try:
                    element_info['xpath'] = self.driver.execute_script(
                        "function getXPath(element) {"
                        "  if (element.id !== '') return '//*[@id=\"" + element.id + "\"]';"
                        "  if (element === document.body) return '/html/body';"
                        "  var ix = 0;"
                        "  var siblings = element.parentNode.childNodes;"
                        "  for (var i = 0; i < siblings.length; i++) {"
                        "    var sibling = siblings[i];"
                        "    if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';"
                        "    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;"
                        "  }"
                        "}"
                        "return getXPath(arguments[0]);", element
                    )
                except:
                    element_info['xpath'] = None
                    
                self.logger.debug(f"要素情報: タグ={element_info['tag']}, ID={element_info['id']}, クラス={element_info['class']}")
        except Exception as e:
            self.logger.warning(f"初回要素情報取得エラー: {e}")
        
        self.logger.info(f"最大 {max_checks} 回のチェックを開始（タイムアウト: {timeout}秒）")
        
        for i in range(max_checks):
            self.logger.debug(f"ストリーミングチェック {i+1}/{max_checks}")
            try:
                # 要素を再取得（Stale Element対策）
                current_element = None
                
                # 複数の方法で要素を再取得を試す
                methods = []
                
                if isinstance(response_element_selector, str):
                    methods.append(('selector', response_element_selector))
                    # 同様のセレクターのバリエーションも試す
                    if '*' not in response_element_selector:  # 既にワイルドカードを含まない場合
                        # クラス名やIDの部分マッチも試す
                        if response_element_selector.startswith('.'):
                            class_name = response_element_selector[1:]
                            methods.append(('partial_class', f"[class*='{class_name}']"))
                        elif response_element_selector.startswith('#'):
                            id_name = response_element_selector[1:]
                            methods.append(('partial_id', f"[id*='{id_name}']"))
                else:
                    if element_info['id']:
                        methods.append(('id', element_info['id']))
                    if element_info['xpath']:
                        methods.append(('xpath', element_info['xpath']))
                    if element_info['class']:
                        methods.append(('class', element_info['class']))
                
                for method_type, method_value in methods:
                    try:
                        if method_type == 'selector' or method_type == 'partial_class' or method_type == 'partial_id':
                            elements = self.driver.find_elements(By.CSS_SELECTOR, method_value)
                            if elements:
                                # DOM順序で最後の要素（最新）を優先し、それがダメなら最もテキストが長いものを選択
                                valid_elements = [e for e in elements if e.is_displayed() and len(e.text.strip()) > 0]
                                if valid_elements:
                                    # 最後の要素（最新）を選択
                                    current_element = valid_elements[-1]
                        elif method_type == 'id':
                            current_element = self.driver.find_element(By.ID, method_value)
                        elif method_type == 'xpath':
                            current_element = self.driver.find_element(By.XPATH, method_value)
                        elif method_type == 'class':
                            elements = self.driver.find_elements(By.CLASS_NAME, method_value)
                            if elements:
                                # クラス名で複数見つかった場合は、テキストが最も長い要素を選択
                                valid_elements = [e for e in elements if e.is_displayed() and len(e.text.strip()) > 0]
                                if valid_elements:
                                    current_element = max(valid_elements, key=lambda e: len(e.text.strip()))
                        
                        if current_element and current_element.is_displayed():
                            break
                            
                    except Exception as method_error:
                        self.logger.debug(f"要素再取得エラー ({method_type}: {method_value}): {method_error}")
                        continue
                
                if not current_element:
                    # セレクターで見つからない場合は、message-content-id属性を直接検索
                    self.logger.debug(f"チェック {i+1}: セレクター検索失敗、message-content-id属性による直接検索を実行中...")
                    
                    # response_element_selectorから ID を抽出
                    target_id = None
                    if isinstance(response_element_selector, str) and "message-content-id=" in response_element_selector:
                        # "[message-content-id='11']" から '11' を抽出
                        import re
                        match = re.search(r"message-content-id='(\d+)'", response_element_selector)
                        if match:
                            target_id = match.group(1)
                    
                    if target_id:
                        try:
                            # 指定されたIDのmessage-content-id要素を直接検索
                            specific_elements = self.driver.find_elements(By.CSS_SELECTOR, f"[message-content-id='{target_id}']")
                            
                            # 表示されている要素を選択
                            for elem in specific_elements:
                                if elem.is_displayed():
                                    current_element = elem
                                    self.logger.debug(f"message-content-id={target_id}の要素を発見: {len(elem.text.strip())}文字")
                                    break
                            
                            if not current_element:
                                self.logger.warning(f"チェック {i+1}: message-content-id={target_id}要素が表示されていません")
                                time.sleep(check_interval)
                                continue
                        except Exception as specific_error:
                            self.logger.debug(f"message-content-id検索エラー: {specific_error}")
                            time.sleep(check_interval)
                            continue
                    else:
                        self.logger.warning(f"チェック {i+1}: セレクターからIDを抽出できません: {response_element_selector}")
                        time.sleep(check_interval)
                        continue
                
                current_text = current_element.text.strip()
                current_length = len(current_text)
                
                self.logger.debug(f"チェック {i+1}/{max_checks}: テキスト長={current_length}文字")
                
                # 「応答を再生成」メッセージの検出（エラー状態）
                if "応答を再生成" in current_text or "再生成" in current_text:
                    self.logger.warning(f"再生成メッセージを検出 - エラー状態: '{current_text[:100]}'")
                    self.logger.info(f"セレクター: {response_element_selector}, チェック回数: {i+1}/{max_checks}")
                    # エラー状態として特別なフラグを返す
                    return "REGENERATE_ERROR_DETECTED"
                
                # 生成中フラグを初期化
                is_still_generating = False
                
                # Genspark.ai固有の完了判定：送信したプロンプト後の「コピー」ボタンの検出
                try:
                    prompt_based_copy_detected = self.check_copy_button_after_current_prompt()
                    
                    if prompt_based_copy_detected and current_length > 100:  # プロンプト後にコピーボタンがあり、十分なテキストがある
                        self.logger.info(f"送信したプロンプト後のコピーボタンを検出 - 応答完了と判定")
                        
                        # 「コピー」以下のテキストを除去
                        cleaned_text = self.clean_response_text(current_text)
                        self.logger.info(f"プロンプト後コピーボタン検出による応答完了（{len(cleaned_text)}文字）")
                        return cleaned_text
                        
                except Exception as e:
                    self.logger.debug(f"プロンプト後コピーボタン検出エラー: {e}")
                
                # Genspark.ai固有の生成中インジケーター検出
                genspark_loading_indicators = [
                    "thinking...", "thinking", "考え中", "生成中", "█"
                ]
                
                # 要素のclassをチェックしてthinking状態を検出
                try:
                    if hasattr(current_element, 'get_attribute'):
                        element_classes = current_element.get_attribute("class") or ""
                        if "thinking" in element_classes:
                            is_still_generating = True
                            self.logger.debug("要素のthinkingクラスを検出")
                except:
                    pass
                
                # テキスト内とページ内での「Thinking...」検出
                page_text = ""
                try:
                    page_text = self.driver.page_source.lower()
                except:
                    pass
                
                for indicator in genspark_loading_indicators:
                    # 現在のテキスト内でのチェック
                    if indicator.lower() in current_text.lower():
                        is_still_generating = True
                        self.logger.debug(f"テキスト内生成中インジケーター検出: {indicator}")
                        break
                    
                    # ページ内での「thinking」チェック（より限定的）
                    if indicator == "thinking" and "thinking..." in page_text:
                        # 「Thinking...」要素を具体的に検索
                        try:
                            thinking_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Thinking') or contains(text(), 'thinking')]")
                            visible_thinking = [elem for elem in thinking_elements if elem.is_displayed() and ("thinking" in elem.text.lower() or "█" in elem.text)]
                            
                            if visible_thinking:
                                is_still_generating = True
                                self.logger.debug("Thinking...インジケーターを検出")
                                break
                        except:
                            pass
                
                # ページソース全体でThinking関連の要素を再確認
                try:
                    if not is_still_generating: # 既に生成中と判定されていない場合のみ
                        # Thinkingを示す要素をより広範囲に検索
                        thinking_elements_broad = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'thinking') or contains(text(), 'Thinking') or contains(text(), '考え中') or contains(text(), '生成中')]")
                        visible_thinking_broad = [elem for elem in thinking_elements_broad if elem.is_displayed()]
                        if visible_thinking_broad:
                            is_still_generating = True
                            self.logger.debug("広範囲なThinking要素を検出")
                except Exception as e:
                    self.logger.debug(f"広範囲Thinking要素検索エラー: {e}")
                
                # 前回と同じテキストかチェック
                if current_text == previous_text and current_length > 0:
                    stable_count += 1
                    self.logger.debug(f"安定カウント: {stable_count}/{required_stable_count}")
                    
                    # 完了判定（より厳密に）
                    if stable_count >= required_stable_count and not is_still_generating and current_length >= minimum_response_length:
                        # プロンプト後のコピーボタンの存在を最終確認
                        copy_button_exists = False
                        try:
                            copy_button_exists = self.check_copy_button_after_current_prompt()
                        except:
                            pass
                        
                        if copy_button_exists or current_length >= 500:  # コピーボタンがあるか、十分長い場合
                            cleaned_text = self.clean_response_text(current_text)
                            self.logger.info(f"ストリーミング応答が完了しました（最終: {len(cleaned_text)}文字、コピーボタン: {copy_button_exists}）")
                            return cleaned_text
                        else:
                            self.logger.debug(f"完了条件を満たしていません（長さ: {current_length}, コピーボタン: {copy_button_exists}）")
                            stable_count = max(0, stable_count - 1)  # カウントを少し戻す
                else:
                    # テキストが変化した場合はカウントをリセット
                    if current_length > 0:  # 空のテキストは無視
                        stable_count = 0
                        previous_text = current_text
                        self.logger.debug(f"テキスト更新: {current_length}文字")
                
                # インジケーター検出時の処理
                if is_still_generating:
                    self.logger.debug("生成中インジケーターを検出")
                    stable_count = 0  # インジケーターがある間はカウントリセット
                
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"ストリーミング応答チェック中のエラー: {e}")
                time.sleep(check_interval)
                continue
        
        # タイムアウトした場合は古いテキストを返さずNoneを返す
        self.logger.warning(f"=== ストリーミングタイムアウト詳細情報 ===")
        self.logger.warning(f"タイムアウト時間: {timeout}秒")
        self.logger.warning(f"チェック回数: {max_checks}回（実際に実行された回数）")
        self.logger.warning(f"チェック間隔: {check_interval}秒")
        self.logger.warning(f"最後に取得されたテキスト長: {len(previous_text)}文字")
        self.logger.warning(f"最後のテキスト内容: {self.mask_text_for_debug(previous_text)}")
        self.logger.warning(f"stable_count: {stable_count}/{required_stable_count}")
        self.logger.warning("再生成ボタンチェックのためNoneを返します")
        return None

    def wait_for_streaming_complete_v2(self, response_element_selector, timeout=60, check_interval=3):
        """ストリーミング応答完了待機の新実装（動的要素遷移対応）"""
        self.logger.info("新ストリーミング検出ロジックを開始...")
        self.logger.info(f"最大 20 回のチェックを開始（タイムアウト: {timeout}秒）")
        
        start_time = time.time()
        max_checks = 20
        stable_count = 0
        stable_threshold = 3
        previous_text = ""
        
        # 初期状態の記録（プロンプト送信直後の状態）
        initial_message_ids = set()
        try:
            initial_elements = self.driver.find_elements(By.CSS_SELECTOR, "[message-content-id]")
            for elem in initial_elements:
                if elem.is_displayed():
                    msg_id = elem.get_attribute("message-content-id")
                    if msg_id:
                        initial_message_ids.add(msg_id)
            self.logger.debug(f"初期状態のmessage-content-id: {sorted(initial_message_ids)}")
        except Exception as e:
            self.logger.warning(f"初期状態記録エラー: {e}")
        
        # 初期のThinking要素ID特定
        initial_thinking_id = None
        if isinstance(response_element_selector, str) and "message-content-id=" in response_element_selector:
            import re
            match = re.search(r"message-content-id='(\d+)'", response_element_selector)
            if match:
                initial_thinking_id = match.group(1)
                self.logger.debug(f"初期Thinking要素ID: {initial_thinking_id}")
        
        for i in range(max_checks):
            self.logger.debug(f"新ストリーミングチェック {i+1}/{max_checks}")
            try:
                # 🔄 最優先: 再生成ボタンチェック
                self.logger.debug(f"チェック {i+1}: 再生成ボタンの優先チェックを実行中...")
                regenerate_detected = self.check_regenerate_button_lightweight()
                if regenerate_detected:
                    self.logger.warning(f"チェック {i+1}: 🚨 再生成ボタンを検出！即座にストリーミング監視を終了します")
                    self.logger.info("フォールバックメッセージ送信処理に移行します")
                    return "REGENERATE_ERROR_DETECTED"
                else:
                    self.logger.debug(f"チェック {i+1}: 再生成ボタンは未検出 - 通常の監視を継続")
                
                # 現在のすべてのmessage-content-id要素を取得
                current_elements = self.driver.find_elements(By.CSS_SELECTOR, "[message-content-id]")
                valid_elements = []
                
                for elem in current_elements:
                    if elem.is_displayed():
                        msg_id = elem.get_attribute("message-content-id")
                        text = elem.text.strip()
                        class_attr = elem.get_attribute('class') or ""
                        if msg_id and text:
                            valid_elements.append({
                                'element': elem,
                                'id': msg_id,
                                'text': text,
                                'length': len(text),
                                'classes': class_attr
                            })
                
                if not valid_elements:
                    self.logger.warning(f"チェック {i+1}: 有効な要素が見つかりません")
                    time.sleep(check_interval)
                    continue
                
                # ID順でソート（最新が最後）
                valid_elements.sort(key=lambda x: int(x['id']))
                
                # 1. 初期Thinking要素の確認
                thinking_element = None
                if initial_thinking_id:
                    for elem_data in valid_elements:
                        if elem_data['id'] == initial_thinking_id:
                            thinking_element = elem_data
                            break
                
                # 2. 新しい応答要素（初期状態にない要素）を探す
                new_response_elements = []
                for elem_data in valid_elements:
                    if elem_data['id'] not in initial_message_ids:
                        # Thinking系のクラスを持たない場合は正式な応答要素
                        if 'thinking' not in elem_data['classes'].lower():
                            new_response_elements.append(elem_data)
                
                current_element = None
                current_text = ""
                element_type = ""
                
                if new_response_elements:
                    # 新しい応答要素がある場合は最新のものを優先
                    latest_response = new_response_elements[-1]
                    current_element = latest_response['element']
                    current_text = latest_response['text']
                    element_type = f"新応答要素ID={latest_response['id']}"
                    self.logger.info(f"チェック {i+1}: ✅ 新しい応答要素が出現しました！Thinking状態終了 (ID={latest_response['id']})")
                    self.logger.debug(f"チェック {i+1}: {element_type}, 長さ={len(current_text)}文字")
                elif thinking_element:
                    # Thinking要素のみ存在
                    current_element = thinking_element['element']
                    current_text = thinking_element['text']
                    element_type = f"Thinking要素ID={thinking_element['id']}"
                    self.logger.debug(f"チェック {i+1}: {element_type}, 長さ={len(current_text)}文字")
                    
                    # Thinking状態のチェック
                    if self.is_thinking_state(current_text, "ストリーミング待機"):
                        self.logger.debug(f"チェック {i+1}: まだThinking状態 - {current_text[:20]}...")
                        time.sleep(check_interval)
                        continue
                    else:
                        self.logger.info(f"チェック {i+1}: ✅ Thinking状態が終了しました！ (Thinking要素ID={thinking_element['id']})")
                        self.logger.debug(f"Thinking終了時のテキスト内容: {current_text[:50]}...")
                else:
                    self.logger.warning(f"チェック {i+1}: 監視可能な要素が見つかりません")
                    time.sleep(check_interval)
                    continue
                
                # Thinking終了直後の5秒待機
                self.logger.info("Thinking状態が終了しました。5秒待機してからエラーチェックを開始します...")
                time.sleep(5)
                
                # エラーメッセージの検出
                self.logger.info("=== エラーチェック開始 ===")
                self.logger.info("再生成メッセージの有無をチェック中...")
                
                # 方法1: テキスト内容での判定
                text_based_error = "応答を再生成" in current_text or "再生成" in current_text
                self.logger.info(f"テキスト内容チェック結果: {'検出' if text_based_error else '未検出'}")
                
                # 方法2: DOM要素での判定
                self.logger.info("DOM要素での再生成ボタン検索を実行中...")
                dom_based_button = self.find_regenerate_button()
                self.logger.info(f"DOM要素チェック結果: {'検出' if dom_based_button else '未検出'}")
                
                # どちらが成功したかのログ出力
                if text_based_error and dom_based_button:
                    self.logger.warning("両方の方法で再生成エラーを検出しました（テキスト + DOM要素）")
                    return "REGENERATE_ERROR_DETECTED"
                elif text_based_error:
                    self.logger.warning("テキスト内容で再生成エラーを検出しました")
                    return "REGENERATE_ERROR_DETECTED"
                elif dom_based_button:
                    self.logger.warning("DOM要素で再生成ボタンを検出しました")
                    return "REGENERATE_ERROR_DETECTED"
                else:
                    self.logger.info("どちらの方法でも再生成エラーは検出されませんでした")
                
                # コピーボタンによる完了判定
                try:
                    copy_button_detected = self.check_copy_button_after_current_prompt()
                    if copy_button_detected and len(current_text) > 100:
                        cleaned_text = self.clean_response_text(current_text)
                        self.logger.info(f"コピーボタン検出による完了判定: {len(cleaned_text)}文字")
                        return cleaned_text
                except Exception as e:
                    self.logger.debug(f"コピーボタン検出エラー: {e}")
                
                # テキスト安定性チェック
                if current_text == previous_text and len(current_text) > 50:
                    stable_count += 1
                    self.logger.debug(f"安定カウント: {stable_count}/{stable_threshold} ({element_type})")
                    
                    if stable_count >= stable_threshold:
                        cleaned_text = self.clean_response_text(current_text)
                        self.logger.info(f"テキスト安定性による完了判定: {len(cleaned_text)}文字")
                        return cleaned_text
                else:
                    if len(current_text) > 0:
                        stable_count = 0
                        previous_text = current_text
                        self.logger.debug(f"テキスト更新: {len(current_text)}文字 ({element_type})")
                
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"新ストリーミングチェック {i+1} エラー: {e}")
                time.sleep(check_interval)
                continue
        
        # タイムアウト処理
        self.logger.warning(f"=== 新ストリーミングタイムアウト ===")
        self.logger.warning(f"タイムアウト時間: {timeout}秒, チェック回数: {max_checks}回")
        self.logger.warning(f"最後のテキスト: {self.mask_text_for_debug(previous_text)}")
        self.logger.warning("再生成ボタンチェックのためNoneを返します")
        return None

    def clean_response_text(self, text):
        """応答テキストから不要な部分（コピーボタン以下など）を除去"""
        if not text:
            return text
            
        # 「コピー」や「Copy」以下のテキストを除去
        copy_indicators = ["コピー", "Copy", "copy"]
        
        for indicator in copy_indicators:
            if indicator in text:
                # 「コピー」の位置を見つけて、その前までのテキストを取得
                copy_index = text.find(indicator)
                if copy_index > 0:
                    # コピーボタンより前の部分を取得
                    cleaned_text = text[:copy_index].strip()
                    self.logger.debug(f"「{indicator}」以下を除去: {len(text)} → {len(cleaned_text)}文字")
                    return cleaned_text
        
        # その他の不要な要素を除去
        unwanted_patterns = [
            # ボタンテキスト
            "再生成", "Regenerate", "いいね", "Like", "シェア", "Share",
            # ナビゲーション要素
            "次へ", "戻る", "Previous", "Next",
            # UI要素
            "メニュー", "Menu", "設定", "Settings"
        ]
        
        cleaned_text = text
        for pattern in unwanted_patterns:
            if pattern in cleaned_text:
                # パターンが文末近くにある場合は除去
                pattern_index = cleaned_text.rfind(pattern)
                if pattern_index > len(cleaned_text) * 0.8:  # 文章の80%以降にある場合
                    cleaned_text = cleaned_text[:pattern_index].strip()
                    self.logger.debug(f"不要なパターン「{pattern}」を除去")
        
        return cleaned_text.strip()

    def count_existing_responses(self):
        """既存の応答要素数をカウント"""
        response_selectors = [
            ".thinking_prompt",
            ".response_text", 
            ".assistant-message",
            ".ai-response",
            ".chat-response"
        ]
        
        max_count = 0
        try:
            for selector in response_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                max_count = max(max_count, len(elements))
            self.logger.debug(f"既存応答数カウント結果: {max_count}")
        except Exception as e:
            self.logger.debug(f"既存応答数カウントエラー: {e}")
        
        return max_count

    def count_existing_copy_buttons(self):
        """既存のコピーボタン数をカウント"""
        try:
            copy_buttons = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'コピー') or contains(text(), 'Copy')]")
            visible_copy_buttons = [btn for btn in copy_buttons if btn.is_displayed()]
            count = len(visible_copy_buttons)
            self.logger.debug(f"既存コピーボタン数: {count}")
            return count
        except Exception as e:
            self.logger.debug(f"既存コピーボタン数カウントエラー: {e}")
            return 0

    def check_copy_button_near_current_response(self, current_element):
        """現在の応答要素の近くにコピーボタンがあるかチェック"""
        try:
            if not current_element:
                return False
            
            # 現在の応答要素の親要素やその周辺でコピーボタンを探す
            parent_element = current_element
            
            # 複数レベルの親要素をチェック
            for level in range(5):  # 最大5階層上まで確認
                try:
                    # 現在の要素内でコピーボタンを探す
                    copy_buttons_in_area = parent_element.find_elements(By.XPATH, ".//*[contains(text(), 'コピー') or contains(text(), 'Copy')]")
                    
                    if copy_buttons_in_area:
                        # 表示されているコピーボタンがあるかチェック
                        visible_copies = [btn for btn in copy_buttons_in_area if btn.is_displayed()]
                        if visible_copies:
                            self.logger.debug(f"レベル{level}の親要素でコピーボタンを発見: {len(visible_copies)}個")
                            return True
                    
                    # 次の親要素に移動
                    parent_element = parent_element.find_element(By.XPATH, "..")
                    
                except:
                    break
            
            # 応答要素の次の兄弟要素もチェック
            try:
                next_siblings = current_element.find_elements(By.XPATH, "./following-sibling::*")
                for sibling in next_siblings[:3]:  # 最初の3つの兄弟要素をチェック
                    copy_buttons_in_sibling = sibling.find_elements(By.XPATH, ".//*[contains(text(), 'コピー') or contains(text(), 'Copy')]")
                    if copy_buttons_in_sibling:
                        visible_copies = [btn for btn in copy_buttons_in_sibling if btn.is_displayed()]
                        if visible_copies:
                            self.logger.debug(f"兄弟要素でコピーボタンを発見: {len(visible_copies)}個")
                            return True
            except:
                pass
                
            return False
            
        except Exception as e:
            self.logger.debug(f"コピーボタン近接チェックエラー: {e}")
            return False

    def check_copy_button_after_current_prompt(self):
        """現在送信したプロンプトの後にコピーボタンがあるかチェック"""
        try:
            if not hasattr(self, 'current_prompt_text') or not self.current_prompt_text:
                return False
            
            # ページ内で送信したプロンプトテキストを含む要素を探す
            prompt_text_short = self.current_prompt_text[:50]  # 最初の50文字で検索
            
            # プロンプトテキストを含む要素を探す
            xpath_query = f"//*[contains(text(), '{prompt_text_short}')]"
            
            try:
                prompt_elements = self.driver.find_elements(By.XPATH, xpath_query)
                
                for prompt_element in prompt_elements:
                    if prompt_element.is_displayed():
                        self.logger.debug(f"プロンプト要素を発見: {prompt_element.text[:100]}...")
                        
                        # このプロンプト要素の後にコピーボタンがあるかチェック
                        # 次の兄弟要素や親要素の次の兄弟要素を確認
                        if self.find_copy_button_after_element(prompt_element):
                            return True
                        
            except Exception as e:
                self.logger.debug(f"プロンプト要素検索エラー: {e}")
            
            # より広範囲にプロンプト文字列を検索
            try:
                page_source = self.driver.page_source
                if self.current_prompt_text in page_source:
                    self.logger.debug("ページソース内でプロンプトテキストを確認")
                    
                    # コピーボタンがプロンプト送信後に増えているかチェック
                    current_copy_count = self.count_existing_copy_buttons()
                    if current_copy_count > self.existing_copy_button_count:
                        self.logger.debug(f"コピーボタンが増加: {self.existing_copy_button_count} → {current_copy_count}")
                        return True
                        
            except Exception as e:
                self.logger.debug(f"ページソース検索エラー: {e}")
            
            return False
            
        except Exception as e:
            self.logger.debug(f"プロンプト後コピーボタンチェックエラー: {e}")
            return False

    def find_copy_button_after_element(self, element):
        """指定要素の後にコピーボタンがあるかチェック"""
        try:
            # 要素の後の兄弟要素をチェック
            following_elements = element.find_elements(By.XPATH, "./following-sibling::*")
            
            for following in following_elements[:10]:  # 最初の10個をチェック
                copy_buttons = following.find_elements(By.XPATH, ".//*[contains(text(), 'コピー') or contains(text(), 'Copy')]")
                if copy_buttons:
                    visible_copies = [btn for btn in copy_buttons if btn.is_displayed()]
                    if visible_copies:
                        self.logger.debug("プロンプト要素後にコピーボタンを発見")
                        return True
            
            # 親要素の次の兄弟要素もチェック
            try:
                parent = element.find_element(By.XPATH, "..")
                parent_following = parent.find_elements(By.XPATH, "./following-sibling::*")
                
                for following in parent_following[:5]:  # 最初の5個をチェック
                    copy_buttons = following.find_elements(By.XPATH, ".//*[contains(text(), 'コピー') or contains(text(), 'Copy')]")
                    if copy_buttons:
                        visible_copies = [btn for btn in copy_buttons if btn.is_displayed()]
                        if visible_copies:
                            self.logger.debug("プロンプト親要素後にコピーボタンを発見")
                            return True
            except:
                pass
                
            return False
            
        except Exception as e:
            self.logger.debug(f"要素後コピーボタン検索エラー: {e}")
            return False

    def get_latest_message_content(self, wait_for_streaming=True):
        """message-content-id属性を持つ要素から最新の応答を取得"""
        try:
            # message-content-id属性を持つすべての要素を取得
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, "[message-content-id]")
            
            if not message_elements:
                self.logger.debug("get_latest_message_content: message-content-id要素が見つかりません。Noneを返します。 (1)")
                return None
            
            self.logger.info(f"=== デバッグ: message-content-id要素を{len(message_elements)}個発見 ===")
            
            # IDでソートして最新を特定
            elements_with_id = []
            for i, element in enumerate(message_elements):
                if element.is_displayed():
                    content_id = element.get_attribute("message-content-id")
                    if content_id and content_id.isdigit():
                        text_content = element.text.strip()
                        element_classes = element.get_attribute("class") or ""
                        
                        # 詳細デバッグ情報（プライバシー保護）
                        self.logger.info(f"要素{i+1}: ID={content_id}, テキスト長={len(text_content)}文字, クラス={element_classes}")
                        masked_preview = self.mask_text_for_debug(text_content)
                        self.logger.info(f"  プレビュー: {masked_preview}")
                        self.logger.debug(f"  [HTML]: {element.get_attribute('outerHTML')}")
                        
                        # エラーメッセージは候補から除外
                        if "応答の生成中にエラーが発生" in text_content or "再生成" in text_content:
                            self.logger.info(f"  ✗ エラーメッセージのため除外: {text_content[:50]}...")
                            continue
                        
                        elements_with_id.append((int(content_id), element, text_content))
                    else:
                        self.logger.debug(f"要素{i+1}: 無効なID={content_id}")
                else:
                    self.logger.debug(f"要素{i+1}: 非表示")
            
            if not elements_with_id:
                self.logger.debug("get_latest_message_content: 有効なmessage-content-id要素が見つかりません。Noneを返します。 (2)")
                return None
            
            # IDでソート（降順 = 最新が最初）
            elements_with_id.sort(key=lambda x: x[0], reverse=True)
            
            self.logger.info(f"=== 有効な要素一覧（ID順） ===")
            for content_id, element, text_content in elements_with_id:
                masked_content = self.mask_text_for_debug(text_content, max_preview=10)
                self.logger.info(f"ID={content_id}: {masked_content}")
                self.logger.debug(f"  [HTML]: {element.get_attribute('outerHTML')}")
            
            # プロンプト送信後に新しく現れた応答らしい要素を探す
            new_elements = []
            prompt_texts_to_check = []
            if self.original_user_prompt:
                prompt_texts_to_check.append(self.original_user_prompt.strip())
            if self.current_prompt_text:
                prompt_texts_to_check.append(self.current_prompt_text.strip())

            for content_id, element, text_content in elements_with_id:
                # プロンプトと完全一致する場合のみ除外する
                is_prompt_match = text_content.strip() == self.current_prompt_text.strip() or text_content.strip() == self.original_user_prompt.strip()
                self.logger.debug(f"  要素ID={content_id}: プロンプトと一致={is_prompt_match}, テキスト長={len(text_content)}")
                if is_prompt_match:
                    self.logger.info(f"  ✗ ID={content_id}は送信したプロンプトと完全一致するため除外")
                    continue
                
                # 応答候補として追加
                new_elements.append((content_id, element, text_content))
            
            if not new_elements:
                self.logger.warning("get_latest_message_content: プロンプト送信後の新しい応答候補が見つかりません。Noneを返します。 (3)")
                return None
            
            # 最新のID（最大ID）を持つ要素を選択
            latest_id, latest_element, latest_text = new_elements[0]
            masked_response = self.mask_text_for_debug(latest_text)
            self.logger.info(f"🎯 最新応答を特定: message-content-id={latest_id}, 応答内容={masked_response}")
            
            # wait_for_streamingパラメータのログ出力
            self.logger.info(f"=== ストリーミング待機判定 ===")
            self.logger.info(f"wait_for_streaming: {wait_for_streaming}")
            
            # Thinking状態の事前チェック
            self.logger.info("=== 事前Thinking状態検出開始 ===")
            if latest_text:
                self.logger.info("応答テキストのThinking状態を事前チェック中...")
                is_thinking = self.is_thinking_state(latest_text, "事前チェック")
                self.logger.info(f"事前Thinking状態チェック結果: {is_thinking}")
                if is_thinking:
                    self.logger.info("=== 事前Thinking検出: Thinking状態確認 ===")
                else:
                    self.logger.info("=== 事前Thinking検出: 通常状態確認 ===")
            else:
                self.logger.info("応答テキストが空のため事前Thinkingチェックをスキップ")
                self.logger.info("=== 事前Thinking検出: スキップ ===")
            
            if wait_for_streaming:
                selector = f"[message-content-id='{latest_id}']"
                self.logger.info("=== ストリーミング待機開始 ===")
                self.logger.info(f"待機理由: wait_for_streaming=True が指定されているため")
                self.logger.info(f"監視対象セレクター: {selector}")
                self.logger.info("ストリーミング応答の完了を待機中...")
                # タイムアウトを60秒に短縮（デフォルト120秒から）
                final_text = self.wait_for_streaming_complete_v2(selector, timeout=60)
                
                if final_text == "REGENERATE_ERROR_DETECTED":
                    self.logger.warning(f"再生成エラーが検出されました")
                    self.logger.debug(f"get_latest_message_content: wait_for_streaming_response_completeからの戻り値: REGENERATE_ERROR_DETECTED")
                    return None
                elif final_text and "応答の生成中にエラーが発生しました" not in final_text:
                    masked_final = self.mask_text_for_debug(final_text)
                    self.logger.info(f"🎯 ストリーミング完了後: {masked_final}")
                    self.logger.debug(f"get_latest_message_content: wait_for_streaming_response_completeからの戻り値: {masked_final}。final_textを返します。 (5)")
                    return final_text
                else:
                    # ストリーミングタイムアウト時の詳細チェック
                    self.logger.warning(f"=== ストリーミングタイムアウト詳細チェック ===")
                    self.logger.warning(f"final_text: {self.mask_text_for_debug(final_text) if final_text else 'None'}")
                    self.logger.warning(f"latest_text: {self.mask_text_for_debug(latest_text)}")
                    self.logger.warning(f"latest_text(raw): '{latest_text}'")
                    self.logger.warning(f"latest_text.lower(): '{latest_text.lower() if latest_text else 'None'}'")
                    
                    # Thinking状態の詳細チェック
                    if latest_text:
                        thinking_check1 = "thinking" in latest_text.lower()
                        thinking_check2 = "thinking..." in latest_text
                        thinking_check3 = "thinking" in latest_text
                        self.logger.warning(f"Thinking状態チェック詳細:")
                        self.logger.warning(f"  - 'thinking' in latest_text.lower(): {thinking_check1}")
                        self.logger.warning(f"  - 'thinking...' in latest_text: {thinking_check2}")
                        self.logger.warning(f"  - 'thinking' in latest_text: {thinking_check3}")
                        
                        if thinking_check1 or thinking_check2:
                            self.logger.warning("応答がThinking状態のままタイムアウト - 再生成ボタンチェックのためNoneを返します")
                            return None
                    
                    # プロンプトテキストと同じ場合もNoneを返す
                    if latest_text and (latest_text.strip() == self.current_prompt_text.strip() or 
                        latest_text.strip() == self.original_user_prompt.strip()):
                        self.logger.warning(f"応答がプロンプトテキストと同一 - 再生成ボタンチェックのためNoneを返します")
                        self.logger.warning(f"  - current_prompt_text: {self.mask_text_for_debug(self.current_prompt_text)}")
                        self.logger.warning(f"  - original_user_prompt: {self.mask_text_for_debug(self.original_user_prompt)}")
                        return None
                    
                    masked_latest = self.mask_text_for_debug(latest_text)
                    self.logger.warning(f"ストリーミング失敗だが有効な応答として処理: {masked_latest}")
                    return self.clean_response_text(latest_text)
            else:
                # ストリーミング待機をスキップ
                self.logger.info("=== ストリーミング待機スキップ ===")
                self.logger.info(f"スキップ理由: wait_for_streaming=False が指定されているため")
                masked_latest = self.mask_text_for_debug(latest_text)
                self.logger.info(f"即座に応答を返します: {masked_latest}")
                return self.clean_response_text(latest_text)
                
        except Exception as e:
            self.logger.error(f"最新message-content取得エラー: {e}")
            return None

    def get_response_text(self):
        """応答テキストを取得（ストリーミング対応）"""
        # 最新のmessage-content-id要素を直接検索
        latest_response_text = self.get_latest_message_content()
        self.logger.debug(f"get_response_text: get_latest_message_contentからの戻り値: {self.mask_text_for_debug(latest_response_text) if latest_response_text else 'None'}")
        
        if latest_response_text:
            self.logger.debug(f"get_response_text: 最終的に返す応答テキスト: {self.mask_text_for_debug(latest_response_text)}")
            return latest_response_text
        
        # 応答が取得できない場合は再生成ボタンをチェック
        self.logger.warning("応答が取得できないため再生成ボタンをチェックします")
        regenerate_button = self.find_regenerate_button()
        
        if regenerate_button:
            self.logger.warning("再生成ボタンを検出 - REGENERATE_ERROR_DETECTEDを返します")
            return "REGENERATE_ERROR_DETECTED"
        
        self.logger.error("応答も再生成ボタンも見つかりません")
        return None
    
    def save_to_markdown(self, text, prompt):
        """テキストをMarkdownファイルに保存"""
        self.logger.debug(f"save_to_markdown: 保存テキスト長={len(text)}文字, プロンプト={self.mask_text_for_debug(prompt)}")
        self.prompt_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{self.prompt_counter:03d}_{timestamp}.md"
        
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        self.logger.info(f"save_to_markdown: 保存先ファイルパス: {filepath}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 自動取得結果 #{self.prompt_counter}\n\n")
            f.write(f"**日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
            f.write(f"**プロンプト**: {prompt}\n\n")
            f.write(f"---\n\n")
            f.write(text)
            
        self.logger.info(f"ファイルを保存しました: {filepath}")
        print(f"📁 応答をファイルに保存しました: {filename}")
        return filepath

    def send_message(self, prompt_text):
        """
        テキスト入力と送信を統一的に扱うメソッド。
        ユーザー操作を模倣し、複数の方法で確実な送信を試みる。
        """
        self.logger.info(f"メッセージ送信処理開始: {self.mask_text_for_debug(prompt_text)}")
        
        try:
            # 1. テキスト入力フィールドを探す
            text_input = self.find_text_input()
            if not text_input:
                self.logger.error("テキスト入力フィールドが見つかりません。")
                return False

            # 2. ユーザー操作を模倣：クリックしてフォーカス
            try:
                text_input.click()
                self.logger.info("テキスト入力フィールドにフォーカスしました。")
            except Exception as e:
                self.logger.warning(f"フィールドへのクリックに失敗: {e}")

            # 3. JavaScriptで確実に入力内容を設定し、イベントを発火
            self.logger.info("JavaScriptでテキストを設定し、inputイベントを発火させます。")
            escaped_text = prompt_text.replace('\\', '\\\\').replace('"', '\"').replace('\n', '\\n')
            self.driver.execute_script(f'arguments[0].value = "{escaped_text}";', text_input)
            self.driver.execute_script('arguments[0].dispatchEvent(new Event("input", { bubbles: true }));', text_input)
            
            time.sleep(0.5) # イベントが処理されるのを少し待つ

            # 4. あらゆる方法で送信を試みる
            send_success = False
            
            # 方法A: 送信ボタンのクリック（コメントアウト）
            # submit_button = self.find_submit_button()
            # if submit_button and submit_button != "ENTER_KEY":
            #     try:
            #         submit_button.click()
            #         self.logger.info("方法A: 送信ボタンのクリックに成功しました。")
            #         send_success = True
            #     except Exception as e:
            #         self.logger.warning(f"方法A失敗: {e}")

            # 方法B: JavaScriptによるフォーム送信（コメントアウト）
            # if not send_success:
            #     try:
            #         form_element = text_input.find_element(By.XPATH, "./ancestor-or-self::form")
            #         self.driver.execute_script("arguments[0].submit();", form_element)
            #         self.logger.info("方法B: JavaScriptによるフォーム送信に成功しました。")
            #         send_success = True
            #     except Exception as e:
            #         self.logger.warning(f"方法B失敗: {e}")

            # 方法C: キーボードイベントの発火（メイン送信方法）
            # send_success は常にFalseなので直接実行
            try:
                from selenium.webdriver.common.keys import Keys
                text_input.send_keys(Keys.ENTER)
                self.logger.info("Enterキーによる送信に成功しました。")
                send_success = True
            except Exception as e:
                self.logger.warning(f"Enterキー送信失敗: {e}")

            if not send_success:
                self.logger.error("すべての送信方法が失敗しました。")
                return False
            
            self.logger.info("メッセージが正常に送信されたと判断します。")
            return True

        except Exception as e:
            self.logger.error(f"メッセージ送信処理中の予期せぬエラー: {e}")
            return False
    
    def process_single_prompt(self, prompt_text):
        """単一のプロンプトを処理（メイン処理）"""
        # 新しいプロンプト処理開始時に状態変数をリセット
        self.current_retry_count = 0
        if hasattr(self, '_regenerate_button_call_count'):
            self._regenerate_button_call_count = 0
        
        # 詳細状態ログ
        self.logger.info(f"=== プロンプト処理開始 ===")
        self.logger.info(f"プロンプト内容: {self.mask_text_for_debug(prompt_text)}")
        self.logger.info(f"現在の状態変数:")
        self.logger.info(f"  - current_retry_count: {getattr(self, 'current_retry_count', 'undefined')}")
        self.logger.info(f"  - _regenerate_button_call_count: {getattr(self, '_regenerate_button_call_count', 'undefined')}")
        self.logger.info(f"  - existing_response_count: {getattr(self, 'existing_response_count', 'undefined')}")
        self.logger.info(f"  - existing_copy_button_count: {getattr(self, 'existing_copy_button_count', 'undefined')}")
        self.logger.info(f"  - prompt_counter: {getattr(self, 'prompt_counter', 'undefined')}")
        self.logger.info("状態変数をリセット完了")
        
        # プロンプト送信前の既存応答数とコピーボタン数を記録
        self.existing_response_count = self.count_existing_responses()
        self.existing_copy_button_count = self.count_existing_copy_buttons()
        self.current_prompt_text = prompt_text
        
        # 新しいプロンプト処理のたびにoriginal_user_promptを更新
        self.original_user_prompt = prompt_text
        self.logger.info(f"ユーザー元プロンプトを更新: {self.mask_text_for_debug(self.original_user_prompt)}")
        
        # 統一された送信メソッドを呼び出す
        if not self.send_message(prompt_text):
            self.logger.error("メッセージ送信に失敗したため、処理を中断します。")
            return False, "SEND_FAILED"
            
        # 少し待機してから応答をチェック
        time.sleep(3)
        
        self.logger.info("=== 応答テキスト取得フェーズ開始 ===")
        self.logger.info("get_response_text()を呼び出し中...")
        response_text = self.get_response_text()
        
        self.logger.info(f"=== get_response_text()結果詳細 ===")
        self.logger.info(f"戻り値: {self.mask_text_for_debug(response_text) if response_text else 'None'}")
        self.logger.info(f"戻り値の型: {type(response_text)}")
        self.logger.info(f"戻り値の長さ: {len(response_text) if response_text else 0}文字")
        self.logger.info(f"REGENERATE_ERROR_DETECTED判定: {response_text == 'REGENERATE_ERROR_DETECTED'}")
        
        # 再生成エラーの場合は明示的に失敗を返す
        if response_text == "REGENERATE_ERROR_DETECTED":
            self.logger.warning("再生成ボタンが検出されました - フォールバック処理が必要です")
            return False, "REGENERATE_ERROR_DETECTED"
        
        self.logger.debug(f"process_single_prompt: ファイル保存条件評価前: response_text={repr(response_text)}, bool(response_text)={bool(response_text)}, エラーメッセージ有無={'応答の生成中にエラーが発生' in response_text if response_text else False}")
        if response_text and "応答の生成中にエラーが発生" not in response_text:
            self.logger.debug(f"process_single_prompt: ファイル保存条件を満たしました。response_textの長さ={len(response_text)}")
            filepath = self.save_to_markdown(response_text, prompt_text)
            self.logger.info("処理が正常に完了しました")
            return True, response_text
        else:
            self.logger.warning(f"process_single_prompt: ファイル保存条件を満たしませんでした。response_text={self.mask_text_for_debug(response_text) if response_text else 'None'}, エラーメッセージ有無={'応答の生成中にエラーが発生' in response_text if response_text else False}")
            # デバッグ情報を出力してページ構造を確認
            self.debug_page_structure()
            return False, response_text

    def process_continuous_prompts(self):
        """継続的にプロンプトを処理する"""
        prompt_count = 0
        
        while True:
            try:
                prompt_count += 1
                print(f"\n=== プロンプト {prompt_count} ===")
                print("送信するプロンプトを入力してください:")
                print("（終了したい場合は 'quit' または 'exit' と入力してください）")
                
                prompt = input("プロンプト: ").strip()
                
                # 終了コマンドをチェック
                if prompt.lower() in ['quit', 'exit', '終了', 'q']:
                    print("プロンプト送信を終了します。")
                    break
                
                if not prompt:
                    print("空のプロンプトです。再度入力してください。")
                    continue
                
                # プロンプトを処理
                print(f"\nプロンプト {prompt_count} を送信中...")
                success, response_text = self.process_single_prompt(prompt)
                
                if success:
                    print(f"✅ プロンプト {prompt_count} の応答が正常に保存されました！")
                elif success is False:
                    print(f"❌ プロンプト {prompt_count} の処理中にエラーが発生しました")
                    
                    # process_single_promptがFalseを返した場合の詳細チェック
                    # 5回連続再生成エラーの場合は自動終了
                    print("処理を終了します。")
                    break
                        
            except KeyboardInterrupt:
                print("\n\nCtrl+Cが押されました。処理を中断しています...")
                break
            except Exception as e:
                self.logger.error(f"継続処理中のエラー: {e}")
                print(f"予期しないエラーが発生しました: {e}")
                
                retry_input = input("処理を続行しますか？ (y/n): ").strip().lower()
                if retry_input not in ['y', 'yes', 'はい']:
                    break
        
        print(f"\n🎉 合計 {prompt_count - 1} 個のプロンプトを処理しました。")
        return True
    
    def close(self):
        """ブラウザを閉じる"""
        if self.driver:
            # ユーザーに確認してからブラウザを閉じる
            try:
                print("\nブラウザを閉じますか？")
                print("ログイン状態は保持されます。")
                print("Enterキーでブラウザを閉じる、Ctrl+Cで中断: ")
                input()
                self.driver.quit()
                self.logger.info("ブラウザを閉じました（ログイン状態は保持されています）")
            except KeyboardInterrupt:
                print("\nブラウザは開いたままにします")
                self.logger.info("ブラウザは開いたままです")


def main():
    """メイン関数"""
    tool = ChromeAutomationTool(debug=True)
    
    try:
        # Chromeブラウザを起動
        if not tool.launch_chrome():
            return
            
        # ユーザーが手動でサイトを開くまで待機
        tool.wait_for_user_navigation()
        
        print("\n🚀 Chrome自動操作ツールが準備完了しました！")
        print("継続的にプロンプトを送信し、応答を保存します。")
        
        # 継続的なプロンプト処理を開始
        tool.process_continuous_prompts()
            
    except KeyboardInterrupt:
        print("\n処理を中断しました")
        
    finally:
        tool.close()


if __name__ == "__main__":
    main()