import requests

access_token = "your-instagram-access-token"
instagram_account_id = "your-instagram-account-id"

# Post a photo
image_url = "https://example.com/photo.jpg"
caption = "This is a test post from my Templar chatbot."

url = f"https://graph.facebook.com/v12.0/{instagram_account_id}/media"
payload = {
    "image_url": image_url,
    "caption": caption,
    "access_token": access_token
}

response = requests.post(url, data=payload)
print(response.json())