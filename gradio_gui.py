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
import json
import os
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
        self.settings_file = "gui_settings.json"
        
        # プロンプトフロー状態管理
        self.current_prompt_type = None
        self.current_bc_cycle = 0
        self.max_bc_cycles = 0
        
        # 設定をロード
        self.settings = self.load_settings()
        
        # メモリ内設定の強制クリーンアップ（旧キー削除）
        self._cleanup_memory_settings()
    
    def _cleanup_memory_settings(self):
        """メモリ内設定から旧構造のキーを削除"""
        old_keys_to_remove = [
            "prompt_a", "prompt_b", "prompt_c",
            "prompt_a_list", "prompt_b_list", "prompt_c_list", 
            "use_list_a", "use_list_b", "use_list_c"
        ]
        keys_removed = []
        for key in old_keys_to_remove:
            if key in self.settings:
                del self.settings[key]
                keys_removed.append(key)
        
        if keys_removed:
            print(f"[DEBUG] メモリ内旧キー削除: {keys_removed}")
            print(f"[DEBUG] クリーンアップ後キー一覧: {list(self.settings.keys())}")
    
    def load_settings(self):
        """設定ファイルから設定をロード（prompt_sets構造対応）"""
        print(f"[DEBUG] load_settings() 開始")
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    print(f"設定ファイルをロードしました: {self.settings_file}")
                    print(f"[DEBUG] ファイル読み込み後のキー一覧: {list(settings.keys())}")
                    print(f"[DEBUG] ファイル内active_prompt_set: {settings.get('active_prompt_set', 'NOT_FOUND')}")
                    
                    # Stage 4: prompt_sets構造への移行チェック
                    if "prompt_sets" not in settings:
                        print("Stage 4: 旧構造から新構造（prompt_sets）に移行中...")
                        settings = self._migrate_to_prompt_sets(settings)
                        print(f"[DEBUG] 移行後active_prompt_set: {settings.get('active_prompt_set', 'NOT_FOUND')}")
                    else:
                        print(f"[DEBUG] prompt_sets構造確認済み - 旧キーチェック開始")
                        # 新構造でも旧キーが残っている場合のクリーンアップ
                        old_keys_to_remove = [
                            "prompt_a", "prompt_b", "prompt_c",
                            "prompt_a_list", "prompt_b_list", "prompt_c_list", 
                            "use_list_a", "use_list_b", "use_list_c"
                        ]
                        keys_found = [key for key in old_keys_to_remove if key in settings]
                        print(f"[DEBUG] ファイル内検出された旧キー: {keys_found}")
                        
                        keys_removed = []
                        for key in old_keys_to_remove:
                            if key in settings:
                                del settings[key]
                                keys_removed.append(key)
                        
                        if keys_removed:
                            print(f"[DEBUG] 読み込み時旧キー削除: {keys_removed}")
                            print(f"[DEBUG] 削除前active_prompt_set: {settings.get('active_prompt_set', 'NOT_FOUND')}")
                            # クリーンアップ後再保存
                            try:
                                with open(self.settings_file, 'w', encoding='utf-8') as f:
                                    json.dump(settings, f, ensure_ascii=False, indent=2)
                                print(f"✅ 設定ファイルクリーンアップ完了")
                                print(f"[DEBUG] 保存後active_prompt_set: {settings.get('active_prompt_set', 'NOT_FOUND')}")
                            except Exception as e:
                                print(f"❌ クリーンアップ保存エラー: {e}")
                        else:
                            print(f"[DEBUG] 旧キーなし - クリーンアップ不要")
                    
                    print(f"[DEBUG] load_settings() 戻り値のactive_prompt_set: {settings.get('active_prompt_set', 'NOT_FOUND')}")
                    print(f"[DEBUG] load_settings() 戻り値のキー一覧: {list(settings.keys())}")
                    return settings
        except Exception as e:
            print(f"設定ファイルの読み込みエラー: {e}")
        
        # デフォルト設定（新構造）
        print(f"[DEBUG] デフォルト設定を返します")
        default_settings = self._get_default_prompt_sets_settings()
        print(f"[DEBUG] デフォルト設定のactive_prompt_set: {default_settings.get('active_prompt_set', 'NOT_FOUND')}")
        return default_settings
    
    def _get_default_prompt_sets_settings(self):
        """prompt_sets構造のデフォルト設定"""
        return {
            "fallback_message": "",
            "url": "https://www.genspark.ai/agents?type=moa_chat",
            "bc_loop_count": 0,
            "active_prompt_set": "デフォルト",
            "prompt_sets": {
                "デフォルト": {
                    "prompt_a": "",
                    "prompt_b": "",
                    "prompt_c": "",
                    "prompt_a_list": [],
                    "prompt_b_list": [],
                    "prompt_c_list": [],
                    "use_list_a": False,
                    "use_list_b": False,
                    "use_list_c": False
                }
            },
            "active_prompt_set": "デフォルト"
        }
    
    def _migrate_to_prompt_sets(self, old_settings):
        """旧構造から新構造（prompt_sets）への移行"""
        print("データ構造を移行中...")
        
        # 新構造のベース作成
        new_settings = self._get_default_prompt_sets_settings()
        
        # 共通設定移行（active_prompt_set含む）
        new_settings["fallback_message"] = old_settings.get("fallback_message", "")
        new_settings["url"] = old_settings.get("url", "https://www.genspark.ai/agents?type=moa_chat")
        new_settings["bc_loop_count"] = old_settings.get("bc_loop_count", 0)
        new_settings["active_prompt_set"] = old_settings.get("active_prompt_set", "デフォルト")
        
        # プロンプト関連を「デフォルト」セットに移行
        default_set = new_settings["prompt_sets"]["デフォルト"]
        default_set["prompt_a"] = old_settings.get("prompt_a", "")
        default_set["prompt_b"] = old_settings.get("prompt_b", "")
        default_set["prompt_c"] = old_settings.get("prompt_c", "")
        default_set["prompt_a_list"] = old_settings.get("prompt_a_list", [])
        default_set["prompt_b_list"] = old_settings.get("prompt_b_list", [])
        default_set["prompt_c_list"] = old_settings.get("prompt_c_list", [])
        default_set["use_list_a"] = old_settings.get("use_list_a", False)
        default_set["use_list_b"] = old_settings.get("use_list_b", False)
        default_set["use_list_c"] = old_settings.get("use_list_c", False)
        
        # 旧構造のキーを完全に削除（移行後の混在回避）
        old_keys_to_remove = [
            "prompt_a", "prompt_b", "prompt_c",
            "prompt_a_list", "prompt_b_list", "prompt_c_list", 
            "use_list_a", "use_list_b", "use_list_c"
        ]
        for key in old_keys_to_remove:
            if key in new_settings:
                del new_settings[key]
                print(f"[DEBUG] 旧構造キー削除: {key}")
        
        # 移行後保存
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(new_settings, f, ensure_ascii=False, indent=2)
            print(f"✅ prompt_sets構造への移行完了（旧キー削除済み): {self.settings_file}")
        except Exception as e:
            print(f"❌ 移行後保存エラー: {e}")
        
        return new_settings
    
    def save_settings(self, **kwargs):
        """設定をファイルに保存"""
        try:
            # 現在の設定を更新
            self.settings.update(kwargs)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            print(f"設定を保存しました: {self.settings_file}")
            return "✅ 設定を保存しました"
        except Exception as e:
            error_msg = f"設定保存エラー: {e}"
            print(error_msg)
            return f"❌ {error_msg}"
    
    # Phase2: プロンプトリスト管理機能
    def add_to_list(self, prompt_type, new_prompt):
        """プロンプトをリストに追加"""
        if not new_prompt.strip():
            return f"❌ プロンプトが空です", self.get_list_display(prompt_type)
            
        # デバッグログ: 追加操作詳細
        current_active = self.settings.get("active_prompt_set", "unknown")
        print(f"[DEBUG] プロンプト{prompt_type.upper()}追加: アクティブセット='{current_active}', 追加内容='{new_prompt.strip()}'")
        
        # アクティブセットに追加
        active_set = self.get_active_prompt_set()
        list_key = f"prompt_{prompt_type}_list"
        
        if list_key not in active_set:
            active_set[list_key] = []
        
        old_count = len(active_set[list_key])    
        active_set[list_key].append(new_prompt.strip())
        new_count = len(active_set[list_key])
        print(f"[DEBUG] {prompt_type.upper()}リスト: {old_count}項目 → {new_count}項目")
        
        self.save_settings()
        
        return f"✅ プロンプト{prompt_type.upper()}リストに追加しました", self.get_list_display(prompt_type)
    
    def remove_from_list(self, prompt_type, index):
        """プロンプトをリストから削除"""
        # アクティブセットから削除
        active_set = self.get_active_prompt_set()
        list_key = f"prompt_{prompt_type}_list"
        
        prompt_list = active_set.get(list_key, [])
        if not prompt_list:
            return f"❌ プロンプト{prompt_type.upper()}リストが空です", self.get_list_display(prompt_type)
            
        try:
            index = int(index)
            if 0 <= index < len(prompt_list):
                removed = prompt_list.pop(index)
                self.save_settings()
                return f"✅ 削除しました: {removed[:50]}...", self.get_list_display(prompt_type)
            else:
                return f"❌ インデックス {index} が範囲外です", self.get_list_display(prompt_type)
        except ValueError:
            return f"❌ 無効なインデックスです: {index}", self.get_list_display(prompt_type)
    
    def edit_list_item(self, prompt_type, index, new_content):
        """リスト項目を編集"""
        # アクティブセット内の項目を編集
        active_set = self.get_active_prompt_set()
        list_key = f"prompt_{prompt_type}_list"
        
        prompt_list = active_set.get(list_key, [])
        if not prompt_list:
            return f"❌ プロンプト{prompt_type.upper()}リストが空です", self.get_list_display(prompt_type)
            
        if not new_content.strip():
            return f"❌ 新しいプロンプトが空です", self.get_list_display(prompt_type)
            
        try:
            index = int(index)
            if 0 <= index < len(prompt_list):
                old_content = prompt_list[index]
                prompt_list[index] = new_content.strip()
                self.save_settings()
                return f"✅ 編集しました: {old_content[:30]}... → {new_content[:30]}...", self.get_list_display(prompt_type)
            else:
                return f"❌ インデックス {index} が範囲外です", self.get_list_display(prompt_type)
        except ValueError:
            return f"❌ 無効なインデックスです: {index}", self.get_list_display(prompt_type)
    
    def get_list_display(self, prompt_type):
        """リストの表示用文字列を取得"""
        # アクティブセットから取得
        active_set = self.get_active_prompt_set()
        list_key = f"prompt_{prompt_type}_list"
        
        prompt_list = active_set.get(list_key, [])
        if not prompt_list:
            return f"プロンプト{prompt_type.upper()}リスト: (空)"
        
        items = []
        for i, prompt in enumerate(prompt_list):
            items.append(f"{i}: {prompt}")
        
        return f"プロンプト{prompt_type.upper()}リスト ({len(prompt_list)}件):\n" + "\n".join(items)
    
    def get_unified_list_display(self):
        """A/B/C統合リストの表示用文字列を取得（読み取り専用）"""
        all_items = []
        
        # アクティブセットから取得
        active_set = self.get_active_prompt_set()
        
        # プロンプトA
        list_a = active_set.get("prompt_a_list", [])
        for i, prompt in enumerate(list_a):
            all_items.append(f"A-{i}: {prompt}")
        
        # プロンプトB
        list_b = active_set.get("prompt_b_list", [])
        for i, prompt in enumerate(list_b):
            all_items.append(f"B-{i}: {prompt}")
        
        # プロンプトC
        list_c = active_set.get("prompt_c_list", [])
        for i, prompt in enumerate(list_c):
            all_items.append(f"C-{i}: {prompt}")
        
        total_count = len(list_a) + len(list_b) + len(list_c)
        
        if not all_items:
            return "📋 統合プロンプトリスト: (空)"
        
        header = f"📋 統合プロンプトリスト (合計 {total_count}件: A={len(list_a)}, B={len(list_b)}, C={len(list_c)}):"
        return header + "\n" + "\n".join(all_items)
    
    def add_to_unified_list(self, category, new_prompt):
        """統合リストに新しいプロンプトを追加（カテゴリ指定）"""
        if not new_prompt.strip():
            return f"❌ プロンプトが空です", self.get_unified_list_display()
        
        if category not in ["a", "b", "c"]:
            return f"❌ 無効なカテゴリです: {category}", self.get_unified_list_display()
            
        # 対応する個別リストメソッドを呼び出し
        result_msg, _ = self.add_to_list(category, new_prompt)
        
        return result_msg, self.get_unified_list_display()
    
    # Stage 3-4: プロンプトセット管理メソッド（新構造対応）
    def get_prompt_set_names(self):
        """利用可能なプロンプトセット名のリストを取得"""
        return list(self.settings.get("prompt_sets", {}).keys())
    
    def get_active_prompt_set(self):
        """アクティブなプロンプトセットを取得"""
        print(f"[DEBUG] get_active_prompt_set() 開始")
        active_set_name = self.settings.get("active_prompt_set", "デフォルト")
        print(f"[DEBUG] self.settingsから取得したactive_set_name: '{active_set_name}'")
        
        available_sets = list(self.settings.get("prompt_sets", {}).keys())
        print(f"[DEBUG] 利用可能なプロンプトセット: {available_sets}")
        
        if active_set_name not in self.settings.get("prompt_sets", {}):
            # アクティブセットが存在しない場合、デフォルトに設定
            print(f"[DEBUG] アクティブセット '{active_set_name}' が存在しません - デフォルトにフォールバック")
            active_set_name = "デフォルト"
            self.settings["active_prompt_set"] = active_set_name
        
        target_set = self.settings["prompt_sets"][active_set_name]
        print(f"[DEBUG] 返すセット名: '{active_set_name}'")
        print(f"[DEBUG] セット内容: A={len(target_set.get('prompt_a_list', []))}, B={len(target_set.get('prompt_b_list', []))}, C={len(target_set.get('prompt_c_list', []))}項目")
        
        return target_set
    
    def create_prompt_set(self, set_name):
        """新しいプロンプトセットを作成"""
        if not set_name or not set_name.strip():
            return "❌ セット名を入力してください"
        
        set_name = set_name.strip()
        
        # 設定を強制的に再読み込みしてUIとの同期を確保
        print(f"[DEBUG] セット作成前: 設定再読み込み実行")
        print(f"[DEBUG] 再読み込み前のself.settings active_prompt_set: {self.settings.get('active_prompt_set', 'unknown')}")
        print(f"[DEBUG] 再読み込み前のself.settingsキー一覧: {list(self.settings.keys())}")
        
        self.settings = self.load_settings()
        
        print(f"[DEBUG] 再読み込み後のself.settings active_prompt_set: {self.settings.get('active_prompt_set', 'unknown')}")
        print(f"[DEBUG] 再読み込み後のself.settingsキー一覧: {list(self.settings.keys())}")
        
        # **修正**: セット削除前に現在のアクティブセット内容を保存
        print(f"[DEBUG] セット削除前にアクティブセット内容を保存")
        active_set = self.get_active_prompt_set()
        print(f"[DEBUG] 保存したアクティブセット内容: A={len(active_set.get('prompt_a_list', []))}, B={len(active_set.get('prompt_b_list', []))}, C={len(active_set.get('prompt_c_list', []))}項目")
        
        # Stage 11b: 既存セット上書き機能（削除→新規作成方式）
        if set_name in self.settings.get("prompt_sets", {}):
            print(f"[DEBUG] 既存セット '{set_name}' を削除します")
            # 削除前にアクティブセット情報を保持
            was_active_set = (self.settings.get("active_prompt_set") == set_name)
            print(f"[DEBUG] 削除するセットがアクティブセット?: {was_active_set}")
            
            # 既存セットを削除してから新規作成
            del self.settings["prompt_sets"][set_name]
            
            # アクティブセットだった場合、一時的にデフォルトに変更
            if was_active_set:
                print(f"[DEBUG] アクティブセットを一時的に'デフォルト'に変更")
                self.settings["active_prompt_set"] = "デフォルト"
            
            overwrite_message = f"（既存セット '{set_name}' を上書き）"
        else:
            overwrite_message = ""
        
        # **注意**: active_setは既に削除前に保存済み
        print(f"[DEBUG] 削除後の確認 - 保存済みアクティブセット内容を使用")
        print(f"[DEBUG] セット作成 '{set_name}' で使用する内容: A={len(active_set.get('prompt_a_list', []))}, B={len(active_set.get('prompt_b_list', []))}, C={len(active_set.get('prompt_c_list', []))}項目")
        
        # 新しいセットを現在の内容で初期化
        new_set = {
            "prompt_a": active_set.get("prompt_a", ""),
            "prompt_b": active_set.get("prompt_b", ""),
            "prompt_c": active_set.get("prompt_c", ""),
            "prompt_a_list": active_set.get("prompt_a_list", []).copy(),
            "prompt_b_list": active_set.get("prompt_b_list", []).copy(),
            "prompt_c_list": active_set.get("prompt_c_list", []).copy(),
            "use_list_a": active_set.get("use_list_a", False),
            "use_list_b": active_set.get("use_list_b", False),
            "use_list_c": active_set.get("use_list_c", False)
        }
        
        # prompt_setsに新しいセットを追加
        if "prompt_sets" not in self.settings:
            self.settings["prompt_sets"] = {}
        
        self.settings["prompt_sets"][set_name] = new_set
        
        # 上書きの場合、アクティブセットを復元
        if overwrite_message:  # 上書きの場合
            print(f"[DEBUG] セット作成後、アクティブセットを '{set_name}' に復元")
            self.settings["active_prompt_set"] = set_name
        
        # 設定を保存
        self.save_settings()
        
        # 作成後の確認
        print(f"[DEBUG] セット作成完了後のactive_prompt_set: {self.settings.get('active_prompt_set', 'unknown')}")
        print(f"[DEBUG] 利用可能セット一覧: {list(self.settings.get('prompt_sets', {}).keys())}")
        
        # コピーされた内容の統計
        total_items = (len(new_set["prompt_a_list"]) + 
                      len(new_set["prompt_b_list"]) + 
                      len(new_set["prompt_c_list"]))
        
        return f"✅ プロンプトセット '{set_name}' を作成しました{overwrite_message}\n📋 A/B/Cリスト内容をコピー（合計{total_items}項目）"
    
    def switch_prompt_set(self, set_name):
        """プロンプトセットを切り替え"""
        if not set_name or set_name not in self.settings.get("prompt_sets", {}):
            return f"❌ セット '{set_name}' が見つかりません"
        
        # デバッグログ: セット切り替え詳細
        old_active = self.settings.get("active_prompt_set", "unknown")
        print(f"[DEBUG] セット切り替え: '{old_active}' → '{set_name}'")
        
        # アクティブセットを変更
        self.settings["active_prompt_set"] = set_name
        print(f"[DEBUG] メモリ内設定更新: active_prompt_set='{self.settings.get('active_prompt_set', 'unknown')}'")
        
        # 保存前の詳細デバッグ
        print(f"[DEBUG] 保存前のself.settings内容抜粋: active_prompt_set='{self.settings.get('active_prompt_set', 'NOT_FOUND')}'")
        print(f"[DEBUG] settings辞書のキー一覧: {list(self.settings.keys())}")
        
        # 設定をファイルに保存
        self.save_settings()
        print(f"[DEBUG] 設定ファイル保存完了")
        
        # ファイル保存直後の内容確認
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                file_content = json.load(f)
                file_active = file_content.get("active_prompt_set", "NOT_FOUND_IN_FILE")
                print(f"[DEBUG] ファイル直読み確認: active_prompt_set='{file_active}'")
        except Exception as e:
            print(f"[DEBUG] ファイル直読みエラー: {e}")
        
        # 保存後の確認のため設定を再読み込み
        self.settings = self.load_settings()
        final_active = self.settings.get("active_prompt_set", "unknown")
        print(f"[DEBUG] ファイル保存確認: 再読み込み後のアクティブセット='{final_active}'")
        
        return f"✅ プロンプトセットを '{set_name}' に切り替えました"
    
    def delete_prompt_set(self, set_name):
        """プロンプトセットを削除"""
        if not set_name or not set_name.strip():
            return "❌ セット名が空です"
            
        set_name = set_name.strip()
        
        # デフォルトセットの削除を防止
        if set_name == "デフォルト":
            return "❌ 「デフォルト」セットは削除できません"
            
        # セットの存在確認
        if set_name not in self.settings.get("prompt_sets", {}):
            return f"❌ セット '{set_name}' が見つかりません"
            
        # 現在のアクティブセットが削除対象の場合はデフォルトに切り替え
        current_active = self.settings.get("active_prompt_set", "デフォルト")
        if current_active == set_name:
            self.settings["active_prompt_set"] = "デフォルト"
            
        # セットを削除
        del self.settings["prompt_sets"][set_name]
        self.save_settings()
        
        if current_active == set_name:
            return f"✅ セット '{set_name}' を削除し、アクティブセットを「デフォルト」に変更しました"
        else:
            return f"✅ セット '{set_name}' を削除しました"
    
    def get_random_prompt(self, prompt_type, fallback_prompt):
        """リストからランダムプロンプトを取得（統合プロンプトリスト対応）"""
        print(f"[DEBUG] get_random_prompt called: type={prompt_type}, fallback='{fallback_prompt[:30]}...'")
        
        # 統合プロンプトリストの現在アクティブなセットから取得
        active_set = self.get_active_prompt_set()
        use_list_key = f"use_list_{prompt_type}"
        list_key = f"prompt_{prompt_type}_list"
        
        print(f"[DEBUG] Active prompt set: {self.settings.get('active_prompt_set', 'デフォルト')}")
        print(f"[DEBUG] Use list setting ({use_list_key}): {active_set.get(use_list_key, False)}")
        
        # リストを使用する設定かつ、リストが空でない場合
        if (active_set.get(use_list_key, False) and 
            list_key in active_set and 
            active_set[list_key]):
            selected_prompt = random.choice(active_set[list_key])
            print(f"[DEBUG] Selected from list: '{selected_prompt[:30]}...'")
            return selected_prompt
        else:
            print(f"[DEBUG] Using fallback prompt: '{fallback_prompt[:30]}...'")
            return fallback_prompt
        
    def start_prompt_flow(self, url, prompt_a, prompt_b, prompt_c, use_fallback, fallback_message, retry_count, bc_loop_count):
        """プロンプトフロー自動化を開始"""
        if self.is_running:
            return "⚠️ 既に実行中です", "", "実行中"
            
        if not prompt_a.strip() or not prompt_b.strip() or not prompt_c.strip():
            return "❌ プロンプトA、B、Cすべてを入力してください", "", "待機中"
            
        self.is_running = True
        
        # プロンプトフロー状態を初期化
        self.current_prompt_type = None
        self.current_bc_cycle = 0
        self.max_bc_cycles = max(0, int(bc_loop_count))
        
        # バックグラウンドスレッドで実行
        self.current_thread = threading.Thread(
            target=self._run_prompt_flow,
            args=(url, prompt_a, prompt_b, prompt_c, use_fallback, fallback_message, retry_count, bc_loop_count),
            daemon=True
        )
        self.current_thread.start()
        
        return "🔄 プロンプトフローを開始しました", "", "実行中"
    
    def _run_prompt_flow(self, url, prompt_a, prompt_b, prompt_c, use_fallback, fallback_message, retry_count, bc_loop_count):
        """プロンプトフローのバックグラウンド実行"""
        try:
            # Chrome初期化
            if not self.chrome_initialized:
                self.status_queue.put("🌐 Chrome初期化中...")
                self.tool = ChromeAutomationTool()
                if not self.tool.launch_chrome():
                    self.status_queue.put("❌ Chrome起動に失敗")
                    self.response_queue.put("Chrome起動に失敗しました")
                    return
                self.chrome_initialized = True
                
            # URLナビゲーション
            if url.strip() and url.strip() != "https://www.genspark.ai/agents?type=moa_chat":
                self.status_queue.put(f"URLに移動中: {url}")
                self.tool.driver.get(url.strip())
                time.sleep(3)
            
            # retry_countを設定
            if hasattr(self.tool, 'max_regenerate_retries'):
                self.tool.max_regenerate_retries = max(1, int(retry_count))
            
            cycle_count = 0
            
            # 最初にプロンプトAを送信
            if self.is_running:
                cycle_count += 1
                self.current_prompt_type = "A"
                self.status_queue.put(f"🔄 サイクル{cycle_count}: プロンプトA送信")
                
                wait_time = random.randint(5, 30)
                self.status_queue.put(f"⏱️ プロンプトA送信前の待機中... ({wait_time}秒)")
                
                for i in range(wait_time):
                    if not self.is_running:
                        return
                    time.sleep(1)
                
                # ランダム選択機能を使用
                actual_prompt_a = self.get_random_prompt("a", prompt_a)
                self.status_queue.put(f"📤 プロンプトA送信中: {actual_prompt_a[:50]}...")
                response_a = self._send_prompt_with_retry(actual_prompt_a, use_fallback, fallback_message, retry_count)
                
                if response_a == "STOPPED":
                    return
                elif response_a and response_a != "ERROR":
                    # ファイル保存
                    try:
                        filepath = self.tool.save_to_markdown(response_a, actual_prompt_a)
                        self.response_queue.put(f"[プロンプトA] {response_a}")
                        self.status_queue.put(f"✅ プロンプトA完了、ファイル保存: {filepath}")
                    except Exception as save_error:
                        self.status_queue.put(f"⚠️ ファイル保存エラー: {save_error}")
                        self.response_queue.put(f"[プロンプトA] {response_a}")
                else:
                    self.status_queue.put(f"❌ プロンプトAでエラーが発生")
                    # エラーでも続行
            
            # B→C→B→Cのループ（回数制御対応）
            bc_cycles = 0
            max_cycles = max(0, int(bc_loop_count))
            
            while self.is_running and (max_cycles == 0 or bc_cycles < max_cycles):
                # プロンプトB送信
                if self.is_running:
                    self.current_prompt_type = "B"
                    self.current_bc_cycle = bc_cycles + 1
                    wait_time = random.randint(5, 30)
                    self.status_queue.put(f"⏱️ プロンプトB送信前の待機中... ({wait_time}秒)")
                    
                    for i in range(wait_time):
                        if not self.is_running:
                            return
                        time.sleep(1)
                    
                    actual_prompt_b = self.get_random_prompt("b", prompt_b)
                    loop_info = f" (サイクル{self.current_bc_cycle}/{max_cycles if max_cycles > 0 else '∞'})"
                    self.status_queue.put(f"📤 プロンプトB送信中{loop_info}: {actual_prompt_b[:50]}...")
                    response_b = self._send_prompt_with_retry(actual_prompt_b, use_fallback, fallback_message, retry_count)
                    
                    if response_b == "STOPPED":
                        return
                    elif response_b and response_b != "ERROR":
                        try:
                            filepath = self.tool.save_to_markdown(response_b, actual_prompt_b)
                            self.response_queue.put(f"[プロンプトB] {response_b}")
                            self.status_queue.put(f"✅ プロンプトB完了、ファイル保存: {filepath}")
                        except Exception as save_error:
                            self.status_queue.put(f"⚠️ ファイル保存エラー: {save_error}")
                            self.response_queue.put(f"[プロンプトB] {response_b}")
                    else:
                        self.status_queue.put(f"❌ プロンプトBでエラーが発生")
                
                # プロンプトC送信
                if self.is_running:
                    self.current_prompt_type = "C"
                    wait_time = random.randint(5, 30)
                    self.status_queue.put(f"⏱️ プロンプトC送信前の待機中... ({wait_time}秒)")
                    
                    for i in range(wait_time):
                        if not self.is_running:
                            return
                        time.sleep(1)
                    
                    actual_prompt_c = self.get_random_prompt("c", prompt_c)
                    loop_info = f" (サイクル{self.current_bc_cycle}/{max_cycles if max_cycles > 0 else '∞'})"
                    self.status_queue.put(f"📤 プロンプトC送信中{loop_info}: {actual_prompt_c[:50]}...")
                    response_c = self._send_prompt_with_retry(actual_prompt_c, use_fallback, fallback_message, retry_count)
                    
                    if response_c == "STOPPED":
                        return
                    elif response_c and response_c != "ERROR":
                        try:
                            filepath = self.tool.save_to_markdown(response_c, actual_prompt_c)
                            self.response_queue.put(f"[プロンプトC] {response_c}")
                            self.status_queue.put(f"✅ プロンプトC完了、ファイル保存: {filepath}")
                        except Exception as save_error:
                            self.status_queue.put(f"⚠️ ファイル保存エラー: {save_error}")
                            self.response_queue.put(f"[プロンプトC] {response_c}")
                    else:
                        self.status_queue.put(f"❌ プロンプトCでエラーが発生")
                
                bc_cycles += 1
                cycle_count += 1
                
                if max_cycles > 0 and bc_cycles >= max_cycles:
                    self.status_queue.put(f"🏁 指定されたB→Cサイクル({max_cycles}回)が完了しました")
                    break
                else:
                    remaining = f"残り{max_cycles - bc_cycles}回" if max_cycles > 0 else "無限継続"
                    self.status_queue.put(f"🔄 サイクル{cycle_count}完了、次のB→Cサイクルへ... ({remaining})")
                
        except Exception as e:
            error_msg = f"プロンプトフローエラー: {str(e)}"
            self.status_queue.put(f"❌ {error_msg}")
            self.response_queue.put(error_msg)
        finally:
            self.is_running = False
            self.current_prompt_type = None
            self.current_bc_cycle = 0
    
    def _send_prompt_with_retry(self, prompt, use_fallback, fallback_message, retry_count):
        """プロンプト送信とリトライ処理"""
        try:
            # プロンプト送信 - process_single_promptは戻り値が(success, response_text)のタプル
            success, response_text = self.tool.process_single_prompt(prompt, save_file=False)
            
            if not success or response_text == "REGENERATE_ERROR_DETECTED":
                if use_fallback and fallback_message.strip():
                    self.status_queue.put("🔄 フォールバックメッセージでリトライ中...")
                    
                    for retry in range(retry_count):
                        if not self.is_running:
                            return "STOPPED"
                            
                        # フォールバック前の待機
                        time.sleep(5)
                        
                        fallback_success, fallback_response = self.tool.process_single_prompt(fallback_message, save_file=False)
                        
                        if fallback_success and fallback_response != "REGENERATE_ERROR_DETECTED":
                            self.status_queue.put(f"✅ フォールバック成功 (試行{retry + 1}回目)")
                            return fallback_response
                        
                        self.status_queue.put(f"⚠️ フォールバック失敗 (試行{retry + 1}回目)")
                    
                    return "ERROR"
                else:
                    return "ERROR"
            else:
                return response_text
                
        except Exception as e:
            return f"ERROR: {str(e)}"

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
            success, response_text = self.tool.process_single_prompt(prompt_text, save_file=False)
            
            if (success and response_text and response_text != "REGENERATE_ERROR_DETECTED"):
                self.status_queue.put("✅ 応答受信完了")
                self.response_queue.put(response_text)
                
                # 成功した応答をMarkdownファイルに保存
                try:
                    filepath = self.tool.save_to_markdown(response_text, prompt_text)
                    self.status_queue.put(f"📁 応答をMarkdownファイルに保存しました: {filepath}")
                except Exception as save_error:
                    self.status_queue.put(f"⚠️ ファイル保存エラー: {save_error}")
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
    
    def stop_prompt_only(self):
        """プロンプトのみ停止（Chrome維持）"""
        if not self.is_running:
            return "待機中です", "待機中"
            
        self.is_running = False
        self.current_prompt_type = None
        self.current_bc_cycle = 0
                
        return "⏸️ プロンプト処理を停止しました（Chrome維持中）", "待機中"
    
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
            if not self.is_running:
                return "待機中"
            elif self.current_prompt_type:
                if self.max_bc_cycles > 0:
                    progress = f"{self.current_bc_cycle}/{self.max_bc_cycles}"
                else:
                    progress = f"{self.current_bc_cycle}/∞"
                return f"実行中 (プロンプト{self.current_prompt_type} - {progress})"
            else:
                return "実行中"
    
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
        
        # タブ切り替え
        with gr.Tabs():
            with gr.TabItem("🚀 メイン機能"):
                status_display, response_display, bc_loop_input = create_main_tab(gui)
            
            with gr.TabItem("📝 プロンプトリストの編集"):
                create_prompt_list_tab(gui, bc_loop_input)
        
        # リアルタイム更新設定
        interface.load(
            fn=lambda: (gui.get_status_update(), gui.get_response_update()),
            outputs=[status_display, response_display],
            every=1
        )
    
    return interface

