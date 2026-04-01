"""Telegram integration"""
import requests
import logging

logger = logging.getLogger(__name__)


def send_telegram_message(bot_token, chat_id, message, file_path=None):
    """Send message or file to Telegram"""
    try:
        if file_path:
            url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            with open(file_path, 'rb') as f:
                files = {'document': f}
                data = {'chat_id': chat_id, 'caption': message}
                response = requests.post(url, data=data, files=files, timeout=30)
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {'chat_id': chat_id, 'text': message}
            response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            logger.warning(f"Telegram API error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Telegram request timed out")
        return False
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False
