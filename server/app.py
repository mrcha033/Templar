from flask import Flask, request, jsonify, send_from_directory
import os
from templar import chat_with_knight
import requests
import logging
import traceback
import sys
from datetime import datetime

app = Flask(__name__)

# Configure logging for Vercel environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Verify environment variables
if not all([ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID, VERIFY_TOKEN]):
    logger.error("Missing required environment variables")
    required_vars = {
        "ACCESS_TOKEN": bool(ACCESS_TOKEN),
        "INSTAGRAM_ACCOUNT_ID": bool(INSTAGRAM_ACCOUNT_ID),
        "VERIFY_TOKEN": bool(VERIFY_TOKEN)
    }
    logger.error(f"Environment variables status: {required_vars}")

class InstagramError(Exception):
    """Custom exception for Instagram API errors"""
    pass

class InstagramHandler:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}"
        self.headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        self.logger = logging.getLogger(__name__)
    
    def log_api_error(self, error, endpoint, method="GET", data=None):
        """Log API errors with detailed information"""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "endpoint": endpoint,
            "method": method,
            "data": data,
            "traceback": traceback.format_exc()
        }
        self.logger.error(f"API Error: {error_info}")
        return error_info

    def get_messages(self):
        """Fetch recent messages from Instagram"""
        endpoint = f"{self.base_url}/messages"
        params = {
            "fields": "message,from"
        }

        try:
            self.logger.info(f"Fetching messages from endpoint: {endpoint}")
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            messages = response.json().get("data", [])
            self.logger.info(f"Successfully fetched {len(messages)} messages")
            return messages
        except requests.exceptions.RequestException as e:
            error_info = self.log_api_error(e, endpoint)
            return []

    def send_message(self, user_id, message):
        """Send a message to a specific user"""
        endpoint = f"{self.base_url}/messages"
        data = {
            "recipient": {"id": user_id},
            "message": {"text": message}
        }
        
        try:
            self.logger.info(f"Sending message to user {user_id}")
            response = requests.post(endpoint, headers=self.headers, json=data)
            response.raise_for_status()
            self.logger.info(f"Successfully sent message to user {user_id}")
            return True
        except requests.exceptions.RequestException as e:
            error_info = self.log_api_error(e, endpoint, "POST", data)
            return False

    def reply_to_comment(self, comment_id, message):
        """Reply to a comment on Instagram"""
        endpoint = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
        data = {
            "message": message,
            "access_token": ACCESS_TOKEN
        }
        
        try:
            self.logger.info(f"Replying to comment {comment_id}")
            response = requests.post(endpoint, json=data)
            response.raise_for_status()
            self.logger.info(f"Successfully replied to comment {comment_id}")
            return True
        except requests.exceptions.RequestException as e:
            error_info = self.log_api_error(e, endpoint, "POST", data)
            return False

    def get_media_comments(self, media_id):
        """Get comments on a specific media"""
        endpoint = f"https://graph.facebook.com/v19.0/{media_id}/comments"
        params = {
            "fields": "id,text,username,timestamp",
            "access_token": ACCESS_TOKEN
        }
        
        try:
            self.logger.info(f"Fetching comments for media {media_id}")
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            comments = response.json().get("data", [])
            self.logger.info(f"Successfully fetched {len(comments)} comments for media {media_id}")
            return comments
        except requests.exceptions.RequestException as e:
            error_info = self.log_api_error(e, endpoint)
            return []

    def process_messages(self):
        """Process new messages and respond using the Templar chatbot"""
        try:
            messages = self.get_messages()
            self.logger.info(f"Processing {len(messages)} messages")
            
            for message in messages:
                user_id = message.get("from", {}).get("id")
                user_message = message.get("message")

                if user_id and user_message:
                    self.logger.info(f"Processing message from user {user_id}: {user_message[:50]}...")
                    # Get response from Templar chatbot
                    response = chat_with_knight(user_message)
                    
                    # Send response back to user
                    self.send_message(user_id, response)
        except Exception as e:
            self.logger.error(f"Error processing messages: {str(e)}\n{traceback.format_exc()}")

    def process_comments(self, media_id):
        """Process comments on a media post"""
        try:
            comments = self.get_media_comments(media_id)
            self.logger.info(f"Processing {len(comments)} comments for media {media_id}")
            
            for comment in comments:
                comment_id = comment.get("id")
                comment_text = comment.get("text")
                
                if comment_id and comment_text:
                    self.logger.info(f"Processing comment {comment_id}: {comment_text[:50]}...")
                    # Get response from Templar chatbot
                    response = chat_with_knight(comment_text)
                    
                    # Reply to the comment
                    self.reply_to_comment(comment_id, response)
        except Exception as e:
            self.logger.error(f"Error processing comments: {str(e)}\n{traceback.format_exc()}")

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

@app.route('/')
def index():
    """Root endpoint that shows the bot is running"""
    return jsonify({
        "status": "active",
        "message": "템플러 기사단장 봇이 깨어있습니다.",
        "version": "1.0.0"
    })

@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    """Handle favicon requests"""
    return '', 204  # No content response

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verification challenge
        verify_token = request.args.get('hub.verify_token')
        logger.info(f"Received webhook verification request with token: {verify_token}")
        
        if verify_token == VERIFY_TOKEN:
            challenge = request.args.get('hub.challenge')
            logger.info("Webhook verification successful")
            return challenge
        
        logger.warning("Webhook verification failed: token mismatch")
        return 'Verification token mismatch', 403

    if request.method == 'POST':
        try:
            logger.info("Received webhook event")
            # Handle incoming Webhook events
            data = request.json
            logger.debug(f"Webhook payload: {data}")
            
            # Extract messaging events
            if 'entry' in data:
                for entry in data['entry']:
                    # Handle messages
                    if 'messaging' in entry:
                        logger.info("Processing messaging events")
                        for messaging in entry['messaging']:
                            sender_id = messaging.get('sender', {}).get('id')
                            message = messaging.get('message', {}).get('text')
                            
                            if sender_id and message:
                                logger.info(f"Processing message from {sender_id}: {message[:50]}...")
                                # Get response from Templar chatbot
                                response = chat_with_knight(message)
                                
                                # Send response back to user
                                instagram.send_message(sender_id, response)
                    
                    # Handle comments
                    if 'changes' in entry:
                        logger.info("Processing comment events")
                        for change in entry['changes']:
                            if change.get('field') == 'comments':
                                comment_data = change.get('value', {})
                                media_id = comment_data.get('media_id')
                                comment_id = comment_data.get('id')
                                comment_text = comment_data.get('text')
                                
                                if comment_id and comment_text:
                                    logger.info(f"Processing comment {comment_id} on media {media_id}: {comment_text[:50]}...")
                                    # Get response from Templar chatbot
                                    response = chat_with_knight(comment_text)
                                    
                                    # Reply to the comment
                                    instagram.reply_to_comment(comment_id, response)
            
            return jsonify(success=True), 200
        except Exception as e:
            error_msg = f"Error processing webhook: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return jsonify(success=False, error=str(e)), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return jsonify(status="healthy"), 200

if __name__ == '__main__':
    logger.info("Starting Instagram Templar Bot")
    app.run(port=3000)