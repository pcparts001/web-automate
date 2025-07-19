#!/usr/bin/env python3
"""
Chrome自動操作ツール - Gradio Web GUI
"""

import gradio as gr
import threading
import time
import queue
import logging
from datetime import datetime
from main import ChromeAutomationTool

class AutomationGUI:
    def __init__(self):
        self.tool = None
        self.is_running = False
        self.status_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.current_thread = None
        self.chrome_initialized = False
        
    def mask_response_for_debug(self, text, max_preview=6):
        """応答テキストをデバッグ用にマスキング（プライバシー保護強化）"""
        if not text:
            return "None"
        
        text = text.strip()
        if len(text) <= max_preview:
            # 短いテキストは全体を表示
            return f"[{len(text)}文字] '{text}'"
        else:
            # 長いテキストは先頭6文字のみ表示
            start = text[:max_preview]
            return f"[{len(text)}文字] '{start}...(({len(text) - max_preview}文字省略))'"
        
    def start_automation(self, url, prompt_text, use_fallback, fallback_message, retry_count):
        """自動化プロセスを開始"""
        if self.is_running:
            return "⚠️ 既に実行中です", "", "実行中"
            
        if not prompt_text.strip():
            return "❌ プロンプトを入力してください", "", "待機中"
            
        self.is_running = True
        
        # バックグラウンドスレッドで実行
        self.current_thread = threading.Thread(
            target=self._run_automation,
            args=(url, prompt_text, use_fallback, fallback_message, retry_count),
            daemon=True
        )
        self.current_thread.start()
        
        return "🚀 自動化を開始しました", "", "実行中"
    
    def _run_automation(self, url, prompt_text, use_fallback, fallback_message, retry_count):
        """バックグラウンドで自動化を実行"""
        try:
            # Chrome初期化（初回のみ）
            if not self.chrome_initialized:
                self.status_queue.put("Chrome起動中...")
                
                # ChromeAutomationToolを初期化
                self.tool = ChromeAutomationTool(debug=True)
                
                # Chrome起動
                if not self.tool.launch_chrome():
                    self.status_queue.put("❌ Chrome起動に失敗")
                    self.response_queue.put("Chrome起動に失敗しました")
                    return
                    
                self.chrome_initialized = True
                self.status_queue.put("Chrome初期化完了")
                
            # URLナビゲーション（デフォルト以外の場合）
            default_url = "https://www.genspark.ai/agents?type=moa_chat"
            if url.strip() and url.strip() != default_url:
                current_url = self.tool.driver.current_url
                if current_url != url.strip():
                    self.status_queue.put(f"URLに移動中: {url}")
                    self.tool.driver.get(url.strip())
                    time.sleep(3)
            
            self.status_queue.put("ページ準備完了")
            
            # プロンプト処理
            self.status_queue.put("プロンプト送信中...")
            
            # retry_countを設定
            if hasattr(self.tool, 'max_regenerate_retries'):
                self.tool.max_regenerate_retries = max(1, int(retry_count))
            
            # single promptとして処理
            success, response_text = self.tool.process_single_prompt(prompt_text)
            
            # 成功かつ有効な応答がある場合
            if (success and response_text and 
                response_text != "REGENERATE_ERROR_DETECTED" and 
                "応答の生成中にエラーが発生" not in response_text):
                self.status_queue.put("✅ 応答受信完了")
                self.response_queue.put(response_text)
            else:
                # 失敗した場合またはエラーメッセージが含まれる場合の処理
                if response_text == "REGENERATE_ERROR_DETECTED":
                    self.status_queue.put("⚠️ 再生成ボタンを検出 - フォールバック処理を開始")
                else:
                    self.status_queue.put(f"⚠️ エラー検出: {response_text if response_text else 'None'}")
                
                # フォールバック処理の条件を厳格化：再生成エラーが明確に検出された場合のみ実行
                if (use_fallback and fallback_message.strip() and 
                    response_text == "REGENERATE_ERROR_DETECTED"):
                    # フォールバックメッセージを自動送信
                    self.status_queue.put("🔄 フォールバックメッセージを自動送信中...")
                    
                    try:
                        # 直接テキスト入力と送信を実行（既存のロジックを使用）
                        self.status_queue.put("📝 フォールバックテキスト入力中...")
                        
                        # フォールバック送信前に状態をリセット（元プロンプトは保持）
                        self.tool.existing_response_count = self.tool.count_existing_responses()
                        # current_prompt_textはフォールバックメッセージで更新しつつ、original_user_promptは保持
                        self.tool.current_prompt_text = fallback_message.strip()
                        self.status_queue.put(f"🔍 [DEBUG] フォールバックメッセージ設定: {self.tool.mask_text_for_debug(fallback_message)}")
                        if hasattr(self.tool, 'original_user_prompt'):
                            self.status_queue.put(f"🔍 [DEBUG] 元ユーザープロンプト保持: {self.tool.mask_text_for_debug(self.tool.original_user_prompt)}")
                        
                        # テキスト入力フィールドを取得
                        text_input = self.tool.find_text_input()
                        if text_input:
                            text_input.clear()
                            
                            # 複数行対応（通常プロンプトと同じロジック）
                            if '\n' in fallback_message.strip():
                                self.status_queue.put("📝 複数行フォールバックメッセージをJavaScriptで設定中...")
                                # JavaScriptでvalueを直接設定
                                escaped_text = fallback_message.strip().replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                                self.tool.driver.execute_script(f'arguments[0].value = "{escaped_text}";', text_input)
                                # inputイベントを発火
                                self.tool.driver.execute_script('arguments[0].dispatchEvent(new Event("input", { bubbles: true }));', text_input)
                            else:
                                text_input.send_keys(fallback_message.strip())
                                
                            self.status_queue.put("📤 フォールバック送信中...")
                            
                            # 確実な送信実行（複数の方法を順次試行）
                            from selenium.webdriver.common.keys import Keys
                            
                            send_success = False
                            
                            # 方法1: 送信ボタンクリック
                            submit_button = self.tool.find_submit_button()
                            self.status_queue.put(f"🔍 [DEBUG] 送信ボタン検出結果: {submit_button} (型: {type(submit_button)})")
                            
                            if submit_button and submit_button != "ENTER_KEY":
                                try:
                                    submit_button.click()
                                    self.status_queue.put("🔍 [DEBUG] 方法1: ボタンクリックで送信実行")
                                    send_success = True
                                except Exception as e:
                                    self.status_queue.put(f"⚠️ [DEBUG] 方法1失敗: {e}")
                            
                            # 方法2: textarea専用送信（Shift+Enter）
                            if not send_success:
                                try:
                                    # textareaの場合はShift+Enterを試す
                                    if text_input.tag_name == "textarea":
                                        text_input.send_keys(Keys.SHIFT + Keys.RETURN)
                                        self.status_queue.put("🔍 [DEBUG] 方法2: Shift+Enterキーで送信実行")
                                    else:
                                        text_input.send_keys(Keys.RETURN)
                                        self.status_queue.put("🔍 [DEBUG] 方法2: Enterキーで送信実行")
                                    send_success = True
                                except Exception as e:
                                    self.status_queue.put(f"⚠️ [DEBUG] 方法2失敗: {e}")
                            
                            # 方法2.5: Ctrl+Enter
                            if not send_success:
                                try:
                                    text_input.send_keys(Keys.CONTROL + Keys.RETURN)
                                    self.status_queue.put("🔍 [DEBUG] 方法2.5: Ctrl+Enterキーで送信実行")
                                    send_success = True
                                except Exception as e:
                                    self.status_queue.put(f"⚠️ [DEBUG] 方法2.5失敗: {e}")
                            
                            # 方法3: JavaScript強制送信（FormSubmit）
                            if not send_success:
                                try:
                                    # フォーム要素を探して送信
                                    from selenium.webdriver.common.by import By
                                    form_element = text_input.find_element(By.XPATH, "./ancestor-or-self::form")
                                    self.tool.driver.execute_script("arguments[0].submit();", form_element)
                                    self.status_queue.put("🔍 [DEBUG] 方法3: JavaScript form.submit()で送信実行")
                                    send_success = True
                                except Exception as e:
                                    self.status_queue.put(f"⚠️ [DEBUG] 方法3失敗: {e}")
                            
                            # 方法4: JavaScript Enterキーイベント発火
                            if not send_success:
                                try:
                                    self.tool.driver.execute_script("""
                                        const input = arguments[0];
                                        const event = new KeyboardEvent('keypress', {
                                            key: 'Enter',
                                            code: 'Enter',
                                            keyCode: 13,
                                            which: 13,
                                            bubbles: true,
                                            cancelable: true
                                        });
                                        input.dispatchEvent(event);
                                    """, text_input)
                                    self.status_queue.put("🔍 [DEBUG] 方法4: JavaScriptキーボードイベントで送信実行")
                                    send_success = True
                                except Exception as e:
                                    self.status_queue.put(f"⚠️ [DEBUG] 方法4失敗: {e}")
                            
                            if not send_success:
                                self.status_queue.put("❌ [ERROR] すべての送信方法が失敗しました")
                            else:
                                self.status_queue.put("✅ [DEBUG] フォールバック送信完了")
                            
                            # 少し待機してから応答をチェック（短縮）
                            self.status_queue.put("⏳ 送信後3秒待機中...")
                            time.sleep(3)
                            
                            # 送信後のページ要素数確認
                            from selenium.webdriver.common.by import By
                            post_send_elements = self.tool.driver.find_elements(By.CSS_SELECTOR, "[message-content-id]")
                            self.status_queue.put(f"🔍 [DEBUG] 送信後のmessage-content要素数: {len(post_send_elements)}")
                            
                            # 簡潔な応答取得（ストリーミング待機をスキップ）
                            self.status_queue.put("⏳ フォールバック応答を取得中...")
                            fallback_response_text = self.tool.get_latest_message_content(wait_for_streaming=False)
                            self.status_queue.put(f"🔍 [DEBUG] 初回応答取得結果: {bool(fallback_response_text)}")
                            
                            # 応答が取得できない場合は少し待ってもう一度試す
                            if not fallback_response_text:
                                self.status_queue.put("⏳ 応答なし - 2秒追加待機...")
                                time.sleep(2)
                                fallback_response_text = self.tool.get_latest_message_content(wait_for_streaming=False)
                                self.status_queue.put(f"🔍 [DEBUG] 2回目応答取得結果: {bool(fallback_response_text)}")
                            
                            if isinstance(fallback_response_text, tuple):
                                # タプルの場合は2番目の要素（応答テキスト）を取得
                                fallback_response_text = fallback_response_text[1]
                                
                            # フォールバック応答の詳細ログ（マスキング済み）
                            masked_response = self.mask_response_for_debug(fallback_response_text)
                            self.status_queue.put(f"🔍 [DEBUG] フォールバック応答取得: {masked_response}")
                            self.status_queue.put(f"🔍 [DEBUG] エラーメッセージ含有: {'応答の生成中にエラーが発生' in fallback_response_text if fallback_response_text else False}")
                            
                            if fallback_response_text and "応答の生成中にエラーが発生" not in fallback_response_text:
                                # フォールバック後に再生成ボタンが表示されていないかチェック
                                self.status_queue.put("🔍 [DEBUG] 2秒待機してから再生成ボタンをチェック...")
                                time.sleep(2)  # 少し待機してから再生成ボタンをチェック
                                regenerate_button = self.tool.find_regenerate_button()
                                self.status_queue.put(f"🔍 [DEBUG] 再生成ボタン検出結果: {bool(regenerate_button)}")
                                
                                # 初回フォールバック成功の場合も応答内容を検証
                                if not regenerate_button:
                                    # 応答内容の検証（連続フォールバック処理と同じロジック）
                                    response_length = len(fallback_response_text.strip())
                                    fallback_prefix = fallback_message.strip()[:20]
                                    is_not_echo = fallback_prefix not in fallback_response_text
                                    
                                    self.status_queue.put(f"🔍 [DEBUG] 応答検証: 長さ={response_length}>20, エコーでない={is_not_echo}")
                                    self.status_queue.put(f"🔍 [DEBUG] フォールバックプレフィクス: '{fallback_prefix}'")
                                    
                                    # 初回フォールバック成功判定を強化（100文字以上、簡単な応答除外）
                                    simple_responses = ["hello", "hi", "こんにちは", "ありがとう", "ok", "yes", "no"]
                                    is_simple = any(simple.lower() in fallback_response_text.lower() for simple in simple_responses) if fallback_response_text else True
                                    
                                    if (response_length > 100 and is_not_echo and not is_simple):
                                        self.status_queue.put("✅ 初回フォールバック成功 - 有効な応答を確認")
                                        self.response_queue.put(fallback_response_text)
                                    else:
                                        self.status_queue.put(f"⚠️ 初回フォールバック応答が不適切: {response_length}文字, エコーでない={is_not_echo}, 簡単応答={is_simple}")
                                        # 応答が不適切な場合は連続フォールバック処理に移行
                                        regenerate_button = True  # 強制的に連続処理モードに入る
                                        self.status_queue.put("🔍 [DEBUG] 強制的に連続フォールバック処理モードに移行")
                                
                                if regenerate_button:
                                    if isinstance(regenerate_button, bool) and regenerate_button:
                                        self.status_queue.put("⚠️ 応答検証失敗により連続フォールバック実行開始")
                                    else:
                                        self.status_queue.put("⚠️ フォールバック後も再生成ボタンが表示 - 連続フォールバック実行開始")
                                    self.status_queue.put(f"🔍 [DEBUG] regenerate_button値: {regenerate_button} (型: {type(regenerate_button)})")
                                    
                                    # 連続フォールバック処理を実行（最大20回まで）
                                    max_fallback_retries = getattr(self.tool, 'max_regenerate_retries', 20)
                                    self.status_queue.put(f"📋 最大フォールバックリトライ回数: {max_fallback_retries}回")
                                    
                                    fallback_success = False
                                    for retry_attempt in range(max_fallback_retries):
                                        self.status_queue.put(f"🔄 フォールバック再実行中 ({retry_attempt + 1}/{max_fallback_retries})...")
                                        
                                        # 再度フォールバックメッセージを送信
                                        self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: テキスト入力フィールドを検索中...")
                                        text_input = self.tool.find_text_input()
                                        if text_input:
                                            self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: テキスト入力フィールド取得成功")
                                            # 送信前に現在の応答数を記録（新しい応答検出用）
                                            from selenium.webdriver.common.by import By
                                            current_message_elements = self.tool.driver.find_elements(By.CSS_SELECTOR, "[message-content-id]")
                                            pre_send_message_count = len(current_message_elements)
                                            self.status_queue.put(f"📊 送信前message-content要素数: {pre_send_message_count}")
                                            
                                            # 送信前に現在の状態をリセット（元プロンプトは保持）
                                            self.tool.existing_response_count = self.tool.count_existing_responses()
                                            # リトライ時もcurrent_prompt_textのみ更新
                                            self.tool.current_prompt_text = fallback_message.strip()
                                            text_input.clear()
                                            
                                            if '\n' in fallback_message.strip():
                                                escaped_text = fallback_message.strip().replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                                                self.tool.driver.execute_script(f'arguments[0].value = "{escaped_text}";', text_input)
                                                self.tool.driver.execute_script('arguments[0].dispatchEvent(new Event("input", { bubbles: true }));', text_input)
                                            else:
                                                text_input.send_keys(fallback_message.strip())
                                                
                                            # 確実な送信実行（リトライ用）
                                            from selenium.webdriver.common.keys import Keys
                                            
                                            retry_send_success = False
                                            
                                            # 方法1: 送信ボタンクリック
                                            submit_button = self.tool.find_submit_button()
                                            self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 送信ボタン検出結果: {submit_button} (型: {type(submit_button)})")
                                            
                                            if submit_button and submit_button != "ENTER_KEY":
                                                try:
                                                    submit_button.click()
                                                    self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 方法1ボタンクリック成功")
                                                    retry_send_success = True
                                                except Exception as e:
                                                    self.status_queue.put(f"⚠️ [DEBUG] リトライ {retry_attempt + 1}: 方法1失敗: {e}")
                                            
                                            # 方法2: textarea専用送信
                                            if not retry_send_success:
                                                try:
                                                    if text_input.tag_name == "textarea":
                                                        text_input.send_keys(Keys.SHIFT + Keys.RETURN)
                                                        self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 方法2Shift+Enter成功")
                                                    else:
                                                        text_input.send_keys(Keys.RETURN)
                                                        self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 方法2Enter成功")
                                                    retry_send_success = True
                                                except Exception as e:
                                                    self.status_queue.put(f"⚠️ [DEBUG] リトライ {retry_attempt + 1}: 方法2失敗: {e}")
                                            
                                            # 方法2.5: Ctrl+Enter
                                            if not retry_send_success:
                                                try:
                                                    text_input.send_keys(Keys.CONTROL + Keys.RETURN)
                                                    self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 方法2.5Ctrl+Enter成功")
                                                    retry_send_success = True
                                                except Exception as e:
                                                    self.status_queue.put(f"⚠️ [DEBUG] リトライ {retry_attempt + 1}: 方法2.5失敗: {e}")
                                            
                                            # 方法3: JavaScript Enterキーイベント
                                            if not retry_send_success:
                                                try:
                                                    self.tool.driver.execute_script("""
                                                        const input = arguments[0];
                                                        const event = new KeyboardEvent('keypress', {
                                                            key: 'Enter',
                                                            code: 'Enter',
                                                            keyCode: 13,
                                                            which: 13,
                                                            bubbles: true,
                                                            cancelable: true
                                                        });
                                                        input.dispatchEvent(event);
                                                    """, text_input)
                                                    self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 方法3JavaScript成功")
                                                    retry_send_success = True
                                                except Exception as e:
                                                    self.status_queue.put(f"⚠️ [DEBUG] リトライ {retry_attempt + 1}: 方法3失敗: {e}")
                                            
                                            if not retry_send_success:
                                                self.status_queue.put(f"❌ [ERROR] リトライ {retry_attempt + 1}: すべての送信方法が失敗")
                                            
                                            # ランダム待機時間（1-5秒）
                                            import random
                                            wait_time = random.uniform(1, 5)
                                            self.status_queue.put(f"⏳ ランダム待機: {wait_time:.1f}秒")
                                            time.sleep(wait_time)
                                            
                                            # 再生成ボタンが消えたかチェック
                                            self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 再生成ボタンの状態をチェック中...")
                                            regenerate_button_check = self.tool.find_regenerate_button()
                                            self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 再生成ボタン検出結果: {bool(regenerate_button_check)}")
                                            
                                            if not regenerate_button_check:
                                                # 再生成ボタンが消えた - 新しい応答が追加されたかチェック
                                                current_message_elements = self.tool.driver.find_elements(By.CSS_SELECTOR, "[message-content-id]")
                                                post_send_message_count = len(current_message_elements)
                                                self.status_queue.put(f"📊 送信後message-content要素数: {post_send_message_count} (送信前: {pre_send_message_count})")
                                                
                                                if post_send_message_count > pre_send_message_count:
                                                    # 新しい応答が追加された
                                                    final_fallback_response = self.tool.get_latest_message_content(wait_for_streaming=False)
                                                    if isinstance(final_fallback_response, tuple):
                                                        final_fallback_response = final_fallback_response[1]
                                                    
                                                                    # 応答内容の検証を強化（デバッグログ付き）
                                                    final_masked = self.mask_response_for_debug(final_fallback_response)
                                                    self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 最終応答 = {final_masked}")
                                                    
                                                    has_error = "応答の生成中にエラーが発生" in final_fallback_response if final_fallback_response else False
                                                    is_long_enough = len(final_fallback_response.strip()) > 50 if final_fallback_response else False
                                                    is_not_echo = fallback_message.strip()[:20] not in final_fallback_response if final_fallback_response else False
                                                    
                                                    self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: エラーなし={not has_error}, 十分な長さ={is_long_enough}, エコーでない={is_not_echo}")
                                                    
                                                    # フォールバック再実行成功判定を強化（150文字以上、簡単応答除外）
                                                    simple_responses = ["hello", "hi", "こんにちは", "ありがとう", "ok", "yes", "no"]
                                                    is_simple_retry = any(simple.lower() in final_fallback_response.lower() for simple in simple_responses) if final_fallback_response else True
                                                    is_long_enough_retry = len(final_fallback_response.strip()) > 150 if final_fallback_response else False
                                                    
                                                    self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 長さ十分={is_long_enough_retry}, 簡単応答でない={not is_simple_retry}")
                                                    
                                                    if (final_fallback_response and not has_error and is_long_enough_retry and is_not_echo and not is_simple_retry):
                                                        
                                                        self.status_queue.put(f"✅ フォールバック再実行成功: 新しい応答を検出 ({retry_attempt + 1}回目)")
                                                        self.response_queue.put(final_fallback_response)
                                                        fallback_success = True
                                                        break
                                                    else:
                                                        response_length = len(final_fallback_response.strip()) if final_fallback_response else 0
                                                        self.status_queue.put(f"⚠️ 新しい応答はあるが内容が不適切 ({retry_attempt + 1}回目): {response_length}文字")
                                                else:
                                                    self.status_queue.put(f"⚠️ 再生成ボタンは消えたが新しい応答が追加されていない ({retry_attempt + 1}回目)")
                                            else:
                                                self.status_queue.put(f"⚠️ フォールバック再実行 {retry_attempt + 1} 回目: まだ再生成ボタンが表示中")
                                                self.status_queue.put(f"🔍 [DEBUG] リトライ {retry_attempt + 1}: 次のリトライに進みます")
                                        else:
                                            self.status_queue.put(f"❌ [DEBUG] リトライ {retry_attempt + 1}: テキスト入力フィールドが見つからない - リトライ終了")
                                            break
                                        
                                        # ループが完了したかチェック（break で抜けた場合はこの処理は実行されない）
                                        if retry_attempt == max_fallback_retries - 1:  # 最後の試行
                                            self.status_queue.put(f"❌ {max_fallback_retries}回のフォールバック再実行がすべて失敗")
                                    
                                    # ループ終了後の処理
                                    if not fallback_success:
                                        self.status_queue.put("📝 デフォルトフォールバックメッセージを表示")
                                        self.response_queue.put(fallback_message.strip())
                                # else文は削除 - 初回フォールバック成功時の処理は上記で実装済み
                            else:
                                self.status_queue.put("⚠️ フォールバック送信も失敗 - メッセージを表示")
                                self.response_queue.put(fallback_message.strip())
                        else:
                            self.status_queue.put("❌ テキスト入力フィールドが見つからない")
                            self.response_queue.put(fallback_message.strip())
                            
                    except Exception as fallback_error:
                        self.status_queue.put(f"❌ フォールバック送信エラー: {str(fallback_error)}")
                        self.response_queue.put(fallback_message.strip())
                else:
                    error_msg = response_text if response_text else "応答の取得に失敗しました"
                    self.status_queue.put("❌ 応答取得失敗")
                    self.response_queue.put(error_msg)
                
        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            self.status_queue.put(f"❌ {error_msg}")
            
            if use_fallback and fallback_message.strip():
                self.response_queue.put(fallback_message.strip())
                self.status_queue.put("⚠️ フォールバックメッセージを使用")
            else:
                self.response_queue.put(error_msg)
                
        finally:
            self.is_running = False
            # Chromeを閉じずに維持
            self.status_queue.put("プロンプト処理完了（Chrome維持中）")
    
    def stop_automation(self):
        """自動化を停止（Chromeも終了）"""
        if not self.is_running and not self.chrome_initialized:
            return "待機中です", "待機中"
            
        self.is_running = False
        if self.tool and self.tool.driver:
            try:
                self.tool.driver.quit()
                self.chrome_initialized = False
                self.tool = None
            except:
                pass
                
        return "🛑 自動化を停止し、Chromeを終了しました", "停止"
    
    def get_status_update(self):
        """ステータス更新を取得"""
        try:
            status = self.status_queue.get_nowait()
            return status
        except queue.Empty:
            return "待機中" if not self.is_running else "実行中"
    
    def get_response_update(self):
        """応答更新を取得"""
        try:
            response = self.response_queue.get_nowait()
            return response
        except queue.Empty:
            return ""

