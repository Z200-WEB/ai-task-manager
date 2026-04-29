from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import os


def get_llm():
      return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.7,
      )


class AgentState(TypedDict):
      task: str
      plan: str
      research: str
      draft: str
      final: str
      steps: List[dict]


def planner_agent(state: AgentState) -> AgentState:
      llm = get_llm()
      messages = [
          SystemMessage(content="""You are a Planner AI agent.
  Break down the given task into 3-4 clear, actionable steps.
  Be concise and structured. Output as a numbered list."""),
          HumanMessage(content=f"Task: {state['task']}")
      ]
      response = llm.invoke(messages)
      step = {
          "agent": "Planner",
          "icon": "map",
          "status": "done",
          "output": response.content
      }
      return {**state, "plan": response.content, "steps": state["steps"] + [step]}


def researcher_agent(state: AgentState) -> AgentState:
      llm = get_llm()
      messages = [
          SystemMessage(content="""You are a Research AI agent.
  Based on the task and plan, provide relevant insights, facts,
  best practices, and key points that would be useful.
  Be informative and thorough but concise."""),
          HumanMessage(content=f"Task: {state['task']}\n\nPlan:\n{state['plan']}")
      ]
      response = llm.invoke(messages)
      step = {
          "agent": "Researcher",
          "icon": "search",
          "status": "done",
          "output": response.content
      }
      return {**state, "research": response.content, "steps": state["steps"] + [step]}


def writer_agent(state: AgentState) -> AgentState:
      llm = get_llm()
      messages = [
          SystemMessage(content="""You are a Writer AI agent.
  Using the task, plan, and research provided, create a comprehensive,
  well-structured draft response. Make it practical and actionable."""),
          HumanMessage(content=f"Task: {state['task']}\n\nPlan:\n{state['plan']}\n\nResearch:\n{state['research']}")
      ]
      response = llm.invoke(messages)
      step = {
          "agent": "Writer",
          "icon": "pencil",
          "status": "done",
          "output": response.content
      }
      return {**state, "draft": response.content, "steps": state["steps"] + [step]}


def reviewer_agent(state: AgentState) -> AgentState:
      llm = get_llm()
      messages = [
          SystemMessage(content="""You are a Reviewer AI agent.
  Review the draft and improve it. Fix any issues, enhance clarity,
  add missing important points, and make it polished and professional.
  Output the final improved version directly."""),
          HumanMessage(content=f"Original Task: {state['task']}\n\nDraft:\n{state['draft']}")
      ]
      response = llm.invoke(messages)
      step = {
          "agent": "Reviewer",
          "icon": "check",
          "status": "done",
          "output": response.content
      }
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
