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
        
        print("\\nGenspark.aiチャットページが開きました。")
        print("ページが完全に読み込まれたらEnterキーを押してください: ")
        input()
        
    def find_text_input(self):
        """テキスト入力フィールドを探す"""
        selectors = [
            "textarea",
            "input[type='text']",
            "[contenteditable='true']",
            "textarea[placeholder*='質問']",
            "textarea[placeholder*='プロンプト']",
            ".prompt-textarea",
            "#prompt-textarea"
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
        """送信ボタンを探す"""
        # 一般的なボタンセレクター
        selectors = [
            "button[type='submit']",
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
                self.logger.debug(f"送信ボタンを発見: {selector}")
                return element
            except NoSuchElementException:
                continue
        
        # テキストベースで検索
        for text in text_searches:
            try:
                element = self.driver.find_element(By.XPATH, f"//button[contains(text(), '{text}')]")
                self.logger.debug(f"送信ボタンを発見 (テキスト): {text}")
                return element
            except NoSuchElementException:
                continue
        
        # より広範囲な検索 - すべてのボタンをチェック
        try:
            self.logger.info("すべてのボタンを検索して適切なものを探します...")
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
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
                    self.logger.info(f"適切な送信ボタンを発見: テキスト='{button_text}', クラス='{button_classes}'")
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
    
    def find_regenerate_button(self):
        """応答を再生成ボタンを探す（改善版・デバッグ強化）"""
        # グローバルカウンターを初期化（なければ）
        if not hasattr(self, '_regenerate_button_call_count'):
            self._regenerate_button_call_count = 0
        self._regenerate_button_call_count += 1
        
        self.logger.info(f"=== 再生成ボタン検索開始 (呼び出し{self._regenerate_button_call_count}回目) ===")
        
        # まず全体的なデバッグ情報を取得
        try:
            all_retry_elements = self.driver.find_elements(By.CSS_SELECTOR, "*[class*='retry']")
            self.logger.info(f"retry関連要素を{len(all_retry_elements)}個発見")
            
            for i, elem in enumerate(all_retry_elements):
                if elem.is_displayed():
                    class_attr = elem.get_attribute("class") or ""
                    tag_name = elem.tag_name
                    text_content = elem.text.strip()[:100]
                    self.logger.info(f"retry要素{i+1}: <{tag_name}> class='{class_attr}' text='{text_content}'")
        except Exception as e:
            self.logger.debug(f"retry要素デバッグエラー: {e}")
        
        # HTMLから分析した具体的なセレクター（優先順位順）
        selectors = [
            # 最も優先: 明確に「応答を再生成」テキストを含む要素
            "//*[contains(text(), '応答を再生成')]",
            "//*[contains(text(), '再生成')]", 
            # Genspark.ai固有の構造（Vue.js動的属性対応）
            ".bubble.retry .button",
            ".bubble.retry div.button", 
            ".bubble[class*='retry'] .button",
            ".bubble[class*='retry'] div.button",
            "[class*='bubble'][class*='retry'] .button",
            "[class*='bubble'][class*='retry'] div.button",
            # より具体的な構造
            ".bubble.retry .right .button",
            ".retry .right .button",
            "[class*='retry'] [class*='right'] [class*='button']",
            # 一般的なセレクター
            ".regenerate-button",
            "[class*='regenerate']",
            "button[aria-label*='再生成']",
            "button[title*='再生成']",
            # より幅広い検索
            ".retry .button",
            "div.button[class*='retry']",
            "*[class*='retry'] *[class*='button']"
        ]
        
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    elements = self.driver.find_elements(By.XPATH, selector)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                self.logger.debug(f"セレクター '{selector}': {len(elements)}個の要素を発見")
                
                # 表示されているボタンを探す
                for i, element in enumerate(elements):
                    try:
                        is_displayed = element.is_displayed()
                        button_text = element.text.strip()
                        tag_name = element.tag_name
                        class_attr = element.get_attribute("class") or ""
                        
                        self.logger.debug(f"  要素{i+1}: <{tag_name}> class='{class_attr}' displayed={is_displayed} text='{button_text}'")
                        
                        if is_displayed and button_text:
                            self.logger.info(f"表示中の要素発見: '{button_text}' (セレクター: {selector})")
                            
                            # XPathでテキスト検索の場合は即座に返す
                            if selector.startswith("//") and ("再生成" in button_text or "regenerate" in button_text.lower()):
                                self.logger.info(f"✓ XPath検索で有効な再生成ボタンを確認: '{button_text}'")
                                return element
                            
                            # CSS選択の場合はテキストを含むかチェック
                            elif not selector.startswith("//") and ("再生成" in button_text or "regenerate" in button_text.lower()):
                                self.logger.info(f"✓ CSS検索で有効な再生成ボタンを確認: '{button_text}'")
                                return element
                            else:
                                self.logger.debug(f"テキストが一致しない: '{button_text}'")
                    except Exception as e:
                        self.logger.debug(f"要素処理エラー: {e}")
                        
            except Exception as e:
                self.logger.debug(f"再生成ボタン検索エラー ({selector}): {e}")
                continue
        
        # 最後の手段: 「応答を再生成」テキストを含むすべての要素を直接検索
        self.logger.info("=== フォールバック検索開始 ===")
        try:
            # 「応答を再生成」テキストを含む要素を直接検索
            regenerate_text_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '応答を再生成')]")
            self.logger.info(f"フォールバック: {len(regenerate_text_elements)}個の「応答を再生成」テキスト要素を発見")
            
            for i, elem in enumerate(regenerate_text_elements):
                if elem.is_displayed():
                    elem_text = elem.text.strip()
                    self.logger.info(f"再生成テキスト要素{i+1}: '{elem_text}' (タグ: {elem.tag_name})")
                    
                    # この要素またはその親要素でクリック可能なものを探す
                    clickable_candidates = [elem]
                    
                    # 親要素も候補に追加
                    try:
                        parent = elem.find_element(By.XPATH, "..")
                        clickable_candidates.append(parent)
                        # さらに上の親も
                        grandparent = parent.find_element(By.XPATH, "..")
                        clickable_candidates.append(grandparent)
                    except:
                        pass
                    
                    for candidate in clickable_candidates:
                        try:
                            # クリック可能かテスト
                            if candidate.is_displayed() and candidate.is_enabled():
                                self.logger.info(f"✓ クリック可能な再生成要素を発見: {candidate.tag_name}")
                                return candidate
                        except:
                            continue
            
            # 従来のretry要素検索もフォールバックとして実行
            retry_elements = self.driver.find_elements(By.CSS_SELECTOR, "*[class*='retry']")
            self.logger.info(f"フォールバック: {len(retry_elements)}個のretry要素を発見")
            
            for i, retry_element in enumerate(retry_elements):
                if retry_element.is_displayed():
                    all_text = retry_element.text
                    self.logger.info(f"retry要素{i+1}のテキスト: '{all_text}'")
                    
                    if "応答を再生成" in all_text or "再生成" in all_text:
                        self.logger.info(f"✓ retry要素{i+1}に再生成テキストを発見")
                        
                        # retry要素内のボタンやクリック可能な要素を探す
                        clickable_selectors = [".button", "button", "div[class*='button']", "[role='button']", "div", "span"]
                        
                        for cs in clickable_selectors:
                            clickable_elements = retry_element.find_elements(By.CSS_SELECTOR, cs)
                            for j, clickable in enumerate(clickable_elements):
                                try:
                                    if clickable.is_displayed():
                                        clickable_text = clickable.text.strip()
                                        clickable_class = clickable.get_attribute("class") or ""
                                        self.logger.debug(f"    クリック候補{j+1}: text='{clickable_text}' class='{clickable_class}'")
                                        
                                        if "再生成" in clickable_text:
                                            self.logger.info(f"✓ retry要素内で再生成ボタンを発見: '{clickable_text}'")
                                            return clickable
                                except Exception as e:
                                    self.logger.debug(f"clickable要素処理エラー: {e}")
        except Exception as e:
            self.logger.debug(f"retry要素検索エラー: {e}")
                
        self.logger.warning(f"再生成ボタンが見つかりません (呼び出し{self._regenerate_button_call_count}回目)")
        return None

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
    
    def wait_for_streaming_response_complete(self, response_element_selector, timeout=60):
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
                        "  if (element.id !== '') return '//*[@id=\"' + element.id + '\"]';"
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
        
        for i in range(max_checks):
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
                    # セレクターで見つからない場合は、新しく出現したテキストコンテンツを探す
                    self.logger.debug(f"チェック {i+1}: セレクター検索失敗、代替検索を実行中...")
                    try:
                        # ページ上の全div要素から長いテキストを持つものを探す
                        all_divs = self.driver.find_elements(By.TAG_NAME, "div")
                        text_candidates = []
                        
                        for div in all_divs[-100:]:  # 最新の100要素をチェック
                            if div.is_displayed():
                                text = div.text.strip()
                                if len(text) > 50:  # 50文字以上のテキスト
                                    text_candidates.append((div, len(text)))
                        
                        if text_candidates:
                            # 最も長いテキストを持つ要素を選択
                            current_element = max(text_candidates, key=lambda x: x[1])[0]
                            self.logger.debug(f"代替検索で要素を発見: {len(current_element.text.strip())}文字")
                        else:
                            self.logger.warning(f"チェック {i+1}: 要素が見つかりません")
                            time.sleep(check_interval)
                            continue
                    except Exception as fallback_error:
                        self.logger.debug(f"代替検索エラー: {fallback_error}")
                        time.sleep(check_interval)
                        continue
                
                current_text = current_element.text.strip()
                current_length = len(current_text)
                
                self.logger.debug(f"チェック {i+1}/{max_checks}: テキスト長={current_length}文字")
                
                # 「応答を再生成」メッセージの検出（エラー状態）
                if "応答を再生成" in current_text or "再生成" in current_text:
                    self.logger.warning(f"再生成メッセージを検出 - エラー状態: '{current_text[:100]}'")
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
                        if len(current_text.strip()) < 50:  # 短いテキストの場合のみ生成中と判定
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
        
        # タイムアウトした場合でも、最後に取得できたテキストを返す
        self.logger.warning(f"ストリーミング応答のタイムアウト（{timeout}秒）")
        if previous_text:
            cleaned_text = self.clean_response_text(previous_text)
            return cleaned_text
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
                self.logger.debug("message-content-id要素が見つかりません")
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
                        
                        # 詳細デバッグ情報
                        self.logger.info(f"要素{i+1}: ID={content_id}, テキスト長={len(text_content)}文字, クラス={element_classes}")
                        self.logger.info(f"  プレビュー: {text_content[:100]}...")
                        
                        # エラーメッセージやThinking状態は候補から除外（フォールバック処理時）
                        if "応答の生成中にエラーが発生" in text_content or "再生成" in text_content:
                            self.logger.info(f"  ✗ エラーメッセージのため除外: {text_content[:50]}...")
                            continue
                        
                        # フォールバック処理時（wait_for_streaming=False）はThinking状態を除外
                        if not wait_for_streaming and ("Thinking" in text_content or "thinking" in element_classes):
                            self.logger.info(f"  ✗ フォールバック処理時のThinking状態のため除外: {text_content[:50]}...")
                            continue
                        
                        # thinking状態やストリーミング中でも候補に含める（テキストが短くても）
                        is_thinking = "thinking" in element_classes
                        has_cursor = "█" in text_content
                        
                        if len(text_content) > 10 or is_thinking or has_cursor:  # 条件を緩和
                            self.logger.info(f"  ✓ 候補要素として追加（thinking={is_thinking}, cursor={has_cursor}）")
                            elements_with_id.append((int(content_id), element, text_content))
                        else:
                            self.logger.info(f"  ✗ テキストが短すぎます（{len(text_content)}文字）")
                    else:
                        self.logger.debug(f"要素{i+1}: 無効なID={content_id}")
                else:
                    self.logger.debug(f"要素{i+1}: 非表示")
            
            if not elements_with_id:
                self.logger.debug("有効なmessage-content-id要素が見つかりません")
                return None
            
            # IDでソート（降順 = 最新が最初）
            elements_with_id.sort(key=lambda x: x[0], reverse=True)
            
            self.logger.info(f"=== 有効な要素一覧（ID順） ===")
            for content_id, element, text_content in elements_with_id:
                self.logger.info(f"ID={content_id}: {text_content[:50]}...")
            
            self.logger.info(f"=== プロンプト送信前の既存応答数: {self.existing_response_count} ===")
            
            # プロンプト送信後に新しく現れた要素のみを対象とする
            new_elements = []
            for content_id, element, text_content in elements_with_id:
                self.logger.info(f"検証中 ID={content_id}: existing_count={self.existing_response_count}")
                
                # 新しい要素の判定ロジックを改善
                # プロンプト送信前のexisting_response_countは、message-content-idの個数ではなく
                # 従来のセレクターでの応答要素数なので、message-content-idとは比較できない
                # 代わりに、プロンプトテキストを含まず、応答らしい内容を持つ要素を最新として扱う
                
                        # まず、送信したプロンプトテキストが含まれていないかチェック（強化版）
                prompt_check_passed = True
                
                # ユーザーの元プロンプトと現在のプロンプトの両方でチェック
                prompt_texts_to_check = []
                if hasattr(self, 'original_user_prompt') and self.original_user_prompt:
                    prompt_texts_to_check.append(('original', self.original_user_prompt))
                if hasattr(self, 'current_prompt_text') and self.current_prompt_text:
                    prompt_texts_to_check.append(('current', self.current_prompt_text))
                
                for prompt_type, prompt_text in prompt_texts_to_check:
                    if prompt_text and prompt_text[:30] in text_content:
                        masked_prompt = self.mask_text_for_debug(prompt_text)
                        self.logger.info(f"  ✗ ID={content_id}に{prompt_type}プロンプトテキストが含まれています: {masked_prompt}")
                        prompt_check_passed = False
                        break
                
                # 追加プロンプト検出ヒューリスティック
                if prompt_check_passed:
                    # テキストの長さと内容でユーザープロンプトっぽいかチェック
                    is_user_prompt_like = False
                    
                    # 短いテキストで、一般的なプロンプトパターンを含む場合
                    if len(text_content.strip()) < 200:  # 200文字未満の短いテキスト
                        prompt_patterns = [
                            "を書いてください", "を教えて", "どう思いますか", "について",
                            "write", "tell me", "explain", "how", "what", "please", "?", "？",
                            "hello", "hi", "こんにちは", "おはよう"
                        ]
                        
                        if any(pattern in text_content.lower() for pattern in prompt_patterns):
                            is_user_prompt_like = True
                            self.logger.info(f"  ✗ ID={content_id}はプロンプトパターンを含む短いテキストのため除外")
                    
                    if not is_user_prompt_like:
                        self.logger.info(f"  ✓ ID={content_id}はプロンプトテキストを含みません")
                    else:
                        prompt_check_passed = False
                
                if prompt_check_passed:
                    element_classes = element.get_attribute("class") or ""
                    is_thinking = "thinking" in element_classes
                    has_cursor = "█" in text_content
                    
                    if wait_for_streaming:
                        # 通常のストリーミング待機時：thinking状態やストリーミング中の要素は優先的に採用
                        if is_thinking or has_cursor:
                            self.logger.info(f"  ✓ ID={content_id}はthinking/ストリーミング中要素として採用")
                            new_elements.append((content_id, element, text_content))
                        else:
                            # 通常の応答キーワードチェック
                            response_keywords = ["回答:", "比較", "について", "です", "ます", "である", "。", "甘さ", "塩", "砂糖", "今日", "日差し", "強く", "琵琶湖", "日本一", "大きな", "湖", "富士山", "標高", "はい、", "面積", "平方キロメートル"]
                            found_keywords = [kw for kw in response_keywords if kw in text_content]
                            
                            if found_keywords:
                                self.logger.info(f"  ✓ ID={content_id}に応答キーワードを発見: {found_keywords}")
                                new_elements.append((content_id, element, text_content))
                            else:
                                self.logger.info(f"  ✗ ID={content_id}に応答キーワードがありません")
                    else:
                        # フォールバック処理時：thinking状態は除外、通常の応答のみ対象
                        if is_thinking or has_cursor:
                            self.logger.info(f"  ✗ ID={content_id}はフォールバック処理時のthinking状態のため除外")
                        else:
                            # 通常の応答キーワードチェック
                            response_keywords = ["回答:", "比較", "について", "です", "ます", "である", "。", "甘さ", "塩", "砂糖", "今日", "日差し", "強く", "琵琶湖", "日本一", "大きな", "湖", "富士山", "標高", "はい、", "面積", "平方キロメートル"]
                            found_keywords = [kw for kw in response_keywords if kw in text_content]
                            
                            if found_keywords:
                                self.logger.info(f"  ✓ ID={content_id}に応答キーワードを発見: {found_keywords}")
                                new_elements.append((content_id, element, text_content))
                            else:
                                self.logger.info(f"  ✗ ID={content_id}に応答キーワードがありません")
            
            if not new_elements:
                self.logger.warning("プロンプト送信後の新しいmessage-content-id要素が見つかりません")
                self.logger.warning("フォールバック: 最新のID要素を無条件で取得します")
                
                # フォールバック：最新IDの要素を無条件で選択
                if elements_with_id:
                    latest_id, latest_element, latest_text = elements_with_id[0]  # 最大ID
                    self.logger.info(f"フォールバック選択: message-content-id={latest_id}")
                    return self.clean_response_text(latest_text)
                else:
                    return None
            
            # 最新のID（最大ID）を持つ要素を選択
            latest_id, latest_element, latest_text = new_elements[0]
            masked_response = self.mask_text_for_debug(latest_text)
            self.logger.info(f"🎯 最新応答を特定: message-content-id={latest_id}, 応答内容={masked_response}")
            
            # セレクター文字列を作成
            selector = f"[message-content-id='{latest_id}']"
            
            if wait_for_streaming:
                # ストリーミング応答の完了を待機
                self.logger.info("ストリーミング応答の完了を待機中...")
                final_text = self.wait_for_streaming_response_complete(selector)
                
                if final_text == "REGENERATE_ERROR_DETECTED":
                    # 再生成エラーが検出された場合はNoneを返してリトライを促す
                    self.logger.warning(f"再生成エラーが検出されました - リトライが必要です ({self.current_retry_count}回目)")
                    return None
                elif final_text and "応答の生成中にエラーが発生しました" not in final_text:
                    masked_final = self.mask_text_for_debug(final_text)
                    self.logger.info(f"🎯 ストリーミング完了後: {masked_final}")
                    return final_text
                else:
                    # ストリーミング検出に失敗した場合は、現在のテキストを返す
                    self.logger.warning("ストリーミング検出失敗、現在のテキストを返します")
                    return self.clean_response_text(latest_text)
            else:
                # ストリーミング待機をスキップして現在のテキストを返す
                skip_masked = self.mask_text_for_debug(latest_text)
                self.logger.info(f"🎯 ストリーミング待機をスキップ - {skip_masked}")
                return self.clean_response_text(latest_text)
                
        except Exception as e:
            self.logger.error(f"最新message-content取得エラー: {e}")
            return None

    def get_response_text(self):
        """応答テキストを取得（ストリーミング対応）"""
        # 強化されたエラーメッセージチェック
        try:
            # 再生成ボタンや関連エラーメッセージを検出
            error_selectors = [
                "//*[contains(text(), '応答の生成中にエラーが発生')]",
                "//*[contains(text(), '再生成')]", 
                "//*[contains(text(), '応答を再生成')]",
                "*[class*='retry']",
                ".bubble.retry"
            ]
            
            for selector in error_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    visible_errors = [elem for elem in elements if elem.is_displayed()]
                    if visible_errors:
                        self.logger.warning(f"エラー要素検出（{selector}）- 応答取得をスキップ: {len(visible_errors)}個")
                        for elem in visible_errors[:2]:  # 最初の2個をログ出力
                            try:
                                self.logger.info(f"  エラー要素: {elem.text.strip()[:100]}")
                            except:
                                pass
                        return None
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"エラーメッセージチェック中のエラー: {e}")
        
        # 最新のmessage-content-id要素を直接検索する専用メソッドを最初に試す
        latest_response_text = self.get_latest_message_content()
        if latest_response_text:
            return latest_response_text
        
        # get_latest_message_content() が None を返した場合は、エラー状態と判断して終了
        self.logger.warning("get_latest_message_content()がNoneを返しました - エラー状態のため応答取得を中断")
        return None
    
    def save_to_markdown(self, text, prompt):
        """テキストをMarkdownファイルに保存"""
        self.prompt_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{self.prompt_counter:03d}_{timestamp}.md"
        
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 自動取得結果 #{self.prompt_counter}\\n\\n")
            f.write(f"**日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\\n\\n")
            f.write(f"**プロンプト**: {prompt}\\n\\n")
            f.write(f"---\\n\\n")
            f.write(text)
            
        self.logger.info(f"ファイルを保存しました: {filepath}")
        print(f"📁 応答をファイルに保存しました: {filename}")
        return filepath
    
    def process_single_prompt(self, prompt_text):
        """単一のプロンプトを処理（メイン処理）"""
        # プロンプト送信前の既存応答数とコピーボタン数を記録
        self.existing_response_count = self.count_existing_responses()
        self.existing_copy_button_count = self.count_existing_copy_buttons()
        self.current_prompt_text = prompt_text  # 送信するプロンプトテキストを保存
        
        # ユーザーの元プロンプトを保存（フォールバック時の区別用）
        if not hasattr(self, 'original_user_prompt') or not self.original_user_prompt:
            self.original_user_prompt = prompt_text
            self.logger.info(f"ユーザー元プロンプトを記録: {self.mask_text_for_debug(self.original_user_prompt)}")
        
        self.prompt_send_time = time.time()  # プロンプト送信時刻を記録
        self.logger.info(f"プロンプト送信前 - 既存応答数: {self.existing_response_count}, 既存コピーボタン数: {self.existing_copy_button_count}")
        
        # テキスト入力フィールドを探す（リトライ機能付き）
        text_input = None
        max_input_retries = 3
        
        for retry in range(max_input_retries):
            try:
                text_input = self.find_text_input()
                if text_input:
                    # 要素が利用可能かテスト
                    text_input.is_displayed()
                    break
                else:
                    self.logger.warning(f"テキスト入力フィールド検索リトライ {retry + 1}/{max_input_retries}")
                    time.sleep(2)
            except Exception as e:
                self.logger.warning(f"テキスト入力フィールド取得エラー（リトライ {retry + 1}/{max_input_retries}）: {e}")
                time.sleep(2)
                
        if not text_input:
            self.logger.error("テキスト入力フィールドが見つかりません（リトライ後）")
            return False
            
        # プロンプトを入力（複数行対応）
        try:
            text_input.clear()
            # 複数行テキストの場合、JavaScriptで設定する方が確実
            if '\n' in prompt_text:
                self.logger.info("複数行プロンプトをJavaScriptで設定中...")
                # JavaScriptでvalueを直接設定
                escaped_text = prompt_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                self.driver.execute_script(f'arguments[0].value = "{escaped_text}";', text_input)
                # inputイベントを発火
                self.driver.execute_script('arguments[0].dispatchEvent(new Event("input", { bubbles: true }));', text_input)
            else:
                text_input.send_keys(prompt_text)
            
            self.logger.info(f"プロンプトを入力: {prompt_text[:50]}...")
        except Exception as e:
            self.logger.error(f"プロンプト入力エラー: {e}")
            return False
        
        # 送信ボタンをクリック（リトライ機能付き）
        submit_success = False
        max_submit_retries = 3
        
        for retry in range(max_submit_retries):
            try:
                submit_button = self.find_submit_button()
                if submit_button == "ENTER_KEY":
                    # Enterキーを送信
                    from selenium.webdriver.common.keys import Keys
                    text_input.send_keys(Keys.RETURN)
                    self.logger.info("Enterキーで送信しました")
                    submit_success = True
                    break
                elif submit_button:
                    submit_button.click()
                    self.logger.info("送信ボタンをクリックしました")
                    submit_success = True
                    break
                else:
                    self.logger.warning(f"送信ボタン検索リトライ {retry + 1}/{max_submit_retries}")
                    time.sleep(2)
            except Exception as e:
                self.logger.warning(f"送信ボタンクリックエラー（リトライ {retry + 1}/{max_submit_retries}）: {e}")
                time.sleep(2)
                
        if not submit_success:
            self.logger.error("送信ボタンが見つかりません（リトライ後）")
            return False
            
        # 少し待機してから応答をチェック
        time.sleep(3)
        
        # 自動リトライ機能を実行（再生成ボタンが表示された場合の処理）
        if not self.handle_regenerate_with_retry():
            # 5回連続で再生成ボタンが表示された場合はエラーメッセージを返す
            self.logger.warning("5回連続で再生成ボタンが表示されました - フォールバック処理が必要")
            return False, "REGENERATE_RETRY_FAILED"
        
        # 正常な応答テキストを取得
        response_text = self.get_response_text()
        if response_text and response_text != "REGENERATE_ERROR_DETECTED" and "応答の生成中にエラーが発生" not in response_text:
            filepath = self.save_to_markdown(response_text, prompt_text)
            self.logger.info("処理が正常に完了しました")
            return True, response_text  # GUIのために応答テキストも返す
        else:
            self.logger.warning("応答テキストが取得できませんでした")
            # デバッグ情報を出力してページ構造を確認
            self.debug_page_structure()
            return False, response_text  # エラーメッセージも返す（フォールバック判定用）

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
        print("\\n処理を中断しました")
        
    finally:
        tool.close()


if __name__ == "__main__":
    main()