def create_interface():
    """Gradioインターフェースを作成"""
    gui = AutomationGUI()
    
    with gr.Blocks(title="Chrome自動操作ツール", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🤖 Chrome自動操作ツール")
        gr.Markdown("AI chat applications向けの自動化ツール")
        
        with gr.Row():
            with gr.Column(scale=2):
                # URL入力
                url_input = gr.Textbox(
                    label="📍 URL",
                    value="https://www.genspark.ai/agents?type=moa_chat",
                    placeholder="移動先URL（空白でデフォルト）"
                )
                
                # プロンプト入力
                prompt_input = gr.Textbox(
                    label="💬 プロンプト",
                    lines=4,
                    placeholder="送信するプロンプトを入力してください..."
                )
                
                # フォールバック設定
                with gr.Row():
                    use_fallback = gr.Checkbox(
                        label="フォールバックメッセージを使用",
                        value=False
                    )
                    retry_count = gr.Number(
                        label="最大リトライ回数",
                        value=20,
                        minimum=1,
                        maximum=50
                    )
                
                fallback_input = gr.Textbox(
                    label="📝 フォールバックメッセージ",
                    lines=2,
                    placeholder="エラー時の代替メッセージ...",
                    visible=False
                )
                
                # フォールバックの表示/非表示制御
                use_fallback.change(
                    fn=lambda x: gr.update(visible=x),
                    inputs=[use_fallback],
                    outputs=[fallback_input]
                )
                
                # 制御ボタン
                with gr.Row():
                    start_btn = gr.Button("🚀 プロンプト送信", variant="primary")
                    stop_btn = gr.Button("🛑 停止", variant="stop")
            
            with gr.Column(scale=2):
                # ステータス表示
                status_display = gr.Textbox(
                    label="📊 ツールステータス",
                    value="待機中",
                    interactive=False
                )
                
                # 応答表示
                response_display = gr.Textbox(
                    label="📄 応答内容",
                    lines=15,
                    placeholder="応答がここに表示されます...",
                    interactive=False
                )
        
        # イベントハンドラー
        start_btn.click(
            fn=gui.start_automation,
            inputs=[url_input, prompt_input, use_fallback, fallback_input, retry_count],
            outputs=[status_display, response_display, status_display]
        )
        
        stop_btn.click(
            fn=gui.stop_automation,
            outputs=[status_display, status_display]
        )
        
        # 自動更新（1秒間隔）
        interface.load(
            fn=lambda: [gui.get_status_update(), gui.get_response_update()],
            outputs=[status_display, response_display],
            every=1
        )
    
    return interface

if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Chrome自動操作ツール Web GUI を起動中...")
    
    # インターフェース作成・起動
    interface = create_interface()
    interface.launch(
        server_name="127.0.0.1",  # localhostのみ
        server_port=7860,
        share=False,
        show_error=True
    )