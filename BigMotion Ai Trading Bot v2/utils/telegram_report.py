"""Telegram integration"""
import requests


def send_telegram_message(bot_token, chat_id, message, file_path=None):
    """Send message or file to Telegram"""
    try:
        if file_path:
            url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            with open(file_path, 'rb') as f:
                files = {'document': f}
                data = {'chat_id': chat_id, 'caption': message}
                response = requests.post(url, data=data, files=files)
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {'chat_id': chat_id, 'text': message}
            response = requests.post(url, data=data)
        
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False