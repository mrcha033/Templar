from flask import Flask, request, jsonify
import os
from transformers import AutoTokenizer, AutoModelForCausalLM

app = Flask(__name__)

tokenizer = AutoTokenizer.from_pretrained("./model_directory")
model = AutoModelForCausalLM.from_pretrained("./model_directory")

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verification challenge
        verify_token = os.getenv('VERIFY_TOKEN')
        if request.args.get('hub.verify_token') == verify_token:
            return request.args.get('hub.challenge')
        return 'Verification token mismatch', 403

    if request.method == 'POST':
        # Handle incoming Webhook events
        data = request.json
        print(data)  # Process the data as needed
        return jsonify(success=True), 200

@app.route('/predict', methods=['POST'])
def predict():
    input_data = request.json['input']
    inputs = tokenizer(input_data, return_tensors="pt")
    outputs = model.generate(**inputs)
    response = tokenizer.decode(outputs[0])
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(port=3000)