import requests
import yaml
from server.templar import chat_with_knight

# Load configuration
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)
    ACCESS_TOKEN = config.get("instagram_access_token")  # Note: There's a typo in your config key
    INSTAGRAM_ACCOUNT_ID = config.get("instagram_account_id")

class InstagramBot:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}"
        self.headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }

    def get_messages(self):
        """Fetch recent messages from Instagram"""
        endpoint = f"{self.base_url}/messages"
        params = {
            "fields": "message,from"
        }
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            print(f"Error fetching messages: {e}")
            return []

    def send_message(self, user_id, message):
        """Send a message to a specific user"""
        endpoint = f"{self.base_url}/messages"
        data = {
            "recipient": {"id": user_id},
            "message": {"text": message}
        }
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def process_messages(self):
        """Process new messages and respond using the Templar chatbot"""
        messages = self.get_messages()
        
        for message in messages:
            user_id = message.get("from", {}).get("id")
            user_message = message.get("message")
            
            if user_id and user_message:
                # Get response from Templar chatbot
                response = chat_with_knight(user_message)
                
                # Send response back to user
                self.send_message(user_id, response)

def main():
    bot = InstagramBot()
    print("⚔ 템플러 기사단장 인스타그램 봇 시작 ⚔")
    
    try:
        while True:
            bot.process_messages()
            # Add a delay to avoid hitting rate limits
            import time
            time.sleep(5)  # Check messages every 5 seconds
    except KeyboardInterrupt:
        print("\n⚔ 성스러운 봇이 종료됩니다. ⚔")

if __name__ == "__main__":
    main() 