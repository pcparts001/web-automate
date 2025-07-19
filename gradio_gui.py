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
            
            if success and response_text and "応答の生成中にエラーが発生" not in response_text:
                self.status_queue.put("✅ 応答受信完了")
                self.response_queue.put(response_text)
            else:
                # 失敗した場合またはエラーメッセージが含まれる場合の処理
                self.status_queue.put(f"⚠️ エラー検出: {response_text if response_text else 'None'}")
                
                if use_fallback and fallback_message.strip():
                    # フォールバックメッセージを自動送信
                    self.status_queue.put("🔄 フォールバックメッセージを自動送信中...")
                    
                    try:
                        # 直接テキスト入力と送信を実行（既存のロジックを使用）
                        self.status_queue.put("📝 フォールバックテキスト入力中...")
                        
                        # フォールバック送信前に状態をリセット
                        self.tool.existing_response_count = self.tool.count_existing_responses()
                        self.tool.current_prompt_text = fallback_message.strip()
                        
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
                            
                            # 送信
                            submit_button = self.tool.find_submit_button()
                            if submit_button == "ENTER_KEY":
                                from selenium.webdriver.common.keys import Keys
                                text_input.send_keys(Keys.RETURN)
                            elif submit_button:
                                submit_button.click()
                            
                            # 少し待機してから応答をチェック（短縮）
                            time.sleep(3)
                            
                            # 簡潔な応答取得（ストリーミング待機をスキップ）
                            self.status_queue.put("⏳ フォールバック応答を取得中...")
                            fallback_response_text = self.tool.get_latest_message_content(wait_for_streaming=False)
                            
                            # 応答が取得できない場合は少し待ってもう一度試す
                            if not fallback_response_text:
                                time.sleep(2)
                                fallback_response_text = self.tool.get_latest_message_content(wait_for_streaming=False)
                            
                            if isinstance(fallback_response_text, tuple):
                                # タプルの場合は2番目の要素（応答テキスト）を取得
                                fallback_response_text = fallback_response_text[1]
                                
                            if fallback_response_text and "応答の生成中にエラーが発生" not in fallback_response_text:
                                # フォールバック後に再生成ボタンが表示されていないかチェック
                                time.sleep(2)  # 少し待機してから再生成ボタンをチェック
                                regenerate_button = self.tool.find_regenerate_button()
                                
                                if regenerate_button:
                                    self.status_queue.put("⚠️ フォールバック後も再生成ボタンが表示 - 再度フォールバック実行")
                                    
                                    # 再度フォールバック処理を実行（最大2回まで）
                                    for retry_attempt in range(2):
                                        self.status_queue.put(f"🔄 フォールバック再実行中 ({retry_attempt + 1}/2)...")
                                        
                                        # 再度フォールバックメッセージを送信
                                        text_input = self.tool.find_text_input()
                                        if text_input:
                                            text_input.clear()
                                            
                                            if '\n' in fallback_message.strip():
                                                escaped_text = fallback_message.strip().replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                                                self.tool.driver.execute_script(f'arguments[0].value = "{escaped_text}";', text_input)
                                                self.tool.driver.execute_script('arguments[0].dispatchEvent(new Event("input", { bubbles: true }));', text_input)
                                            else:
                                                text_input.send_keys(fallback_message.strip())
                                                
                                            # 送信
                                            submit_button = self.tool.find_submit_button()
                                            if submit_button == "ENTER_KEY":
                                                from selenium.webdriver.common.keys import Keys
                                                text_input.send_keys(Keys.RETURN)
                                            elif submit_button:
                                                submit_button.click()
                                            
                                            time.sleep(3)
                                            
                                            # 再生成ボタンが消えたかチェック
                                            regenerate_button_check = self.tool.find_regenerate_button()
                                            if not regenerate_button_check:
                                                # 成功
                                                final_fallback_response = self.tool.get_latest_message_content(wait_for_streaming=False)
                                                if isinstance(final_fallback_response, tuple):
                                                    final_fallback_response = final_fallback_response[1]
                                                
                                                if final_fallback_response:
                                                    self.status_queue.put(f"✅ フォールバック再実行成功 ({retry_attempt + 1}回目)")
                                                    self.response_queue.put(final_fallback_response)
                                                    break
                                            else:
                                                self.status_queue.put(f"⚠️ フォールバック再実行 {retry_attempt + 1} 回目も失敗")
                                        
                                        if retry_attempt == 1:  # 最後の試行
                                            self.status_queue.put("❌ フォールバック再実行も失敗 - デフォルトメッセージを表示")
                                            self.response_queue.put(fallback_message.strip())
                                else:
                                    self.status_queue.put("✅ フォールバック応答受信完了")
                                    self.response_queue.put(fallback_response_text)
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