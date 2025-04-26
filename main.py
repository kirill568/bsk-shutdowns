import requests
import os
import re
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
import pytz
import traceback
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN =  os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID =  os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_telegram_message(text, disable_notification=True, file_path=None):
    try:
        if file_path:
            with open(file_path, "rb") as file:
                files = {"document": file}
                data = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": text,
                    "parse_mode": "HTML",
                    "disable_notification": disable_notification
                }
                response = requests.post(f"{TELEGRAM_API_URL}/sendDocument", data=data, files=files)
        else:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_notification": disable_notification
            }
            response = requests.post(f"{TELEGRAM_API_URL}/sendMessage", data=payload)
        
        response.raise_for_status()
    except Exception:
        print(f"Ошибка при отправке сообщения: {traceback.format_exc()}")

def download_pdf(url, save_path):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        f.write(response.content)
    return save_path

def search_in_pdf(file_path, search_text):
    reader = PdfReader(file_path)
    for page in reader.pages:
        text = page.extract_text()
        if text and search_text.lower() in text.lower():
            return True
    return False

def main():
    pdf_path = None
    try:
        today = datetime.now(pytz.timezone('Asia/Barnaul'))
        # today = datetime(2025, 4, 23)
        tomorrow = today + timedelta(days=1)
        tomorrow_datetime = tomorrow.strftime("%d_%m_%Y")  # Для поиска в ссылке

        # Make request
        url = "https://www.bsk22.ru/ajax/contracts.php"
        payload = {
            "date": today.strftime("%Y-%m-01"),
            "iblock": 44
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post(url, data=payload, headers=headers, timeout=10)
        response.raise_for_status()

        html = response.text

        # Find link
        match = re.search(r'href="(\/upload\/iblock\/.*?{}.*?\.pdf)"'.format(re.escape(tomorrow_datetime)), html)
        if not match:
            send_telegram_message(f'На завтра ({tomorrow_datetime}) ничего не нашлось (ссылка на PDF не найдена).')
            return

        pdf_relative_url = match.group(1)
        pdf_url = f"https://www.bsk22.ru{pdf_relative_url}"

        # Download PDF
        save_dir = "downloads"
        os.makedirs(save_dir, exist_ok=True)
        pdf_filename = os.path.basename(pdf_relative_url)
        pdf_path = os.path.join(save_dir, pdf_filename)
        download_pdf(pdf_url, pdf_path)

        # Find "Заречная" in PDF
        found = search_in_pdf(pdf_path, "Заречная")

        if found:
            send_telegram_message(f"⚠️ Отключение электроэнергии на Заречной, найдено в документе: <b>{pdf_filename}</b>", disable_notification=False, file_path=pdf_path)
        else:
            send_telegram_message(f"ℹ️ В документе <b>{pdf_filename}</b> строка 'Заречная' не найдена")

    except Exception as e:
        stacktrace = traceback.format_exc()
        send_telegram_message(f"❌ Произошла ошибка:\n<pre>{stacktrace}</pre>", disable_notification=False)

    finally:
        # Удаление файла
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception as e:
                send_telegram_message(f"❌ Ошибка при удалении файла:\n<pre>{traceback.format_exc()}</pre>", disable_notification=False)    

if __name__ == "__main__":
    main()