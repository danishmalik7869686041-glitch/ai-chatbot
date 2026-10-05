import os
import webbrowser
from threading import Timer

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY .env file mein nahi mili.")

client = genai.Client(api_key=API_KEY)

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "error": "Please enter a message."
        }), 400

    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_message,
        )

        return jsonify({
            "response": response.text
        })

    except Exception as e:
        print("AI Error:", e)

        return jsonify({
            "error": "Sorry, AI response nahi aa raha. Please try again."
        }), 500


def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")


if __name__ == "__main__":
    Timer(1.5, open_browser).start()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )