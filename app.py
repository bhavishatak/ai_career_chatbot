"""
Bhavisha Tak — Personal AI chatbot
Answers visitor questions about Bhavisha's career/background using her CV as
the only source of truth, and records unanswered questions + leads via Telegram.
"""

import json
import os

import gradio as gr
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv(override=True)

openai = OpenAI()  # reads OPENAI_API_KEY from the environment

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

NAME = "Bhavisha Tak"
CV_PATH = "me/Bhavisha_Tak_CV.pdf"


def load_profile_text(path: str) -> str:
    """Extract all text from the CV PDF. Raises a clear error if the file is missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Could not find '{path}'. Make sure the CV PDF is included in the repo "
            f"at that path before deploying."
        )
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text


PROFILE_TEXT = load_profile_text(CV_PATH)

# ---------------------------------------------------------------------------
# Telegram notifications
# ---------------------------------------------------------------------------


def push(message: str) -> None:
    """Send a push notification via a Telegram bot. Fails silently to a printed
    log if credentials are missing or the request errors, so a notification
    issue never breaks the chat experience for a visitor."""
    print(f"Push: {message}", flush=True)
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        print("Telegram not configured — skipping notification.", flush=True)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=10,
        )
    except requests.RequestException as exc:
        print(f"Telegram notification failed: {exc}", flush=True)


# ---------------------------------------------------------------------------
# Tools the LLM can call
# ---------------------------------------------------------------------------


def record_user_details(email: str, name: str = "Name not provided", notes: str = "not provided") -> dict:
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}


def record_unknown_question(question: str, email: str = "not provided") -> dict:
    push(f"Recording question I couldn't answer: '{question}' (asked by: {email})")
    return {"recorded": "ok"}


record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "The email address of this user"},
            "name": {"type": "string", "description": "The user's name, if they provided it"},
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context",
            },
        },
        "required": ["email"],
        "additionalProperties": False,
    },
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question that couldn't be answered"},
            "email": {
                "type": "string",
                "description": "The visitor's email address, if they provided one when asked. Use 'not provided' if they declined or it wasn't given.",
            },
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}

TOOLS = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json},
]

# Maps tool name -> callable, so handle_tool_calls doesn't need an if/elif chain
TOOL_FUNCTIONS = {
    "record_user_details": record_user_details,
    "record_unknown_question": record_unknown_question,
}


def handle_tool_calls(tool_calls) -> list[dict]:
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            arguments = {}
        print(f"Tool called: {tool_name}", flush=True)

        tool = TOOL_FUNCTIONS.get(tool_name)
        result = tool(**arguments) if tool else {"error": f"Unknown tool '{tool_name}'"}

        results.append(
            {"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id}
        )
    return results


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are acting as {NAME}. You are answering questions on {NAME}'s personal website, \
particularly questions related to {NAME}'s career, background, skills, and experience. \
Your responsibility is to represent {NAME} faithfully and professionally to visitors — potential clients, \
recruiters, or future employers — who come across the site.

You will be given {NAME}'s CV/profile below. This is your ONLY source of truth about {NAME}.

Rules you must follow:
1. Answer questions using ONLY the information present in the profile provided below.
2. If a question asks for something that is not covered in the profile (e.g. personal opinions, \
unlisted skills, salary expectations, availability, or anything not explicitly stated), say that you \
don't have that information rather than guessing or inventing details.
3. Do not fabricate job titles, dates, companies, skills, or achievements that are not in the profile.
4. Stay in character as {NAME} at all times — respond in first person ("I worked at...", "My experience includes...").
5. Keep responses professional, warm, and engaging, as if speaking directly with someone interested in \
{NAME}'s work.
6. If asked something completely unrelated to {NAME}'s career/background (e.g. general trivia, coding help \
for the visitor, etc.), politely redirect the conversation back to {NAME}'s professional background.
7. If you cannot answer a question because the information is not in the profile, first politely ask the \
visitor for their email address so you can follow up personally — do not call any tool on this turn. \
Once the visitor responds (with an email, or by declining), call record_unknown_question with the \
original question and their email (use 'not provided' if they decline or don't give one).
8. If the visitor shares their email address or asks to be contacted, or expresses strong interest in \
getting in touch, you MUST call the record_user_details tool with their email (and name/notes if given).
9. CRITICAL: If a question asks about something not in the profile, do NOT answer it or make excuses. Your VERY FIRST step MUST be to ask the visitor for their email address so {NAME} can follow up with them. Only after they provide an email (or decline) should you call record_unknown_question.

## Profile:
{PROFILE_TEXT}

With this context, please chat with the user, always staying in character as {NAME}.
"""

# ---------------------------------------------------------------------------
# Chat loop
# ---------------------------------------------------------------------------


def chat(message: str, history: list[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": message}
    ]

    done = False
    while not done:
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini", messages=messages, tools=TOOLS
            )
        except Exception as exc:
            print(f"OpenAI call failed: {exc}", flush=True)
            return "Sorry, I'm having trouble responding right now — please try again in a moment."

        finish_reason = response.choices[0].finish_reason

        if finish_reason == "tool_calls":
            assistant_message = response.choices[0].message
            results = handle_tool_calls(assistant_message.tool_calls)
            messages.append(assistant_message)
            messages.extend(results)
        else:
            done = True

    return response.choices[0].message.content


if __name__ == "__main__":
    # server_name="0.0.0.0" makes the app reachable from outside the container
    # (Render/most hosts won't route traffic to 127.0.0.1, the Gradio default).
    # server_port reads Render's dynamically assigned PORT env var, falling
    # back to 7860 for local runs where PORT isn't set.
    gr.ChatInterface(chat, title=f"Chat with {NAME}").launch(
       server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
    )
