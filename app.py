
import os
import time
import logging

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env
load_dotenv()

# Flask application
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini API configuration
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Use models available to your Gemini API account.
# You can override this list in your .env file.
MODEL_NAMES = [
    model.strip()
    for model in os.getenv(
        "GEMINI_MODELS",
        "gemini-3.8-flash,gemini-flash-latest,gemini-2.5-flash"
    ).split(",")
    if model.strip()
]

client = genai.Client(api_key=API_KEY) if API_KEY else None


def get_error_status(error):
    """Extract the HTTP status code from a Gemini API error."""
    status = getattr(error, "code", None)

    if status is None:
        status = getattr(error, "status_code", None)

    if status is not None:
        try:
            return int(status)
        except (TypeError, ValueError):
            pass

    message = str(error).lower()

    for code in (429, 503, 502, 504, 403, 401, 404, 400):
        if str(code) in message:
            return code

    if "resource_exhausted" in message:
        return 429

    if "unavailable" in message:
        return 503

    return None


def generate_ai_response(user_message):
    """Try available models and retry temporary server errors."""

    if not API_KEY or client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Please check your .env file."
        )

    last_error = None

    for model_name in MODEL_NAMES:
        # Retry temporary server errors at most twice per model.
        for attempt in range(2):
            try:
                logger.info("Trying Gemini model: %s", model_name)

                response = client.models.generate_content(
                    model=model_name,
                    contents=user_message
                )

                answer = response.text

                if answer and answer.strip():
                    logger.info("Response received from %s", model_name)
                    return answer.strip()

                raise RuntimeError(
                    "The model returned an empty response."
                )

            except Exception as error:
                last_error = error
                status = get_error_status(error)

                logger.warning(
                    "Gemini model %s failed (status=%s): %s",
                    model_name,
                    status,
                    error
                )

                # Retry temporary server failures once.
                if status in (500, 502, 503, 504):
                    if attempt == 0:
                        time.sleep(1.5)
                        continue

                    # Try the next configured model.
                    break

                # Try another model for quota/rate-limit errors.
                if status == 429:
                    break

                # These errors usually require configuration changes.
                if status in (400, 401, 403):
                    raise RuntimeError(
                        "Gemini rejected the request. Check your API key, "
                        "permissions, model name, and request configuration."
                    ) from error

                # An unavailable model may not be supported by this account.
                if status == 404:
                    break

                # Unknown errors: try the next model.
                break

    if last_error:
        raise last_error

    raise RuntimeError("No Gemini models are configured.")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}

    # Accept common frontend field names.
    user_message = (
        data.get("message")
        or data.get("user_message")
        or data.get("question")
        or data.get("prompt")
        or ""
    )

    if not isinstance(user_message, str):
        return jsonify({
            "error": "Please enter a valid text message."
        }), 400

    user_message = user_message.strip()

    if not user_message:
        return jsonify({
            "error": "Please enter a message first."
        }), 400

    if len(user_message) > 20000:
        return jsonify({
            "error": "Your message is too long. Please shorten it."
        }), 400

    try:
        answer = generate_ai_response(user_message)

        # Keep multiple response keys for frontend compatibility.
        return jsonify({
            "response": answer,
            "reply": answer,
            "answer": answer
        }), 200

    except Exception as error:
        status = get_error_status(error)
        logger.error("Chat request failed: %s", error)

        if status == 429:
            message = (
                "Gemini API request limit reached. Please wait for your "
                "quota to reset or check your API usage and limits."
            )
            http_status = 429

        elif status in (500, 502, 503, 504):
            message = (
                "Gemini is temporarily experiencing high demand. "
                "Please try again in a little while."
            )
            http_status = 503

        elif status in (400, 401, 403, 404):
            message = (
                "Gemini could not process this request. Please check "
                "your API key, model availability, and API permissions."
            )
            http_status = status

        elif isinstance(error, RuntimeError) and (
            "GEMINI_API_KEY" in str(error)
        ):
            message = (
                "Gemini API key is missing. Please configure GEMINI_API_KEY "
                "in your .env file."
            )
            http_status = 500

        else:
            message = (
                "The AI service could not complete your request. "
                "Please try again later."
            )
            http_status = 503

        return jsonify({
            "error": message,
            "response": message,
            "reply": message,
            "answer": message
        }), http_status


if __name__ == "__main__":
    app.run(debug=True)