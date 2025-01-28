from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from templar import chat_with_knight
import requests
import logging
import traceback
import sys
from datetime import datetime, timedelta
import asyncio
import time
from requests_oauthlib import OAuth1Session
import hmac
import hashlib
import base64
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure logging for Vercel environment
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Required environment variables
REQUIRED_ENV_VARS = {
    'X_CLIENT_ID': os.getenv('X_CLIENT_ID'),
    'X_CLIENT_SECRET': os.getenv('X_CLIENT_SECRET'),
    'X_ACCESS_TOKEN': os.getenv('X_ACCESS_TOKEN'),
    'X_ACCESS_TOKEN_SECRET': os.getenv('X_ACCESS_TOKEN_SECRET'),
    'X_API_KEY': os.getenv('X_API_KEY'),
    'X_API_KEY_SECRET': os.getenv('X_API_KEY_SECRET'),
    'X_BEARER_TOKEN': os.getenv('X_BEARER_TOKEN'),
    'IG_ACCESS_TOKEN': os.getenv('IG_ACCESS_TOKEN'),
    'IG_ACCOUNT_ID': os.getenv('IG_ACCOUNT_ID'),
    'IG_VERIFY_TOKEN': os.getenv('IG_VERIFY_TOKEN'),
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
    'INSTAGRAM_ACCOUNT_ID': os.getenv('INSTAGRAM_ACCOUNT_ID')
}

# Check for missing environment variables
missing_vars = [var for var, value in REQUIRED_ENV_VARS.items() if not value]
if missing_vars:
    logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize OAuth session
oauth = OAuth1Session(
    client_key=REQUIRED_ENV_VARS['X_CLIENT_ID'],
    client_secret=REQUIRED_ENV_VARS['X_CLIENT_SECRET'],
    resource_owner_key=REQUIRED_ENV_VARS['X_ACCESS_TOKEN'],
    resource_owner_secret=REQUIRED_ENV_VARS['X_ACCESS_TOKEN_SECRET']
)

