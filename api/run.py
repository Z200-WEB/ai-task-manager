from http.server import BaseHTTPRequestHandler
import json
import os
import requests

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

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
          "generationConfig": {"maxOutputTokens": 2048},
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
            break

    yield "data: [DONE]\n\n"


class handler(BaseHTTPRequestHandler):
      def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

      def do_POST(self):
                try:
                              content_length = int(self.headers.get("Content-Length", 0))
                              body = self.rfile.read(content_length)
                              data = json.loads(body)
                              task = (data.get("task", "") or "").strip()

                    if not task:
                                      self.send_response(400)
                                      self.send_header("Content-Type", "application/json")
                                      self.send_header("Access-Control-Allow-Origin", "*")
                                      self.end_headers()
                                      self.wfile.write(json.dumps({"error": "task required"}).encode())
                                      return

                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("X-Accel-Buffering", "no")
                    self.end_headers()

              for chunk in generate_stream(task):
                                self.wfile.write(chunk.encode())
                                self.wfile.flush()

except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