def create_main_tab(gui):
    """メインタブのコンポーネントを作成"""
    with gr.Row():
        with gr.Column(scale=2):
            url_input = gr.Textbox(label="📍 URL", value=gui.settings.get("url", "https://www.genspark.ai/agents?type=moa_chat"), placeholder="移動先URL（空白でデフォルト）")
            prompt_input = gr.Textbox(label="💬 プロンプト", lines=4, placeholder="送信するプロンプトを入力してください...")
            
            with gr.Row():
                use_fallback = gr.Checkbox(label="フォールバックメッセージを使用", value=True)
                retry_count = gr.Number(label="最大リトライ回数", value=20, minimum=1, maximum=50)
            
            fallback_input = gr.Textbox(label="📝 フォールバックメッセージ", lines=2, placeholder="エラー時の代替メッセージ...", visible=True, value=gui.settings.get("fallback_message", ""))
            
            # Phase1: 複数プロンプト機能
            gr.Markdown("### 🔄 プロンプトフロー機能")
            
            # Phase2: ランダム選択機能
            with gr.Row():
                use_list_a = gr.Checkbox(label="🅰️ リストを使用", value=gui.settings.get("use_list_a", False))
                use_list_b = gr.Checkbox(label="🅱️ リストを使用", value=gui.settings.get("use_list_b", False))
                use_list_c = gr.Checkbox(label="🅾️ リストを使用", value=gui.settings.get("use_list_c", False))
            
            prompt_a_input = gr.Textbox(label="🅰️ プロンプトA (初期プロンプト)", lines=3, placeholder="最初に送信するプロンプト...", value=gui.settings.get("prompt_a", ""))
            prompt_b_input = gr.Textbox(label="🅱️ プロンプトB (追加情報要求)", lines=3, placeholder="追加情報の候補をリクエストするプロンプト...", value=gui.settings.get("prompt_b", ""))
            prompt_c_input = gr.Textbox(label="🅾️ プロンプトC (候補承認)", lines=3, placeholder="提案された候補にOKするプロンプト...", value=gui.settings.get("prompt_c", ""))
            
            # B->Cループ回数制御
            bc_loop_input = gr.Number(label="🔄 B→Cループ回数 (0=無限)", value=gui.settings.get("bc_loop_count", 0), minimum=0, maximum=1000)
            
            with gr.Row():
                prompt_flow_btn = gr.Button("🔄 プロンプトフロー開始", variant="primary")
                flow_stop_btn = gr.Button("⏹️ フロー停止", variant="stop")
            
            # 設定保存ボタン
            save_settings_btn = gr.Button("💾 設定を保存", variant="secondary")
            save_status = gr.Textbox(label="保存状況", value="", visible=False, interactive=False)
            
            use_fallback.change(fn=lambda x: gr.update(visible=x), inputs=[use_fallback], outputs=[fallback_input])
            
            with gr.Row():
                start_btn = gr.Button("🚀 プロンプト送信", variant="primary")
                prompt_stop_btn = gr.Button("⏸️ プロンプト停止", variant="secondary")
                stop_btn = gr.Button("🛑 完全停止", variant="stop")
        
        with gr.Column(scale=2):
            status_display = gr.Textbox(label="📊 ツールステータス", value="待機中", interactive=False)
            response_display = gr.Textbox(label="📄 応答内容", lines=15, placeholder="応答がここに表示されます...", interactive=False)
    
    # イベントハンドラー
    start_btn.click(
        fn=gui.start_automation,
        inputs=[url_input, prompt_input, use_fallback, fallback_input, retry_count],
        outputs=[status_display, response_display, status_display]
    )
    
    prompt_stop_btn.click(fn=gui.stop_prompt_only, outputs=[status_display, status_display])
    stop_btn.click(fn=gui.stop_automation, outputs=[status_display, status_display])
    
    # プロンプトフローボタンのイベント
    prompt_flow_btn.click(
        fn=gui.start_prompt_flow,
        inputs=[url_input, prompt_a_input, prompt_b_input, prompt_c_input, use_fallback, fallback_input, retry_count, bc_loop_input],
        outputs=[status_display, response_display, status_display]
    )
    
    flow_stop_btn.click(
        fn=lambda bc_count: gui.stop_automation(),
        inputs=[bc_loop_input],
        outputs=[status_display, status_display]
    )
    
    # 設定保存ボタンのイベント
    save_settings_btn.click(
        fn=lambda url, fallback, pa, pb, pc, ua, ub, uc, bc_count: gui.save_settings(
            url=url, 
            fallback_message=fallback,
            prompt_a=pa,
            prompt_b=pb,
            prompt_c=pc,
            use_list_a=ua,
            use_list_b=ub,
            use_list_c=uc,
            bc_loop_count=bc_count
        ),
        inputs=[url_input, fallback_input, prompt_a_input, prompt_b_input, prompt_c_input, use_list_a, use_list_b, use_list_c, bc_loop_input],
        outputs=[save_status]
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[save_status]
    )
    
    return status_display, response_display, bc_loop_input