class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window  # in seconds
        self.requests = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Check if request can be made within rate limits"""
        async with self.lock:
            now = datetime.now()
            # Remove old requests
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < timedelta(seconds=self.time_window)]
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            # Calculate wait time if rate limit exceeded
            oldest_request = self.requests[0]
            wait_time = (oldest_request + timedelta(seconds=self.time_window) - now).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self.requests = self.requests[1:] + [now]
                return True
            
            return False

class APIHandler:
    def log_api_error(self, error, endpoint, method="GET", data=None):
        """Log API errors with detailed information"""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "endpoint": endpoint,
            "method": method,
            "data": data
        }
        logger.error(f"API Error: {error_info}")
        return error_info

class InstagramHandler(APIHandler):
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/v19.0/{REQUIRED_ENV_VARS['INSTAGRAM_ACCOUNT_ID']}"
        self.headers = {
            "Authorization": f"Bearer {REQUIRED_ENV_VARS['IG_ACCESS_TOKEN']}",
            "Content-Type": "application/json"
        }

    def get_messages(self):
        """Fetch recent messages from Instagram"""
        endpoint = f"{self.base_url}/messages"
        params = {"fields": "message,from"}

        try:
            logger.info(f"Fetching messages from {endpoint}")
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            
            try:
                messages = response.json().get("data", [])
                logger.info(f"Fetched {len(messages)} messages")
                return messages
            except ValueError:
                logger.error("Failed to decode JSON response")
                return []
            
        except requests.exceptions.RequestException as e:
            self.log_api_error(e, endpoint)
            return []

    def send_message(self, user_id, message):
        """Send a message to a specific user"""
        endpoint = f"{self.base_url}/messages"
        data = {
            "recipient": {"id": user_id},
            "message": {"text": message}
        }
        
        try:
            logger.info(f"Sending message to user {user_id}")
            response = requests.post(endpoint, headers=self.headers, json=data)
            response.raise_for_status()
            logger.info(f"Message sent successfully to user {user_id}")
            return True
        except requests.exceptions.RequestException as e:
            self.log_api_error(e, endpoint, "POST", data)
            return False

    def process_messages(self):
        """Process new messages and respond using the Templar chatbot"""
        try:
            messages = self.get_messages()
            logger.info(f"Processing {len(messages)} messages")
            
            for message in messages:
                user_id = message.get("from", {}).get("id")
                user_message = message.get("message")
                
                if user_id and user_message:
                    logger.info(f"Processing message from user {user_id}: {user_message[:50]}...")
                    
                    # Get response from Templar chatbot
                    response = chat_with_knight(user_message)
                    
                    if not response:
                        logger.warning(f"No response generated for user {user_id}")
                        response = "죄송합니다. 현재 답변을 생성할 수 없습니다."
                    
                    # Send response back to user
                    self.send_message(user_id, response)
                    
            return True
        except Exception as e:
            logger.error(f"Error processing messages: {str(e)}")
            return False

    def post_instagram_photo(self, image_url, caption):
        """Post a photo to Instagram"""
        endpoint = f"{self.base_url}/media"
        data = {
            "image_url": image_url,
            "caption": caption,
            "access_token": REQUIRED_ENV_VARS['IG_ACCESS_TOKEN']
        }

        try:
            logger.info(f"Posting image to Instagram: {image_url}")
            response = requests.post(endpoint, headers=self.headers, json=data)
            response.raise_for_status()
            logger.info("Image posted successfully")
            return True
        except requests.exceptions.RequestException as e:
            self.log_api_error(e, endpoint, "POST", data)
            return False

class XHandler(APIHandler):
    def __init__(self):
        self.api_version = "2"
        self.base_url = f"https://api.twitter.com/v{self.api_version}"
        
        # Initialize OAuth1 session
        self.oauth = OAuth1Session(
            REQUIRED_ENV_VARS['X_CLIENT_ID'],
            client_secret=REQUIRED_ENV_VARS['X_CLIENT_SECRET'],
            resource_owner_key=REQUIRED_ENV_VARS['X_ACCESS_TOKEN'],
            resource_owner_secret=REQUIRED_ENV_VARS['X_ACCESS_TOKEN_SECRET']
        )

    def get_user_id(self):
        """Get authenticated user ID"""
        endpoint = f"{self.base_url}/users/me"
        
        try:
            logger.info("Fetching authenticated user ID")
            response = self.oauth.get(endpoint)
            response.raise_for_status()
            user_data = response.json().get("data", {})
            return user_data.get("id")
        except requests.exceptions.RequestException as e:
            self.log_api_error(e, endpoint)
            return None

    def get_mentions(self, since_id=None):
        """Fetch recent mentions"""
        user_id = self.get_user_id()
        if not user_id:
            logger.error("Failed to get user ID")
            return []

        endpoint = f"{self.base_url}/users/{user_id}/mentions"
        params = {
            "expansions": "referenced_tweets.id,author_id",
            "tweet.fields": "conversation_id,created_at,text"
        }
        if since_id:
            params["since_id"] = since_id
        
        try:
            logger.info("Fetching mentions from X")
            response = self.oauth.get(endpoint, params=params)
            response.raise_for_status()
            
            # Log rate limit info
            remaining = response.headers.get('x-rate-limit-remaining')
            reset_time = response.headers.get('x-rate-limit-reset')
            logger.info(f"Rate limit - Remaining: {remaining}, Reset time: {reset_time}")
            
            mentions = response.json().get("data", [])
            logger.info(f"Fetched {len(mentions)} mentions")
            return mentions
        except requests.exceptions.RequestException as e:
            self.log_api_error(e, endpoint)
            return []

    def reply_to_tweet(self, tweet_id, message):
        """Reply to a tweet"""
        endpoint = f"{self.base_url}/tweets"
        data = {
            "reply": {
                "in_reply_to_tweet_id": tweet_id
            },
            "text": message
        }
        
        try:
            logger.info(f"Replying to tweet {tweet_id}")
            response = self.oauth.post(endpoint, json=data)
            response.raise_for_status()
            
            # Log rate limit info
            remaining = response.headers.get('x-rate-limit-remaining')
            reset_time = response.headers.get('x-rate-limit-reset')
            logger.info(f"Rate limit - Remaining: {remaining}, Reset time: {reset_time}")
            
            logger.info(f"Successfully replied to tweet {tweet_id}")
            return True
        except requests.exceptions.RequestException as e:
            self.log_api_error(e, endpoint, "POST", data)
            return False

    def process_mentions(self, since_id=None):
        """Process mentions and respond using the Templar chatbot"""
        try:
            mentions = self.get_mentions(since_id)
            logger.info(f"Processing {len(mentions)} mentions")
            
            for mention in mentions:
                tweet_id = mention.get("id")
                tweet_text = mention.get("text")
                
                if tweet_id and tweet_text:
                    # Remove the mention handle from the text
                    clean_text = ' '.join(word for word in tweet_text.split() 
                                        if not word.startswith('@'))
                    
                    logger.info(f"Processing mention {tweet_id}: {clean_text[:50]}...")
                    
                    # Get response from Templar chatbot
                    response = chat_with_knight(clean_text)
                    
                    if not response:
                        logger.warning(f"No response generated for tweet {tweet_id}")
                        response = "죄송합니다. 현재 답변을 생성할 수 없습니다."
                    
                    # Reply to the tweet
                    self.reply_to_tweet(tweet_id, response)
                    
            # Return the ID of the most recent mention for pagination
            return mentions[0].get("id") if mentions else since_id
        except Exception as e:
            logger.error(f"Error processing mentions: {str(e)}")
            return since_id

# Initialize handlers
instagram_handler = InstagramHandler()
x_handler = XHandler()

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    """Handle favicon requests"""
    return '', 204  # No content response

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook for Instagram"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == REQUIRED_ENV_VARS['IG_VERIFY_TOKEN']:
            logger.info("Webhook verified")
            return challenge, 200
        else:
            logger.warning("Webhook verification failed")
            return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle webhook events from Instagram"""
    try:
        instagram_handler.process_messages()
        return 'OK', 200
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return jsonify(status="healthy"), 200

