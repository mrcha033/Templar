from flask import Flask, request, jsonify
import os
import yaml
from server.templar import chat_with_knight
import requests

app = Flask(__name__)

# Load configuration
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)
    ACCESS_TOKEN = config.get("instagram_access_token")
    INSTAGRAM_ACCOUNT_ID = config.get("instagram_account_id")
    VERIFY_TOKEN = config.get("VERIFY_TOKEN")

class InstagramHandler:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}"
        self.headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }

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

instagram = InstagramHandler()

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verification challenge
        if request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge')
        return 'Verification token mismatch', 403

    if request.method == 'POST':
        try:
            # Handle incoming Webhook events
            data = request.json
            
            # Extract messaging events
            if 'entry' in data:
                for entry in data['entry']:
                    if 'messaging' in entry:
                        for messaging in entry['messaging']:
                            sender_id = messaging.get('sender', {}).get('id')
                            message = messaging.get('message', {}).get('text')
                            
                            if sender_id and message:
                                # Get response from Templar chatbot
                                response = chat_with_knight(message)
                                
                                # Send response back to user
                                instagram.send_message(sender_id, response)
            
            return jsonify(success=True), 200
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return jsonify(success=False, error=str(e)), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify(status="healthy"), 200

if __name__ == '__main__':
    app.run(port=3000)