# MyChat

A clean, fast chatbot web app built with **Flask** and an open-source LLM from Hugging Face. It handles a wide range of everyday tasks: answering questions, writing and editing, summarizing, brainstorming, explaining concepts, and basic coding help.

## Features

- Flask backend serving a custom chat interface (light and dark themes)
- Uses `Qwen/Qwen2.5-0.5B-Instruct` by default: small, free, Apache-2.0, runs on CPU
- Conversation memory (recent context is sent with each message)
- Typing indicator, code-block formatting, suggestion chips, clear-chat button
- Docker support

## Project structure

```
LLM_ChatBotAI/
├── app.py                 # Flask app + model code
├── requirements.txt
├── Dockerfile
├── .gitignore
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    ├── js/script.js
    └── img/               # logo, avatars, favicon
```

## Run locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. The first start downloads the model (about 1 GB) and may take a minute.

## Choose a different model

Set the `MODEL_NAME` environment variable to any chat/instruct model on Hugging Face:

```bash
MODEL_NAME="Qwen/Qwen2.5-1.5B-Instruct" python app.py   # better answers, needs more RAM
```

Change the port the same way: `PORT=8080 python app.py`.

## Run with Docker

```bash
docker build -t mychat .
docker run -p 5000:5000 mychat
```

## API

`POST /chatbot` with JSON `{"messages": [{"role": "user", "content": "Hello"}]}` returns `{"response": "..."}`.
`GET /health` returns the loaded model and device.

## License

MIT
