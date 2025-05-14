"""CMSIS‑Solution Assistant
------------------------
Flask micro‑service that
  • receives chat prompts from a client (payload["messages"])
  • enriches them with system instructions
  • forwards everything to the OpenAI **o3** model
  • (optionally) posts the model’s answer back to a GitHub Issue or PR comment

Environment variables
---------------------
OPENAI_API_KEY – secret key for the OpenAI account
PORT             – HTTP port to bind (default: 3000)
"""

import os
import json
from dotenv import load_dotenv
import openai
import requests
from flask import Flask, request, jsonify

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = "o3-2025-04-16"

openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def build_prompt(messages: list[dict], username: str) -> list[dict]:
    """Prepends our two system messages to whatever the client sent."""
    system_prompts = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that replies to user messages with a focus "
                "on software development. Don't answer questions that are not related "
                "to software or computing."
            ),
        },
        {
            "role": "system",
            "content": f"Start every response with the user's name, which is @{username}",
        },
    ]
    return system_prompts + messages


def github_get_user(token: str) -> dict:
    """Return the authenticated user object."""
    resp = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def root():
    return "Hello! I am a CMSIS‑Solution Assistant."


@app.route("/", methods=["POST"])
def handle_post():
    """Main entry‑point used by the client frontend."""

    # --- 1. Authenticate caller via GitHub token --------------------------------
    token_for_user = request.headers.get("X-GitHub-Token")
    if not token_for_user:
        return jsonify({"error": "Missing X-GitHub-Token header"}), 400

    try:
        user = github_get_user(token_for_user)
    except requests.HTTPError as e:
        return jsonify({"error": f"GitHub auth failed: {e}"}), 401

    # --- 2. Parse inbound JSON ---------------------------------------------------
    payload   = request.get_json(silent=True) or {}
    messages  = payload.get("messages", [])

    # --- 3. Build final prompt for o3 -------------------------------------------
    final_messages = build_prompt(messages, user.get("login", "unknown"))

    # --- 4. Ask o3 for an answer (non‑streaming for simplicity) -----------------
    chat_response = openai.ChatCompletion.create(
        model    = OPENAI_MODEL,
        messages = final_messages,
    )
    answer = chat_response.choices[0].message.content

    # --- 6. Return the answer to the caller -------------------------------------
    return jsonify({"reply": answer})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
