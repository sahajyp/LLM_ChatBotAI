"""MyChat - a small, fast Flask chatbot powered by an open-source instruct LLM.

Run locally:
    pip install -r requirements.txt
    python app.py            # serves on http://localhost:5000

Swap the model without touching code:
    MODEL_NAME="Qwen/Qwen2.5-1.5B-Instruct" python app.py
"""

import os
import threading

import torch
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from transformers import AutoModelForCausalLM, AutoTokenizer

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
# Qwen2.5-0.5B-Instruct: Apache-2.0 licensed, ~1 GB download, runs on a normal
# CPU, and is strong for its size at Q&A, writing, summarizing, coding and
# basic reasoning. For noticeably better answers (needs ~4-6 GB RAM) set
# MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct.
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct")
PORT = int(os.environ.get("PORT", 5000))

SYSTEM_PROMPT = (
    "You are MyChat, a friendly and knowledgeable AI assistant. "
    "Answer clearly and concisely. If you are unsure, say so instead of guessing. "
    "Use short paragraphs, and put code inside triple-backtick code blocks."
)

MAX_HISTORY_MESSAGES = 12   # most recent messages kept as context
MAX_INPUT_TOKENS = 1536     # prompt budget; oldest messages are dropped first
MAX_NEW_TOKENS = 384        # length cap for each reply
MAX_MESSAGE_CHARS = 4000    # per-message safety limit

# --------------------------------------------------------------------------
# Model loading (happens once at startup)
# --------------------------------------------------------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

print(f"Loading {MODEL_NAME} on {device} ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=dtype)
model.to(device)
model.eval()
print("Model ready.")

# Only one generation at a time keeps memory use predictable.
generation_lock = threading.Lock()

app = Flask(__name__)
CORS(app)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def clean_messages(raw):
    """Validate the chat history sent by the browser."""
    cleaned = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content.strip()[:MAX_MESSAGE_CHARS]})
    return cleaned[-MAX_HISTORY_MESSAGES:]


def build_inputs(history):
    """Apply the model's chat template, dropping old turns if the prompt is too long."""
    history = list(history)
    while True:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(text, return_tensors="pt")
        if inputs["input_ids"].shape[1] <= MAX_INPUT_TOKENS or len(history) <= 1:
            return inputs
        history.pop(0)


def generate_reply(history):
    inputs = build_inputs(history).to(device)
    with generation_lock, torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
        )
    # Keep only the newly generated tokens (drop the prompt).
    new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", model_name=MODEL_NAME.split("/")[-1])


@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json(silent=True) or {}

    history = clean_messages(data.get("messages"))
    # Backwards compatible with the old {"prompt": "..."} format.
    if not history and isinstance(data.get("prompt"), str) and data["prompt"].strip():
        history = [{"role": "user", "content": data["prompt"].strip()[:MAX_MESSAGE_CHARS]}]

    if not history or history[-1]["role"] != "user":
        return jsonify(error="Please send a message."), 400

    try:
        reply = generate_reply(history)
    except Exception as exc:  # keep the UI alive on unexpected errors
        app.logger.exception("Generation failed")
        return jsonify(error=f"Generation failed: {exc}"), 500

    return jsonify(response=reply or "I'm not sure how to answer that - could you rephrase?")


@app.route("/health")
def health():
    return jsonify(status="ok", model=MODEL_NAME, device=device)


if __name__ == "__main__":
    # host 0.0.0.0 makes the app reachable from lab/cloud IDEs and Docker.
    app.run(host="0.0.0.0", port=PORT, debug=False)
