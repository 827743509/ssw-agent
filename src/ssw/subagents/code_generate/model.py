import operator
from enum import Enum
from langchain_core.messages import AnyMessage
from pydantic import BaseModel, Field
from typing import Literal, Annotated, Any, Dict


class CodeGenerateType(str, Enum):
    DEFAULT = "default"
    BUG_FIX = "bug_fix"


class CodeGenerateInput(BaseModel):
    messages: Annotated[list[AnyMessage], operator.add]
    question: str = Field(description="用户原始问题")
    url: str = Field( description="项目拉取的git地址")
    project_name: str = Field( description="项目名称")
    branch: str = Field(default="dev", description="git的分支")
    code_edit: str = Field(default="claude", description="ai编程工具")
    project_workspace: str = Field(default=None,description="项目工作空间")
    type: Literal[CodeGenerateType.DEFAULT, CodeGenerateType.BUG_FIX] = Field(default=CodeGenerateType.DEFAULT, description="任务类型")
    review:dict[str, Any] = Field( default=None,description="审批结果")
    plan: str = Field(default=None,description="生成的计划")
    result:str = Field(default=None, description="执行结果")
    git_result:Dict=Field(default=None, description="git提交结果")