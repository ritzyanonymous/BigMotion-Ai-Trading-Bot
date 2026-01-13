import requests

def send_telegram_message(token, chat_id, message, pdf_file=None):
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                  json={"chat_id":chat_id,"text":message})
    if pdf_file:
        files = {"document": open(pdf_file, "rb")}
        data = {"chat_id": chat_id}
        requests.post(f"https://api.telegram.org/bot{token}/sendDocument",
                      files=files, data=data)
