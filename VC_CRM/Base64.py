import base64
from dotenv import load_dotenv
import os
import json

def convert_to_base64(input_text: str) -> str:
    """將輸入文字轉換為 base64 格式"""
    # 確保輸入是有效的 JSON
    try:
        json.loads(input_text)
    except json.JSONDecodeError:
        print("❌ 輸入的文字不是有效的 JSON 格式")
        return None
    
    # 轉換為 base64
    base64_data = base64.b64encode(input_text.encode('utf-8')).decode('utf-8')
    return base64_data

def main():
    print("請選擇操作模式：")
    print("1. 從檔案轉換 (service_account.json)")
    print("2. 手動輸入文字")
    choice = input("請輸入選項 (1/2): ")

    if choice == "1":
        try:
            with open('VC_CRM/service_account.json', 'r') as f:
                service_account_data = f.read()
            base64_data = convert_to_base64(service_account_data)
            if base64_data:
                print("\n轉換結果：")
                print(base64_data)
        
        except FileNotFoundError:
            print("❌ 找不到 service_account.json 檔案")
        except Exception as e:
            print(f"❌ 發生錯誤: {str(e)}")
    
    elif choice == "2":
        print("\n請輸入要轉換的文字（輸入完成後輸入 'END' 並按 Enter 來結束輸入）：")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        
        input_text = "\n".join(lines)
        base64_data = convert_to_base64(input_text)
        if base64_data:
            print("\n轉換結果：")
            print(base64_data)
    
    else:
        print("❌ 無效的選項")

if __name__ == "__main__":
    main()
        
 