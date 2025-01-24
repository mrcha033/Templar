from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verification challenge
        verify_token = 'templar_webhook_verify_token_2024'
        if request.args.get('hub.verify_token') == verify_token:
            return request.args.get('hub.challenge')
        return 'Verification token mismatch', 403

    if request.method == 'POST':
        # Handle incoming Webhook events
        data = request.json
        print(data)  # Process the data as needed
        return jsonify(success=True), 200

if __name__ == '__main__':
    app.run(port=3000)