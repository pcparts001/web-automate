#!/usr/bin/env python3
"""
候補別管理機能のテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gradio_gui import AutomationGUI

def test_candidate_management():
    # AutomationGUIインスタンスを作成
    gui = AutomationGUI()
    
    print("=== 候補別管理機能テスト ===")
    
    # テスト1: 新しい変数に候補を追加
    print("\n--- テスト1: 新しい変数 'name' に候補を追加 ---")
    result1, success1 = gui.add_candidate_to_variable("name", "John\nSmith")
    print(f"結果1: {result1}, 成功: {success1}")
    
    result2, success2 = gui.add_candidate_to_variable("name", "Steve Adam")
    print(f"結果2: {result2}, 成功: {success2}")
    
    result3, success3 = gui.add_candidate_to_variable("name", "Alice Johnson")
    print(f"結果3: {result3}, 成功: {success3}")
    
    # テスト2: 候補一覧表示
    print("\n--- テスト2: 候補一覧表示 ---")
    candidates = gui.get_variable_candidates_display("name")
    print(f"name変数の候補:\n{candidates}")
    
    # テスト3: 候補削除
    print("\n--- テスト3: 候補削除（インデックス1を削除）---")
    result4, success4 = gui.remove_candidate_from_variable("name", "1")
    print(f"結果4: {result4}, 成功: {success4}")
    
    candidates_after = gui.get_variable_candidates_display("name")
    print(f"削除後のname変数の候補:\n{candidates_after}")
    
    # テスト4: 全体表示確認
    print("\n--- テスト4: 全体の変数表示確認 ---")
    all_variables = gui.get_template_variables_display()
    print(f"全変数:\n{all_variables}")

if __name__ == "__main__":
    test_candidate_management()