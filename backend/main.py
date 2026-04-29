from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents import build_graph
from dotenv import load_dotenv
import json
import asyncio

load_dotenv()

app = FastAPI(title="AI Task Manager API")

app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
)


class TaskRequest(BaseModel):
      task: str


@app.get("/")
def root():
      return {"status": "AI Task Manager API running", "version": "1.0.0"}


@app.post("/api/run")
async def run_task(request: TaskRequest):
      async def stream_agents():
                agent_order = ["planner", "researcher", "writer", "reviewer"]
                agent_meta = {
                    "planner":    {"name": "Planner",    "icon": "map",    "desc": "Breaking down the task..."},
                    "researcher": {"name": "Researcher", "icon": "search", "desc": "Gathering insights..."},
                    "writer":     {"name": "Writer",     "icon": "pencil", "desc": "Drafting the response..."},
                    "reviewer":   {"name": "Reviewer",   "icon": "check",  "desc": "Reviewing and polishing..."},
                }
                state = {
                    "task": request.task,
                    "plan": "",
                    "research": "",
                    "draft": "",
                    "final": "",
                    "steps": []
                }
                graph = build_graph()
                for agent_key in agent_order:
                              meta = agent_meta[agent_key]
                              start_event = {"type": "agent_start", "agent": meta["name"], "icon": meta["icon"], "desc": meta["desc"]}
                              yield f"data: {json.dumps(start_event)}\n\n"
                              await asyncio.sleep(0.05)
                              try:
                                                async for chunk in graph.astream(state, {"recursion_limit": 10}):
                                                                      if agent_key in chunk:
                                                                                                state = chunk[agent_key]
                                                                                                break
                              except Exception as e:
                                                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                                                return
                                            output = state["steps"][-1]["output"] if state["steps"] else ""
                              done_event = {"type": "agent_done", "agent": meta["name"], "icon": meta["icon"], "output": output}
                              yield f"data: {json.dumps(done_event)}\n\n"
                              await asyncio.sleep(0.1)
                          final_event = {"type": "final", "result": state.get("final", "")}
                yield f"data: {json.dumps(final_event)}\n\n"
                yield "data: [DONE]\n\n"

      return StreamingResponse(
          stream_agents(),
          media_type="text/event-stream",
          headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
      )
