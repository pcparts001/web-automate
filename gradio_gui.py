#!/usr/bin/env python3
"""
Chrome自動操作ツール - Gradio Web GUI
"""

import gradio as gr
import threading
import time
import queue
import logging
import random
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
            # 長いテキストは先頭6文字のみ表��
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
            # プロンプト送信回数をカウント（Chrome初期化時にリセット）
            if not hasattr(self, 'prompt_count'):
                self.prompt_count = 0
            self.prompt_count += 1
            
            # --- パラメータのログ出力 ---
            logging.info("=" * 60)
            logging.info(f"🚀 ユーザからのプロンプト {self.prompt_count}回目 送信開始")
            logging.info("=" * 60)
            logging.info("--- Gradioからのパラメータ ---")
            logging.info(f"use_fallback: {use_fallback} (type: {type(use_fallback)})")
            logging.info(f"fallback_message: '{fallback_message}'")
            logging.info("--------------------------")

            # Chrome初期化（初回のみ）
            if not self.chrome_initialized:
                self.status_queue.put("Chrome起動中...")
                self.tool = ChromeAutomationTool(debug=True)
                if not self.tool.launch_chrome():
                    self.status_queue.put("❌ Chrome起動に失敗")
                    self.response_queue.put("Chrome起動に失敗しました")
                    return
                self.chrome_initialized = True
                self.prompt_count = 0  # Chrome初期化時にカウントリセット
                self.status_queue.put("Chrome初期化完了")
                
            # URLナビゲーション
            default_url = "https://www.genspark.ai/agents?type=moa_chat"
            if url.strip() and url.strip() != default_url and self.tool.driver.current_url != url.strip():
                self.status_queue.put(f"URLに移動中: {url}")
                self.tool.driver.get(url.strip())
                time.sleep(3)
            
            self.status_queue.put("ページ準備完了、プロンプト処理開始...")
            
            # retry_countを設定
            if hasattr(self.tool, 'max_regenerate_retries'):
                self.tool.max_regenerate_retries = max(1, int(retry_count))
            
            # 初回プロンプト処理
            success, response_text = self.tool.process_single_prompt(prompt_text)
            
            if (success and response_text and response_text != "REGENERATE_ERROR_DETECTED"):
                self.status_queue.put("✅ 応答受信完了")
                self.response_queue.put(response_text)
            else:
                # エラーまたは再生成が必要な場合
                if response_text == "REGENERATE_ERROR_DETECTED":
                    self.status_queue.put("⚠️ 再生成ボタンを検出 - フォールバック処理を開始")
                else:
                    self.status_queue.put(f"⚠️ エラー検出: {response_text if response_text else 'None'}")
                
                if not (use_fallback and fallback_message.strip()):
                    self.status_queue.put("❌ フォールバックが無効なため処理終了")
                    self.response_queue.put(response_text or "フォールバックが無効です。")
                    return

                # --- ここから連続フォールバック処理 ---
                self.status_queue.put("🔄 連続フォールバック処理を開始します...")
                max_fallback_retries = getattr(self.tool, 'max_regenerate_retries', 20)
                fallback_success = False

                for attempt in range(max_fallback_retries):
                    self.status_queue.put(f"--- リトライ {attempt + 1}/{max_fallback_retries} ---")
                    
                    # 統一された送信メソッドでフォールバックメッセージを送信
                    self.tool.current_prompt_text = fallback_message.strip() # ログ記録用
                    if not self.tool.send_message(fallback_message.strip()):
                        self.status_queue.put("❌ フォールバ��クメッセージの送信に失敗")
                        time.sleep(2) # 次の試行まで少し待つ
                        continue

                    self.status_queue.put("⏳ 送信後、応答を待機中...")
                    time.sleep(5) # 応答生成のための初期待機時間

                    # より長い待機時間でストリーミング応答の完了を待つ
                    self.status_queue.put("⏳ ストリーミング完了を待機中...")
                    time.sleep(8) # 追加待機でストリーミング応答を確実に取得

                    # 応答をチェック
                    final_response = self.tool.get_response_text()

                    if final_response == "REGENERATE_ERROR_DETECTED":
                        # フォールバック後にも再生成ボタンが表示された場合
                        self.status_queue.put(f"⚠️ フォールバック後も再生成ボタンが表示されました ({attempt + 1}回目)")
                        # 次のリトライまでランダム待機時間
                        wait_time = random.randint(1, 5)
                        time.sleep(wait_time)
                        continue  # 次のリトライループへ
                    elif final_response and final_response != "REGENERATE_ERROR_DETECTED":
                        # 正常な応答を受信した場合
                        is_long_enough = len(final_response.strip()) > 100
                        is_not_echo = fallback_message.strip()[:20] not in final_response
                        
                        if is_long_enough and is_not_echo:
                            self.status_queue.put(f"✅ フォールバック成功！ ({attempt + 1}回目)")
                            self.response_queue.put(final_response)
                            
                            # フォールバック成功時に応答をMarkdownファイルに保存
                            try:
                                filepath = self.tool.save_to_markdown(final_response, self.tool.original_user_prompt or prompt_text)
                                self.status_queue.put(f"📁 応答をMarkdownファイルに保存しました: {filepath}")
                                self.tool.logger.info(f"フォールバック成功応答をファイルに保存: {filepath}")
                            except Exception as save_error:
                                self.tool.logger.error(f"フォールバック応答の保存中にエラー: {save_error}")
                                self.status_queue.put(f"⚠️ ファイル保存エラー: {save_error}")
                            
                            fallback_success = True
                            break
                        else:
                            self.status_queue.put(f"⚠️ 応答が不適切 (長さ: {len(final_response.strip())}, エコーでない: {is_not_echo})")
                    else:
                        # 応答が取得できない場合
                        self.status_queue.put(f"⚠️ 応答が取得できませんでした ({attempt + 1}回目)")

                if not fallback_success:
                    self.status_queue.put(f"❌ {max_fallback_retries}回のフォールバックリトライがすべて失敗しました。")
                    self.response_queue.put(fallback_message.strip()) # 最終手段としてフォールバックメッセージを表示

        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            self.status_queue.put(f"❌ {error_msg}")
            self.response_queue.put(fallback_message.strip() if use_fallback else error_msg)
                
        finally:
            self.is_running = False
            logging.info("=" * 60)
            logging.info(f"✅ ユーザプロンプト {getattr(self, 'prompt_count', '?')}回目 処理完了")
            logging.info("=" * 60)
            self.status_queue.put("プロンプト処理完了（Chrome維持中）")
    
    def stop_automation(self):
        """自動化を停止（Chromeも終了）"""
        if not self.is_running and not self.chrome_initialized:
            return "待機中です", "待機中"
            
        self.is_running = False
        if self.tool and self.tool.driver:
            try:
                self.tool.driver.quit()
            except:
                pass
        self.chrome_initialized = False
        self.tool = None
                
        return "🛑 自動化を停止し、Chromeを終了しました", "停止"
    
    def get_status_update(self):
        """ステータス更新を取得"""
        try:
            return self.status_queue.get_nowait()
        except queue.Empty:
            return "待機中" if not self.is_running else "実行中"
    
    def get_response_update(self):
        """応答更新を取得"""
        try:
            return self.response_queue.get_nowait()
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
                url_input = gr.Textbox(label="📍 URL", value="https://www.genspark.ai/agents?type=moa_chat", placeholder="移動先URL（空白でデフォルト）")
                prompt_input = gr.Textbox(label="💬 プロンプト", lines=4, placeholder="送信するプロンプトを入力してください...")
                
                with gr.Row():
                    use_fallback = gr.Checkbox(label="フォールバックメッセージを使用", value=True)
                    retry_count = gr.Number(label="最大リトライ回数", value=20, minimum=1, maximum=50)
                
                fallback_input = gr.Textbox(label="📝 フォールバックメッセージ", lines=2, placeholder="エラー時の代替メッセージ...", visible=True)
                
                use_fallback.change(fn=lambda x: gr.update(visible=x), inputs=[use_fallback], outputs=[fallback_input])
                
                with gr.Row():
                    start_btn = gr.Button("🚀 プロンプト送信", variant="primary")
                    stop_btn = gr.Button("🛑 停止", variant="stop")
            
            with gr.Column(scale=2):
                status_display = gr.Textbox(label="📊 ツールステータス", value="待機中", interactive=False)
                response_display = gr.Textbox(label="📄 応答内容", lines=15, placeholder="応答がここに表示されます...", interactive=False)
        
        start_btn.click(
            fn=gui.start_automation,
            inputs=[url_input, prompt_input, use_fallback, fallback_input, retry_count],
            outputs=[status_display, response_display, status_display]
        )
        
        stop_btn.click(fn=gui.stop_automation, outputs=[status_display, status_display])
        
        interface.load(
            fn=lambda: (gui.get_status_update(), gui.get_response_update()),
            outputs=[status_display, response_display],
            every=1
        )
    
    return interface

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("🚀 Chrome��動操作ツール Web GUI を起動中...")
    interface = create_interface()
    interface.launch(server_name="127.0.0.1", server_port=7860, share=False, show_error=True)