@app.route('/process_x_mentions', methods=['POST'])
def process_x_mentions():
    """Endpoint to process X mentions"""
    try:
        since_id = request.json.get('since_id')
        new_since_id = x_handler.process_mentions(since_id)
        return jsonify({"success": True, "since_id": new_since_id}), 200
    except Exception as e:
        logger.error(f"Error processing X mentions: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/webhook/x', methods=['POST'])
def x_webhook():
    """Handle X webhook events"""
    try:
        # Verify the webhook signature
        signature = request.headers.get('x-twitter-webhooks-signature')
        if not signature:
            logger.warning("Missing webhook signature")
            return jsonify({"error": "Missing signature"}), 400

        # Get the raw request body
        raw_data = request.get_data(as_text=True)
        
        # Log webhook payload for debugging
        logger.info(f"Received webhook from X: {raw_data[:200]}...")

        # Parse the webhook payload
        data = request.json
        
        # Check if this is a mention event
        if data.get('tweet_create_events'):
            for tweet in data['tweet_create_events']:
                # Check if this tweet mentions us
                if tweet.get('in_reply_to_user_id') == x_handler.get_user_id():
                    tweet_id = tweet.get('id')
                    tweet_text = tweet.get('text')
                    
                    if tweet_id and tweet_text:
                        # Remove the mention handle from the text
                        clean_text = ' '.join(word for word in tweet_text.split() 
                                            if not word.startswith('@'))
                        
                        logger.info(f"Processing mention from webhook {tweet_id}: {clean_text[:50]}...")
                        
                        # Get response from Templar chatbot
                        response = chat_with_knight(clean_text)
                        
                        if not response:
                            logger.warning(f"No response generated for tweet {tweet_id}")
                            response = "죄송합니다. 현재 답변을 생성할 수 없습니다."
                        
                        # Reply to the tweet
                        x_handler.reply_to_tweet(tweet_id, response)

        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Error processing X webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/x', methods=['GET'])
def verify_x_webhook():
    """Verify X webhook subscription"""
    try:
        # Get the challenge parameter
        crc_token = request.args.get('crc_token')
        if not crc_token:
            return jsonify({"error": "Missing crc_token"}), 400

        # Create HMAC SHA-256 hash
        hmac_token = hmac.new(
            key=REQUIRED_ENV_VARS['X_CLIENT_SECRET'].encode('utf-8'),
            msg=crc_token.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()

        # Encode the hash in base64
        response_token = base64.b64encode(hmac_token).decode('utf-8')

        # Return the response
        return jsonify({"response_token": f"sha256={response_token}"}), 200
    except Exception as e:
        logger.error(f"Error verifying X webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Templar Bot Server")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))