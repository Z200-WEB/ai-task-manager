import json
import os
import requests
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

AGENTS = [
    {
        "key": "planner",
        "name": "Planner",
        "icon": "map",
        "desc": "Breaking down the task...",
        "prompt": "You are a Planner AI. Break down the given task into 3-4 clear, actionable steps. Be concise and structured. Output as a numbered list.",
    },
    {
        "key": "researcher",
        "name": "Researcher",
        "icon": "search",
        "desc": "Gathering insights...",
        "prompt": "You are a Researcher AI. Based on the task and plan provided, give relevant insights, facts, best practices, and key points. Be informative but concise.",
    },
    {
        "key": "writer",
        "name": "Writer",
        "icon": "pencil",
        "desc": "Drafting the response...",
        "prompt": "You are a Writer AI. Using the task, plan, and research provided, create a comprehensive, well-structured draft. Make it practical and actionable.",
    },
    {
        "key": "reviewer",
        "name": "Reviewer",
        "icon": "check",
        "desc": "Reviewing and polishing...",
        "prompt": "You are a Reviewer AI. Review the draft and improve it. Fix issues, enhance clarity, add missing points, and output the final polished version directly.",
    },
]


def call_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    url = f"{GEMINI_API_URL}?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2048}
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def generate_stream(task):
    context = {"task": task, "plan": "", "research": "", "draft": ""}

    for agent in AGENTS:
        yield f"data: {json.dumps({'type': 'agent_start', 'agent': agent['name'], 'icon': agent['icon'], 'desc': agent['desc']})}\n\n"

        try:
            if agent["key"] == "planner":
                prompt = f"{agent['prompt']}\n\nTask: {task}"
            elif agent["key"] == "researcher":
                prompt = f"{agent['prompt']}\n\nTask: {task}\n\nPlan:\n{context['plan']}"
            elif agent["key"] == "writer":
                prompt = f"{agent['prompt']}\n\nTask: {task}\n\nPlan:\n{context['plan']}\n\nResearch:\n{context['research']}"
            else:
                prompt = f"{agent['prompt']}\n\nOriginal Task: {task}\n\nDraft:\n{context['draft']}"

            output = call_gemini(prompt)

            if agent["key"] == "planner":
                context["plan"] = output
            elif agent["key"] == "researcher":
                context["research"] = output
            elif agent["key"] == "writer":
                context["draft"] = output

            yield f"data: {json.dumps({'type': 'agent_done', 'agent': agent['name'], 'icon': agent['icon'], 'output': output})}\n\n"

            if agent["key"] == "reviewer":
                yield f"data: {json.dumps({'type': 'final', 'result': output})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
            return

    yield "data: [DONE]\n\n"


@app.route("/api/run", methods=["POST", "OPTIONS"])
def run():
    if request.method == "OPTIONS":
        resp = Response("")
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    try:
        body = request.get_json(force=True)
        task = (body.get("task", "") or "").strip()
        if not task:
            resp = Response(json.dumps({"error": "task required"}), status=400, mimetype="application/json")
            resp.headers["Access-Control-Allow-Origin"] = "*"
            return resp

        def stream():
            yield from generate_stream(task)

        resp = Response(stream_with_context(stream()), mimetype="text/event-stream")
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["X-Accel-Buffering"] = "no"
        return resp

    except Exception as e:
        resp = Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp
