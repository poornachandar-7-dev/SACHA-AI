"""
SACHA — FastAPI backend entry point.
"""

import os
import signal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai import generate_reply
from memory import save_message, get_history
from tools import run_tool, detect_tool_call

app = FastAPI(title="SACHA Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before deploying publicly
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
def health_check():
    return {"status": "SACHA backend is running"}


@app.get("/history")
def history():
    return {"history": get_history()}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    user_message = request.message
    save_message("user", user_message)

    # Check if the message is asking for a tool action (e.g. "open notepad" / "open youtube" / etc.)
    tool_name, tool_arg = detect_tool_call(user_message)
    if tool_name:
        reply = run_tool(tool_name, tool_arg)
    else:
        # Give the AI recent history for basic context
        context = get_history(limit=6)
        reply = generate_reply(user_message, context=context)

    save_message("assistant", reply)
    return ChatResponse(reply=reply)


@app.post("/shutdown")
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return {"status": "shutting down"}