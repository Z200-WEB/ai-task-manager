import json
import os
from http.server import BaseHTTPRequestHandler
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, List


def get_llm():
    return ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
        google_api_key=os.environ.get("GEMINI_API_KEY"),
        temperature=0.7,
    )
h

class AgentState(TypedDict):
    task: str
    plan: str
    research: str
    draft: str
    final: str
    steps: List[dict]


def planner_agent(state):
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content="You are a Planner AI agent. Break down the given task into 3-4 clear, actionable steps. Be concise and structured. Output as a numbered list."),
        HumanMessage(content=f"Task: {state['task']}")
    ])
    step = {"agent": "Planner", "icon": "map", "status": "done", "output": response.content}
    return {**state, "plan": response.content, "steps": state["steps"] + [step]}


def researcher_agent(state):
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content="You are a Research AI agent. Based on the task and plan, provide relevant insights, facts, best practices, and key points. Be informative but concise."),
        HumanMessage(content=f"Task: {state['task']}\n\nPlan:\n{state['plan']}")
    ])
    step = {"agent": "Researcher", "icon": "search", "status": "done", "output": response.content}
    return {**state, "research": response.content, "steps": state["steps"] + [step]}


def writer_agent(state):
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content="You are a Writer AI agent. Using the task, plan, and research, create a comprehensive, well-structured draft. Make it practical and actionable."),
        HumanMessage(content=f"Task: {state['task']}\n\nPlan:\n{state['plan']}\n\nResearch:\n{state['research']}")
    ])
    step = {"agent": "Writer", "icon": "pencil", "status": "done", "output": response.content}
    return {**state, "draft": response.content, "steps": state["steps"] + [step]}


def reviewer_agent(state):
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content="You are a Reviewer AI agent. Review the draft, fix issues, enhance clarity, add missing points, and output the final polished version directly."),
        HumanMessage(content=f"Original Task: {state['task']}\n\nDraft:\n{state['draft']}")
    ])
    step = {"agent": "Reviewer", "icon": "check", "status": "done", "output": response.content}
    return {**state, "final": response.content, "steps": state["steps"] + [step]}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_agent)
    graph.add_node("researcher", researcher_agent)
    graph.add_node("writer", writer_agent)
    graph.add_node("reviewer", reviewer_agent)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", "reviewer")
    graph.add_edge("reviewer", END)
    return graph.compile()


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            task = data.get("task", "").strip()

            if not task:
                self.send_response(400)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "task is required"}).encode())
                return

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            agent_order = ["planner", "researcher", "writer", "reviewer"]
            agent_meta = {
                "planner":    {"name": "Planner",    "icon": "map",    "desc": "Breaking down the task..."},
                "researcher": {"name": "Researcher", "icon": "search", "desc": "Gathering insights..."},
                "writer":     {"name": "Writer",     "icon": "pencil", "desc": "Drafting the response..."},
                "reviewer":   {"name": "Reviewer",   "icon": "check",  "desc": "Reviewing and polishing..."},
            }

            state = {"task": task, "plan": "", "research": "", "draft": "", "final": "", "steps": []}
            graph = build_graph()

            for agent_key in agent_order:
                meta = agent_meta[agent_key]
                start_event = {"type": "agent_start", "agent": meta["name"], "icon": meta["icon"], "desc": meta["desc"]}
                self._send_event(start_event)
                try:
                    for chunk in graph.stream(state, {"recursion_limit": 10}):
                        if agent_key in chunk:
                            state = chunk[agent_key]
                            break
                except Exception as e:
                    self._send_event({"type": "error", "message": str(e)})
                    return
                output = state["steps"][-1]["output"] if state["steps"] else ""
                self._send_event({"type": "agent_done", "agent": meta["name"], "icon": meta["icon"], "output": output})

            self._send_event({"type": "final", "result": state.get("final", "")})
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

        except Exception as e:
            try:
                self._send_event({"type": "error", "message": str(e)})
            except Exception:
                pass

    def _send_event(self, data):
        msg = f"data: {json.dumps(data)}\n\n"
        self.wfile.write(msg.encode())
        self.wfile.flush()

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
