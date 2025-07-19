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
        self.setup_logging()
        
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
        """応答を再生成ボタンを探す"""
        selectors = [
            "//*[contains(text(), '応答を再生成')]",
            "//*[contains(text(), '再生成')]",
            "//*[contains(text(), 'Regenerate')]",
            ".regenerate-button"
        ]
        
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    element = self.driver.find_element(By.XPATH, selector)
                else:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                self.logger.debug(f"再生成ボタンを発見: {selector}")
                return element
            except NoSuchElementException:
                continue
                
        self.logger.warning("再生成ボタンが見つかりません")
        return None
    
    def wait_for_streaming_response_complete(self, response_element_selector, timeout=60):
        """ストリーミング応答が完了するまで待機（Stale Element対策）"""
        self.logger.info("ストリーミング応答の完了を待機中...")
        
        previous_text = ""
        stable_count = 0
        required_stable_count = 2  # 2回連続でテキストが変わらなければ完了と判定（短縮）
        check_interval = 2  # 2秒間隔でチェック
        max_checks = timeout // check_interval
        
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
                                # 有効な要素の中で最もテキストが長いものを選択
                                valid_elements = [e for e in elements if e.is_displayed() and len(e.text.strip()) > 0]
                                if valid_elements:
                                    current_element = max(valid_elements, key=lambda e: len(e.text.strip()))
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
                
                # 生成中フラグを初期化
                is_still_generating = False
                
                # Genspark.ai固有の完了判定：「コピー」ボタンの検出
                try:
                    copy_buttons = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'コピー') or contains(text(), 'Copy')]")
                    visible_copy_buttons = [btn for btn in copy_buttons if btn.is_displayed()]
                    
                    if visible_copy_buttons and current_length > 100:  # コピーボタンがあり、十分なテキストがある
                        self.logger.info(f"コピーボタンを検出 - 応答完了と判定（{current_length}文字）")
                        return current_text
                        
                except Exception as e:
                    self.logger.debug(f"コピーボタン検出エラー: {e}")
                
                # Genspark.ai固有の生成中インジケーター検出
                genspark_loading_indicators = [
                    "thinking...", "thinking", "考え中", "生成中", "█"
                ]
                
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
                    
                    # 長いテキストの場合は早期完了（1回の安定で十分）
                    early_completion_threshold = 500  # 500文字以上
                    if current_length >= early_completion_threshold and stable_count >= 1 and not is_still_generating:
                        self.logger.info(f"長いテキストの早期完了判定（{current_length}文字）")
                        return current_text
                    
                    # 通常の完了判定
                    if stable_count >= required_stable_count and not is_still_generating:
                        self.logger.info(f"ストリーミング応答が完了しました（最終: {current_length}文字）")
                        return current_text
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
        return previous_text if previous_text else None

    def get_response_text(self):
        """応答テキストを取得（ストリーミング対応）"""
        # Genspark.ai用の具体的なセレクターを最初に試す
        response_selectors = [
            # Genspark.ai 固有のセレクター
            ".thinking_prompt",
            ".response_text", 
            ".assistant-message",
            ".ai-response",
            ".chat-response",
            ".output-container",
            # 一般的な応答コンテナのセレクター
            ".response-content",
            ".message-content", 
            ".output-text",
            ".result",
            "[data-testid='conversation-turn-content']",
            # より広範囲なセレクター
            "[class*='response']",
            "[class*='message']",
            "[class*='output']",
            "[class*='answer']",
            "[id*='response']",
            "[id*='output']"
        ]
        
        # 最初に、新しいコンテンツの出現を待機
        self.logger.info("新しい応答コンテンツの出現を待機中...")
        time.sleep(3)  # 応答が生成され始めるまで少し待機
        
        # まず一般的なセレクターを試す
        for selector in response_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # 新しく追加された要素を特定（最後の要素、または最も長いテキストを持つ要素）
                    candidate_elements = []
                    for element in elements:
                        if element.is_displayed():
                            text_length = len(element.text.strip())
                            if text_length > 0:  # 空でない要素
                                candidate_elements.append((element, text_length))
                    
                    if candidate_elements:
                        # テキストが最も長い要素を選択（最新の応答の可能性が高い）
                        response_element = max(candidate_elements, key=lambda x: x[1])[0]
                        self.logger.info(f"応答要素を発見（セレクター: {selector}, テキスト長: {len(response_element.text.strip())}文字）")
                        
                        # ストリーミング応答の完了を待機（要素ではなくセレクターを渡す）
                        final_text = self.wait_for_streaming_response_complete(selector)
                        if final_text and "応答の生成中にエラーが発生しました" not in final_text:
                            return final_text
            except Exception as e:
                self.logger.debug(f"応答テキスト取得エラー ({selector}): {e}")
                continue
        
        # 一般的なセレクターで見つからない場合、より広範囲に検索
        self.logger.info("広範囲で応答テキストを検索中...")
        
        try:
            # 入力フィールドの後に追加された新しい要素を探す
            current_url = self.driver.current_url
            self.logger.debug(f"現在のURL: {current_url}")
            
            # ページ全体のテキストを確認
            body_elements = self.driver.find_elements(By.TAG_NAME, "div")
            
            # 最近追加された要素で、ある程度の長さのテキストを持つものを探す
            for element in reversed(body_elements[-50:]):  # 最後の50個の要素をチェック
                try:
                    element_text = element.text.strip()
                    element_tag = element.tag_name
                    element_class = element.get_attribute("class") or ""
                    element_id = element.get_attribute("id") or ""
                    
                    # DOM情報のデバッグログ
                    self.logger.debug(f"要素情報: タグ={element_tag}, ID='{element_id}', クラス='{element_class}', 表示={element.is_displayed()}")
                    
                    # 長いテキスト、かつ入力した内容以外のものを探す
                    if (element_text and 
                        len(element_text) > 10 and 
                        not any(skip_word in element_text.lower() for skip_word in ["button", "input", "menu", "nav", "header", "footer"]) and
                        element.is_displayed()):
                        
                        # 応答らしい要素を特定するキーワード
                        response_indicators = ["回答", "応答", "返答", "こんにちは", "hello", "hi", "答え"]
                        
                        self.logger.debug(f"要素候補: タグ={element_tag}, クラス='{element_class}', テキスト='{element_text[:100]}...'")
                        
                        # 応答らしいテキストかチェック
                        if (any(indicator in element_text.lower() for indicator in response_indicators) or
                            len(element_text) > 30):  # 30文字以上の長いテキスト
                            
                            self.logger.info(f"応答候補を発見: {len(element_text)}文字")
                            
                            # ストリーミング応答の完了を待機
                            final_text = self.wait_for_streaming_response_complete(element)
                            if final_text:
                                return final_text
                            
                except Exception as e:
                    self.logger.debug(f"要素チェック中のエラー: {e}")
                    continue
            
            # 特定のサイト向けの検索パターン
            site_specific_selectors = [
                # Genspark.ai用
                "[class*='response']",
                "[class*='answer']", 
                "[class*='reply']",
                "[class*='message']",
                "[class*='content']",
                # その他のAIサイト用
                "[role='main'] div",
                "[role='dialog'] div",
                "main div",
                "article div"
            ]
            
            for selector in site_specific_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if (text and len(text) > 20 and element.is_displayed()):
                            
                            self.logger.debug(f"サイト固有要素: セレクター={selector}, クラス='{element.get_attribute('class')}', ID='{element.get_attribute('id')}'")
                            
                            # ストリーミング応答の完了を待機
                            final_text = self.wait_for_streaming_response_complete(element)
                            if final_text:
                                self.logger.info(f"サイト固有検索で発見: {len(final_text)}文字")
                                return final_text
                                
                except Exception as e:
                    self.logger.debug(f"サイト固有検索エラー ({selector}): {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"広範囲検索中のエラー: {e}")
                
        self.logger.warning("応答テキストが見つかりません")
        return None
    
    def save_to_markdown(self, text, prompt):
        """テキストをMarkdownファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{timestamp}.md"
        
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 自動取得結果\\n\\n")
            f.write(f"**日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\\n\\n")
            f.write(f"**プロンプト**: {prompt}\\n\\n")
            f.write(f"---\\n\\n")
            f.write(text)
            
        self.logger.info(f"ファイルを保存しました: {filepath}")
        return filepath
    
    def process_site(self, prompt_text):
        """サイトを処理（メイン処理）"""
        max_retries = 10
        retry_count = 0
        
        # テキスト入力フィールドを探す
        text_input = self.find_text_input()
        if not text_input:
            self.logger.error("テキスト入力フィールドが見つかりません")
            return False
            
        # プロンプトを入力
        text_input.clear()
        text_input.send_keys(prompt_text)
        self.logger.info(f"プロンプトを入力: {prompt_text[:50]}...")
        
        # 送信ボタンをクリック
        submit_button = self.find_submit_button()
        if submit_button == "ENTER_KEY":
            # Enterキーを送信
            from selenium.webdriver.common.keys import Keys
            text_input.send_keys(Keys.RETURN)
            self.logger.info("Enterキーで送信しました")
        elif submit_button:
            submit_button.click()
            self.logger.info("送信ボタンをクリックしました")
        else:
            self.logger.error("送信ボタンが見つかりません")
            return False
            
        # 応答を待機し、エラーチェック
        while retry_count < max_retries:
            time.sleep(3)  # 応答を待つ
            
            if self.check_for_error_message():
                retry_count += 1
                self.logger.warning(f"エラー検出、再試行 {retry_count}/{max_retries}")
                
                # 再生成ボタンをクリック
                regenerate_button = self.find_regenerate_button()
                if regenerate_button:
                    regenerate_button.click()
                    self.logger.info("再生成ボタンをクリックしました")
                    time.sleep(5)  # 再生成の待機時間
                else:
                    self.logger.error("再生成ボタンが見つかりません")
                    break
            else:
                # エラーメッセージが無い場合、応答テキストを取得
                response_text = self.get_response_text()
                if response_text:
                    filepath = self.save_to_markdown(response_text, prompt_text)
                    self.logger.info("処理が正常に完了しました")
                    return True
                else:
                    self.logger.warning("応答テキストが取得できませんでした")
                    # デバッグ情報を出力してページ構造を確認
                    self.debug_page_structure()
                    time.sleep(2)
                    
        self.logger.error(f"最大試行回数({max_retries})に達しました")
        return False
    
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
        
        # プロンプトを入力
        prompt = input("送信するプロンプトを入力してください: ")
        
        # サイトを処理
        success = tool.process_site(prompt)
        
        if success:
            print("処理が正常に完了しました！")
        else:
            print("処理中にエラーが発生しました")
            
    except KeyboardInterrupt:
        print("\\n処理を中断しました")
        
    finally:
        tool.close()


if __name__ == "__main__":
    main()