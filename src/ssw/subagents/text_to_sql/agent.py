from __future__ import annotations

from pathlib import Path

from deepagents import CompiledSubAgent, create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from ssw.llm import build_llm
from ssw.subagents.text_to_sql.tool import validate_select_sql

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_PATH = "/src/ssw/subagents/text_to_sql/skills"


SYSTEM_PROMPT = """
你是 text-to-SQL Agent，专门把用户的中文或英文自然语言问题转换为 SQL 查询语句。

工作边界：
- 只生成查询 SQL，不生成 INSERT、UPDATE、DELETE、DDL、权限变更或存储过程。
- 优先遵循用户问题中提供的当前数据源名称、类型和 SQL 方言。
- 如果当前数据源类型是 MySQL，生成 MySQL 查询语法。
- 如果当前数据源类型是 ClickHouse，生成 ClickHouse 查询语法。
- 必须优先阅读 Agent skills 目录中的表结构或数据源文档。
- 查询不到表结构时，回复未找到相关数据源或表结构。
- 缺少必要表结构时，先说明缺失信息，不要臆造表或字段。
- 生成 SQL 后必须调用 validate_select_sql 校验是否可以执行。
- 输出必须包含最终 SQL，并用简短中文说明用到的表、过滤条件、排序或聚合逻辑。
- 如果用户问题存在歧义，给出最合理假设；歧义会明显改变结果时，先要求补充条件。

SQL 规范：
- 字段和表名优先使用目标数据库方言支持的引用方式。
- 不使用 SELECT *，除非用户明确要求所有字段。
- 涉及时间范围时写清楚边界条件。
- 涉及分页时默认返回 10 条，除非用户指定数量。
- 对可能重复的业务实体，优先使用 COUNT(DISTINCT ...)。
"""

text_to_sql_agent = create_deep_agent(
    model=build_llm(),
    tools=[validate_select_sql],
    system_prompt=SYSTEM_PROMPT,
    skills=[SKILLS_PATH],
    backend=FilesystemBackend(root_dir=REPO_ROOT, virtual_mode=True),
    name="text-to-sql-agent",
)

text_to_sql_subagent: CompiledSubAgent = {
    "name": "text-to-sql",
    "description": (
        "将自然语言问题转换为 SQL 查询语句。适合需要从子 Agent skills 读取数据源、表结构、"
        "生成 SELECT/CTE 查询、解释查询逻辑和校验 SQL 安全性的任务。"
    ),
    "runnable": text_to_sql_agent,
}
