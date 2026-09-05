# AI Career Chatbot — Bhavisha Tak

An AI-powered chatbot that answers questions about my background, skills, and experience as if I'm answering them myself — built for my portfolio/website so recruiters and visitors can "talk to me" directly.

**🔗 Try it live:** [https://ai-career-chatbot-on77.onrender.com]

![Chatbot demo](docs/demo-screenshot.png)
<!-- Replace with an actual screenshot or GIF of the chatbot in action -->

## What it does

- Answers visitor questions about my career, skills, and background — grounded entirely in my CV, so it never invents experience I don't have
- Uses OpenAI function/tool calling to take real actions during the conversation:
  - **`record_unknown_question`** — if it can't answer something, it asks the visitor for their email, then logs the question so I can personally follow up
  - **`record_user_details`** — if a visitor shares their email or expresses interest in getting in touch, it records their details as a lead
- Sends me a real-time notification (via a [Telegram bot](https://core.telegram.org/bots)) whenever either of those happens, so I never miss a recruiter reaching out or a question I should personally answer
- Deployed as a public web app via [Gradio](https://www.gradio.app/) on Render

## How it works

1. My CV (PDF) is parsed at startup and injected into the system prompt as the model's only source of truth
2. Every visitor message goes through an agent loop: the model can either reply directly or call one of the two tools above — the loop keeps running until the model produces a final text reply
3. Tool calls are executed locally and their results are fed back to the model so it can continue the conversation naturally
4. Notifications for unknown questions / new leads are pushed to my phone instantly via Telegram

## Tech stack

- **Python**
- **OpenAI API** (`gpt-4o-mini`) — chat + function/tool calling
- **Gradio** — chat UI
- **Telegram Bot API** — real-time notifications
- **pypdf** — CV parsing

## Running it locally

```bash
git clone https://github.com/your-username/ai-career-chatbot.git
cd ai-career-chatbot
pip install -r requirements.txt
```

### Getting your Telegram bot token and chat ID

**1. Create a bot via @BotFather**
Open Telegram, search for `@BotFather`, and start a chat. Send `/newbot`, give your bot a name and a username (must end in `bot`, e.g. `bhavisha_alerts_bot`). BotFather replies with a token like `123456789:ABCdefGhIJKlmNoPQRstuVwxyz` — this is your `TELEGRAM_BOT_TOKEN`.

**2. Message your new bot once**
Search for your bot's username in Telegram and send it any message (e.g. "hi"). Bots can't message you first, so this step is required.

**3. Search for the ID bot**
Search for `@userinfobot` in Telegram and open the chat.

**4. Click Start and get your ID**
The bot instantly replies with your Id — a 9 or 10-digit number. This is your `TELEGRAM_CHAT_ID`.

**5. Save both values**
Add them to your `.env` file (see below), alongside the token from step 1.

### Environment variables

Create a `.env` file in the project root with:

```
OPENAI_API_KEY=your_openai_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

Place your own CV as `me/Bhavisha_Tak_CV.pdf` (or update `CV_PATH` in `app.py`), then run:

```bash
python app.py
```

The app will be available at `http://127.0.0.1:7860`.

## Deployment

Deployed on **Render**. Secrets (`OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) are configured as environment variables in the Render dashboard rather than committed to the repo.

## What I'd add next

- Replace the "stuff the whole CV into the prompt" approach with a proper vector store for more scalable, precise retrieval as my profile grows
- Add conversation analytics (most-asked questions, drop-off points)
- Multi-language support

## About me

I'm a second-year Computer Science & Engineering student at Pimpri Chinchwad University, working toward a career in data science and applied machine learning. This project was my first hands-on build combining LLM tool-calling, external API integrations, and deployment — [see my full CV/portfolio here].
