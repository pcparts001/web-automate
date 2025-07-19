#!/usr/bin/env python3
"""
再生成ボタン検出デバッグスクリプト
"""

from main import ChromeAutomationTool
import time

def test_regenerate_button_detection():
    tool = ChromeAutomationTool(debug=True)
    
    try:
        # Chromeを起動
        print("Chromeを起動しています...")
        if not tool.launch_chrome():
            print("Chrome起動に失敗しました")
            return
            
        print("ページが読み込まれるまで少し待機...")
        time.sleep(5)
        
        print("\n=== 再生成ボタン検出テスト ===")
        print("エラーが発生している状態で、このスクリプトを実行してください")
        print("何かキーを押すと検出テストを開始します...")
        input()
        
        # 再生成ボタンを検出
        button = tool.find_regenerate_button()
        
        if button:
            print(f"✅ 再生成ボタンを検出しました!")
            print(f"ボタンテキスト: '{button.text}'")
            print(f"ボタンタグ: {button.tag_name}")
            print(f"ボタンクラス: {button.get_attribute('class')}")
            print(f"表示状態: {button.is_displayed()}")
            
            # クリックテスト
            print("\nクリックテストを実行しますか？ (y/n): ", end="")
            if input().lower() == 'y':
                try:
                    button.click()
                    print("✅ 通常クリック成功")
                except Exception as e:
                    print(f"❌ 通常クリック失敗: {e}")
                    
                    try:
                        tool.driver.execute_script("arguments[0].click();", button)
                        print("✅ JavaScriptクリック成功")
                    except Exception as e2:
                        print(f"❌ JavaScriptクリック失敗: {e2}")
        else:
            print("❌ 再生成ボタンが見つかりませんでした")
            
        print("\nテスト完了。Enterキーでブラウザを閉じます...")
        input()
        
    finally:
        if tool.driver:
            tool.driver.quit()

if __name__ == "__main__":
    test_regenerate_button_detection()