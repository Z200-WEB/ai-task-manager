import json
import os
from http.server import BaseHTTPRequestHandler
import google.generativeai as genai


def get_model():
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        return genai.GenerativeModel("gemini-1.5-flash-latest")


AGENTS = [h
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


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            task = body.get("task", "").strip()
            if not task:
                self.send_response(400)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "task required"}).encode())
                return

            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            model = get_model()
            context = {"task": task, "plan": "", "research": "", "draft": ""}

            for agent in AGENTS:
                self._emit({"type": "agent_start", "agent": agent["name"], "icon": agent["icon"], "desc": agent["desc"]})
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

                    self._emit({"type": "agent_done", "agent": agent["name"], "icon": agent["icon"], "output": output})

                    if agent["key"] == "reviewer":
                        self._emit({"type": "final", "result": output})

                except Exception as e:
                    self._emit({"type": "error", "message": str(e)})
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                    return

            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

        except Exception as e:
            try:
                self._emit({"type": "error", "message": str(e)})
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except Exception:
                pass

    def _emit(self, data):
        msg = f"data: {json.dumps(data)}\n\n"
        self.wfile.write(msg.encode())
        self.wfile.flush()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
