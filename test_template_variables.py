#!/usr/bin/env python3
"""
テンプレート変数のランダム選択機能テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import ChromeAutomationTool

def test_template_variables():
    # ChromeAutomationToolインスタンスを作成（Chromeは起動しない）
    tool = ChromeAutomationTool(debug=True)
    
    # テストプロンプト
    test_prompt = "こんにちは、私の名前は{name}です。今日の話題は{topic}について話しましょう。今の気分は{mood}です。よろしく{greeting}！"
    
    print("=== テンプレート変数ランダム選択機能テスト ===")
    print(f"元のプロンプト: {test_prompt}")
    print()
    
    # 5回テストして異なる結果が出ることを確認
    for i in range(5):
        result = tool.replace_template_variables(test_prompt)
        print(f"テスト{i+1}: {result}")
    
    print()
    print("=== 単一値変数テスト ===")
    single_test = "挨拶: {greeting}, 天気: {weather}"
    result = tool.replace_template_variables(single_test)
    print(f"単一値テスト: {result}")

if __name__ == "__main__":
    test_template_variables()