import base64
from dotenv import load_dotenv


with open('VC_CRM/service_account.json', 'r') as f:
    service_account_data = f.read()
        
    # 轉換為 base64
    base64_data = base64.b64encode(service_account_data.encode('utf-8')).decode('utf-8')
    print(base64_data)
        
 