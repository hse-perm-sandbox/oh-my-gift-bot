import requests
from src.config import settings


class AIService:
    """Генерирует идеи подарков на основе имени и информации о человеке, используя API"""
    @staticmethod
    def generate_gift_ideas(name: str, info: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.API_KEY}"
        }

        prompt = f"Не задавай вопросов, выведи только идеи подарков. Придумай 5 оригинальных идей подарков на день рождения для {name}." \
                 f"Учти следующую информацию: {info}. " \
                 f"Сделай текст не слишком длинным, перечисли идеи списком."

        data = {
            "model": "deepseek-ai/DeepSeek-R1",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты помогаешь с выбором подарков."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            response = requests.post(settings.API_URL, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].split('</think>')[-1].strip()
            return f"Идеи подарков для {name}: книга, подарочный сертификат, цветы"
        except Exception:
            return f"Идеи подарков для {name}: парфюм, билеты на мероприятие, гаджет"

    @staticmethod
    def generate_congratulation(name: str, info: str) -> str:
        """Генерирует поздравление с днем рождения"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.API_KEY}"
        }

        prompt = f"Не задавай вопросов, выведи только поздравление. Придумай оригинальное и теплое поздравление с днем рождения для {name}. Информация о человеке: {info}. " \
                 f"Сделай текст не слишком длинным (4-5 предложений)."

        data = {
            "model": "deepseek-ai/DeepSeek-R1",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты пишешь поздравления."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            response = requests.post(settings.API_URL, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].split('</think>')[-1].strip()
            return f"Дорогой(ая) {name}! От всей души поздравляю с Днём рождения! 🎉"
        except Exception:
            return f"Дорогой(ая) {name}! Сердечно поздравляю с Днём рождения! 🌟"