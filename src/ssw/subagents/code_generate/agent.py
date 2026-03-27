import asyncio
import sys
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from ssw.subagents.code_generate.model import CodeGenerateInput
from ssw.subagents.code_generate.tool import  create_workspace, select_coding_ide, \
    gener_code_plan_by_claude_code, review_plan_node, route_after_review, execute_claude_code_plan, git_commit_push_node




agent_builder = StateGraph(CodeGenerateInput)



agent_builder.add_node("create_workspace", create_workspace)
agent_builder.add_node("gener_code_plan_by_claude_code", gener_code_plan_by_claude_code)
agent_builder.add_node("review_plan", review_plan_node)
agent_builder.add_node("execute_claude_code_plan", execute_claude_code_plan)
agent_builder.add_node("git_commit_push", git_commit_push_node)


agent_builder.add_edge(START, "create_workspace")
agent_builder.add_conditional_edges(
    "create_workspace", select_coding_ide, {"claude": "gener_code_plan_by_claude_code"}
)
agent_builder.add_edge("gener_code_plan_by_claude_code", "review_plan")
agent_builder.add_conditional_edges(
    "review_plan",
    route_after_review,
    {
        "execute_claude": "execute_claude_code_plan",
        "revise_claude": "gener_code_plan_by_claude_code",
        "reject": END,
    },
)

agent_builder.add_edge("execute_claude_code_plan", "git_commit_push")
agent_builder.add_edge("git_commit_push", END)
graph = agent_builder.compile()