def create_prompt_list_tab(gui, bc_loop_input=None):
    """プロンプトリスト編集タブのコンポーネントを作成"""
    
    # 統合リスト表示セクション（Stage 1-2: 表示+追加機能）
    with gr.Column():
        gr.Markdown("## 📋 統合プロンプトリスト (全体表示)")
        
        # Stage 5-6: プロンプトセット表示・選択UI
        with gr.Row():
            current_set_display = gr.Textbox(
                label="現在のプロンプトセット", 
                value=gui.settings.get("active_prompt_set", "デフォルト"),
                interactive=False,
                scale=1
            )
            # Stage 6: プロンプトセット選択Dropdown（イベントハンドラーなし）
            set_selector = gr.Dropdown(
                choices=gui.get_prompt_set_names(),
                value=gui.settings.get("active_prompt_set", "デフォルト"),
                label="セット選択",
                scale=1
            )
        
        # Stage 7a: プロンプトセット作成機能
        gr.Markdown("### ➕ 新しいプロンプトセット作成")
        with gr.Row():
            new_set_name = gr.Textbox(
                label="新しいセット名",
                placeholder="例: 日本の山、日本の湖...",
                scale=3
            )
            create_set_btn = gr.Button("🆕 セット作成", scale=1)
        
        create_set_result = gr.Textbox(
            label="作成結果",
            interactive=False,
            lines=2
        )
        
        # Stage 10: プロンプトセット削除機能
        gr.Markdown("### 🗑️ プロンプトセット削除")
        with gr.Row():
            delete_set_btn = gr.Button("🗑️ 選択中のセットを削除", variant="stop", scale=1)
        
        delete_set_result = gr.Textbox(
            label="削除結果", 
            interactive=False,
            lines=2
        )
        
        unified_list_display = gr.Textbox(
            label="A/B/C統合プロンプトリスト", 
            lines=12, 
            value=gui.get_unified_list_display(), 
            interactive=False,
            placeholder="A/B/Cすべてのプロンプトがここに表示されます..."
        )
        
        # Stage 2: 統合リストへの追加機能
        gr.Markdown("### ➕ 統合リストに追加")
        with gr.Row():
            unified_category = gr.Dropdown(
                choices=[("プロンプトA", "a"), ("プロンプトB", "b"), ("プロンプトC", "c")],
                value="a",
                label="カテゴリ選択",
                scale=1
            )
            unified_new_prompt = gr.Textbox(
                label="新しいプロンプト", 
                placeholder="統合リストに追加するプロンプト...", 
                scale=3
            )
            unified_add_btn = gr.Button("🚀 統合追加", variant="primary", scale=1)
        
        unified_result = gr.Textbox(label="統合操作結果", interactive=False)
    
    gr.Markdown("---")  # セクション区切り
    
    # プロンプトAリスト管理（独立）
    with gr.Column():
        gr.Markdown("### 🅰️ プロンプトAリスト管理")
        list_a_display = gr.Textbox(label="プロンプトAリスト", lines=8, value=gui.get_list_display("a"), interactive=False)
        
        with gr.Row():
            new_prompt_a = gr.Textbox(label="新しいプロンプトA", placeholder="追加するプロンプト...", scale=3)
            add_a_btn = gr.Button("➕ 追加", scale=1)
        
        with gr.Row():
            edit_index_a = gr.Number(label="編集インデックス", value=0, minimum=0, scale=1)
            edit_content_a = gr.Textbox(label="新しい内容", placeholder="編集後の内容...", scale=2)
            edit_a_btn = gr.Button("✏️ 編集", scale=1)
        
        with gr.Row():
            remove_index_a = gr.Number(label="削除インデックス", value=0, minimum=0, scale=2)
            remove_a_btn = gr.Button("🗑️ 削除", scale=1)
        
        result_a = gr.Textbox(label="操作結果", interactive=False)
    
    # プロンプトBリスト管理（独立）
    with gr.Column():
        gr.Markdown("### 🅱️ プロンプトBリスト管理")
        list_b_display = gr.Textbox(label="プロンプトBリスト", lines=8, value=gui.get_list_display("b"), interactive=False)
        
        with gr.Row():
            new_prompt_b = gr.Textbox(label="新しいプロンプトB", placeholder="追加するプロンプト...", scale=3)
            add_b_btn = gr.Button("➕ 追加", scale=1)
        
        with gr.Row():
            edit_index_b = gr.Number(label="編集インデックス", value=0, minimum=0, scale=1)
            edit_content_b = gr.Textbox(label="新しい内容", placeholder="編集後の内容...", scale=2)
            edit_b_btn = gr.Button("✏️ 編集", scale=1)
        
        with gr.Row():
            remove_index_b = gr.Number(label="削除インデックス", value=0, minimum=0, scale=2)
            remove_b_btn = gr.Button("🗑️ 削除", scale=1)
        
        result_b = gr.Textbox(label="操作結果", interactive=False)
    
    # プロンプトCリスト管理（独立）
    with gr.Column():
        gr.Markdown("### 🅾️ プロンプトCリスト管理")
        list_c_display = gr.Textbox(label="プロンプトCリスト", lines=8, value=gui.get_list_display("c"), interactive=False)
        
        with gr.Row():
            new_prompt_c = gr.Textbox(label="新しいプロンプトC", placeholder="追加するプロンプト...", scale=3)
            add_c_btn = gr.Button("➕ 追加", scale=1)
        
        with gr.Row():
            edit_index_c = gr.Number(label="編集インデックス", value=0, minimum=0, scale=1)
            edit_content_c = gr.Textbox(label="新しい内容", placeholder="編集後の内容...", scale=2)
            edit_c_btn = gr.Button("✏️ 編集", scale=1)
        
        with gr.Row():
            remove_index_c = gr.Number(label="削除インデックス", value=0, minimum=0, scale=2)
            remove_c_btn = gr.Button("🗑️ 削除", scale=1)
        
        result_c = gr.Textbox(label="操作結果", interactive=False)
    
    # プロンプトAのイベントハンドラー（統合リスト更新対応）
    add_a_btn.click(
        fn=lambda prompt: gui.add_to_list("a", prompt) + (gui.get_unified_list_display(),),
        inputs=[new_prompt_a],
        outputs=[result_a, list_a_display, unified_list_display]
    ).then(fn=lambda: "", outputs=[new_prompt_a])
    
    edit_a_btn.click(
        fn=lambda idx, content: gui.edit_list_item("a", idx, content) + (gui.get_unified_list_display(),),
        inputs=[edit_index_a, edit_content_a],
        outputs=[result_a, list_a_display, unified_list_display]
    ).then(fn=lambda: "", outputs=[edit_content_a])
    
    remove_a_btn.click(
        fn=lambda idx: gui.remove_from_list("a", idx) + (gui.get_unified_list_display(),),
        inputs=[remove_index_a],
        outputs=[result_a, list_a_display, unified_list_display]
    )
    
    # プロンプトBのイベントハンドラー（統合リスト更新対応）
    add_b_btn.click(
        fn=lambda prompt: gui.add_to_list("b", prompt) + (gui.get_unified_list_display(),),
        inputs=[new_prompt_b],
        outputs=[result_b, list_b_display, unified_list_display]
    ).then(fn=lambda: "", outputs=[new_prompt_b])
    
    edit_b_btn.click(
        fn=lambda idx, content: gui.edit_list_item("b", idx, content) + (gui.get_unified_list_display(),),
        inputs=[edit_index_b, edit_content_b],
        outputs=[result_b, list_b_display, unified_list_display]
    ).then(fn=lambda: "", outputs=[edit_content_b])
    
    remove_b_btn.click(
        fn=lambda idx: gui.remove_from_list("b", idx) + (gui.get_unified_list_display(),),
        inputs=[remove_index_b],
        outputs=[result_b, list_b_display, unified_list_display]
    )
    
    # プロンプトCのイベントハンドラー（統合リスト更新対応）
    add_c_btn.click(
        fn=lambda prompt: gui.add_to_list("c", prompt) + (gui.get_unified_list_display(),),
        inputs=[new_prompt_c],
        outputs=[result_c, list_c_display, unified_list_display]
    ).then(fn=lambda: "", outputs=[new_prompt_c])
    
    edit_c_btn.click(
        fn=lambda idx, content: gui.edit_list_item("c", idx, content) + (gui.get_unified_list_display(),),
        inputs=[edit_index_c, edit_content_c],
        outputs=[result_c, list_c_display, unified_list_display]
    ).then(fn=lambda: "", outputs=[edit_content_c])
    
    remove_c_btn.click(
        fn=lambda idx: gui.remove_from_list("c", idx) + (gui.get_unified_list_display(),),
        inputs=[remove_index_c],
        outputs=[result_c, list_c_display, unified_list_display]
    )
    
    # Stage 2: 統合追加ボタンのイベントハンドラー
    def unified_add_with_list_updates(category, prompt):
        """統合追加 + 個別リスト表示更新"""
        result_msg, unified_display = gui.add_to_unified_list(category, prompt)
        
        # 個別リスト表示も更新
        list_a_new = gui.get_list_display("a")
        list_b_new = gui.get_list_display("b") 
        list_c_new = gui.get_list_display("c")
        
        return result_msg, unified_display, list_a_new, list_b_new, list_c_new
    
    unified_add_btn.click(
        fn=unified_add_with_list_updates,
        inputs=[unified_category, unified_new_prompt],
        outputs=[unified_result, unified_list_display, list_a_display, list_b_display, list_c_display]
    ).then(fn=lambda: "", outputs=[unified_new_prompt])
    
    # Stage 7b: プロンプトセット作成イベントハンドラー
    if bc_loop_input is not None:
        def create_set_with_refresh(set_name, bc_count):
            """プロンプトセット作成 + UI更新"""
            result = gui.create_prompt_set(set_name)
            
            # 作成後にドロップダウンの選択肢を更新
            new_choices = gui.get_prompt_set_names()
            new_current_display = gui.settings.get("active_prompt_set", "デフォルト")
            
            return result, gr.update(choices=new_choices), new_current_display
        
        create_set_btn.click(
            fn=create_set_with_refresh,
            inputs=[new_set_name, bc_loop_input],  # bc_loop_inputを一貫性のため含める
            outputs=[create_set_result, set_selector, current_set_display]
        ).then(fn=lambda: "", outputs=[new_set_name])
        
        # Stage 9a + 11a: プロンプトセット切り替えイベントハンドラー（セット名自動入力機能追加）
        def switch_set_with_refresh(selected_set, bc_count):
            """プロンプトセット切り替え + 全UI更新 + セット名自動入力"""
            result = gui.switch_prompt_set(selected_set)
            
            # 切り替え後のUI更新
            new_unified_display = gui.get_unified_list_display()
            new_list_a = gui.get_list_display("a") 
            new_list_b = gui.get_list_display("b")
            new_list_c = gui.get_list_display("c")
            
            # Stage 11a: 選択したセット名を「新しいセット名」に自動入力
            return result, selected_set, new_unified_display, new_list_a, new_list_b, new_list_c, selected_set
        
        set_selector.change(
            fn=switch_set_with_refresh,
            inputs=[set_selector, bc_loop_input],  # bc_loop_inputを一貫性のため含める
            outputs=[create_set_result, current_set_display, unified_list_display, list_a_display, list_b_display, list_c_display, new_set_name]
        )
        
        # Stage 9b: Dropdown選択肢の定期更新
        def update_dropdown_choices():
            """Dropdown選択肢とアクティブセット表示を更新"""
            current_choices = gui.get_prompt_set_names()
            current_active = gui.settings.get("active_prompt_set", "デフォルト")
            return gr.update(choices=current_choices), current_active
        
        # 定期更新タイマー（5秒間隔）
        dropdown_timer = gr.Timer(value=5)
        dropdown_timer.tick(
            fn=update_dropdown_choices,
            outputs=[set_selector, current_set_display]
        )
        
        # Stage 10: プロンプトセット削除イベントハンドラー
        def delete_set_with_refresh(bc_count):
            """選択中のプロンプトセット削除 + UI更新"""
            current_active = gui.settings.get("active_prompt_set", "デフォルト")
            result = gui.delete_prompt_set(current_active)
            
            # 削除後のUI更新
            new_choices = gui.get_prompt_set_names()
            new_active = gui.settings.get("active_prompt_set", "デフォルト")
            new_unified_display = gui.get_unified_list_display()
            new_list_a = gui.get_list_display("a")
            new_list_b = gui.get_list_display("b") 
            new_list_c = gui.get_list_display("c")
            
            return (result, gr.update(choices=new_choices), new_active, 
                   new_unified_display, new_list_a, new_list_b, new_list_c)
        
        delete_set_btn.click(
            fn=delete_set_with_refresh,
            inputs=[bc_loop_input],  # bc_loop_inputを一貫性のため含める
            outputs=[delete_set_result, set_selector, current_set_display, 
                    unified_list_display, list_a_display, list_b_display, list_c_display]
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("🚀 Chrome��動操作ツール Web GUI を起動中...")
    interface = create_interface()
    interface.launch(server_name="127.0.0.1", server_port=7860, share=False, show_error=True)