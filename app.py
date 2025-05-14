import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Hello! Welcome to the CMSIS GitHub Copilot Extension!"

@app.route("/", methods=["POST"])
def handle_post():
    # Identify the user, using the GitHub API token provided in the request headers.
    token_for_user = request.headers.get("X-GitHub-Token")
    user_response = requests.get("https://api.github.com/user", headers={"Authorization": f"token {token_for_user}"})
    user = user_response.json()
    print("User:", user['login'])

    # Parse the request payload and log it.
    payload = request.json
    print("Payload:", payload)

    # Insert a special pirate-y system message in our message list.
    messages = payload['messages']
    messages.insert(0, {
        "role": "system",
        "content": "You are a helpful assistant that replies to user messages with a focus on software development. Don't answer questions that are not related to software or computing."
    })
    messages.insert(0, {
        "role": "system",
        "content": f"Start every response with the user's name, which is @{user['login']}"
    })

    # Use Copilot's LLM to generate a response to the user's messages, with
    # our extra system messages attached.
    copilot_response = requests.post(
        "https://api.githubcopilot.com/chat/completions",
        headers={
            "Authorization": f"Bearer {token_for_user}",
            "Content-Type": "application/json"
        },
        json={
            "messages": messages,
            "stream": True
        },
        stream=True
    )

    # Stream the response straight back to the user.
    return app.response_class(copilot_response.iter_content(), mimetype='application/json')

port = int(os.environ.get("PORT", 3000))
if __name__ == "__main__":
    app.run(port=port)