import json
import os
from flask import Flask, request, Response, stream_with_context
import google.generativeai as genai

app = Flask(__name__)

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


def get_model():
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    return genai.GenerativeModel("gemini-1.0-pro")


def generate_stream(task):
    model = get_model()
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

            response = model.generate_content(prompt)
            output = response.text

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
