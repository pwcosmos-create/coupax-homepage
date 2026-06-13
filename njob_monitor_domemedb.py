import requests
import time
import datetime
import os

# 설정
TARGET_URL = 'https://domemedb.domeggook.com/index/'
LOG_FILE = 'domemedb_status.log'

def check_status():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=10)
        status = response.status_code
        
        # 200 OK이면서 내용에 'error'나 'Internal Server Error'가 없는지 확인
        if status == 200:
            if "Internal Server Error" in response.text or "서버 점검" in response.text:
                result = "[!] Server is UP, but displaying error message."
            else:
                result = "[✔] Server is UP and responding correctly!"
        else:
            result = f"[✘] Server is DOWN (Status: {status})"
            
    except Exception as e:
        result = f"[✘] Error connecting to server: {e}"
    
    log_msg = f"[{now}] {result}"
    print(log_msg)
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + "\n")
    
    return "[✔]" in result

if __name__ == "__main__":
    check_status()
