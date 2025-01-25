from flask import Flask, request, jsonify
import os
from server.templar import chat_with_knight
import requests

app = Flask(__name__)

# Load environment variables
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

class InstagramHandler:
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

    def reply_to_comment(self, comment_id, message):
        """Reply to a comment on Instagram"""
        endpoint = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
        data = {
            "message": message,
            "access_token": ACCESS_TOKEN
        }
        
        try:
            response = requests.post(endpoint, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error replying to comment: {e}")
            return False

    def get_media_comments(self, media_id):
        """Get comments on a specific media"""
        endpoint = f"https://graph.facebook.com/v19.0/{media_id}/comments"
        params = {
            "fields": "id,text,username,timestamp",
            "access_token": ACCESS_TOKEN
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            print(f"Error fetching comments: {e}")
            return []

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

    def process_comments(self, media_id):
        """Process comments on a media post"""
        comments = self.get_media_comments(media_id)
        
        for comment in comments:
            comment_id = comment.get("id")
            comment_text = comment.get("text")
            
            if comment_id and comment_text:
                # Get response from Templar chatbot
                response = chat_with_knight(comment_text)
                
                # Reply to the comment
                self.reply_to_comment(comment_id, response)

    def post_instagram_photo(self, image_url, caption):
        """Post a photo to Instagram"""
        endpoint = f"{self.base_url}/media"
        data = {
            "image_url": image_url,
            "caption": caption,
            "access_token": ACCESS_TOKEN
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error posting photo: {e}")
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
                    # Handle messages
                    if 'messaging' in entry:
                        for messaging in entry['messaging']:
                            sender_id = messaging.get('sender', {}).get('id')
                            message = messaging.get('message', {}).get('text')
                            
                            if sender_id and message:
                                # Get response from Templar chatbot
                                response = chat_with_knight(message)
                                
                                # Send response back to user
                                instagram.send_message(sender_id, response)
                    
                    # Handle comments
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if change.get('field') == 'comments':
                                comment_data = change.get('value', {})
                                media_id = comment_data.get('media_id')
                                comment_id = comment_data.get('id')
                                comment_text = comment_data.get('text')
                                
                                if comment_id and comment_text:
                                    # Get response from Templar chatbot
                                    response = chat_with_knight(comment_text)
                                    
                                    # Reply to the comment
                                    instagram.reply_to_comment(comment_id, response)
            
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