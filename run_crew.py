import os
import traceback
import time
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field
from typing import Optional, Type

# --- SET YOUR PROJECT PATH HERE ---
raw_project_path = "~/project/project_name"
PROJECT_NAME = os.path.expanduser(raw_project_path)

# --- API KEY CHECK ---
if not os.environ.get("GOOGLE_API_KEY") or not os.environ.get("ANTHROPIC_API_KEY"):
    raise ValueError(
        "API keys for Google and Anthropic must be set as environment variables."
    )

# --- LLM Configuration ---
claude_llm = ChatAnthropic(model_name="claude-3-5-haiku-20241022", temperature=0)
gemini_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)


# --- Tool Schema and Definitions ---
class FileSystemToolInput(BaseModel):
    operation: str = Field(
        description="The operation to perform. Must be one of 'write', 'read', 'list'."
    )
    path: str = Field(
        description="The relative path to the file or directory in the workspace."
    )
    content: Optional[str] = Field(
        default=None,
        description="The content to write to the file. Required only for the 'write' operation.",
    )


class FileSystemTool(BaseTool):
    name: str = "FileSystemTool"
    description: str = """
    A powerful tool to manage files within the project workspace.
    **Valid operations are 'write', 'read', and 'list'.**
    When using the 'write' operation, this tool will automatically create any necessary parent directories for the given file path.
    """
    args_schema: Type[BaseModel] = FileSystemToolInput
    workspace_dir: str

    # ★★★ THE FIX IS HERE ★★★
    # The method name must be `_run` with a single underscore.
    def _run(self, operation: str, path: str, content: Optional[str] = None) -> str:
        full_path = os.path.join(self.workspace_dir, path)
        try:
            if operation == "write":
                if content is None:
                    return (
                        "Error: The 'write' operation requires the 'content' argument."
                    )
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)
                return f"Successfully wrote {len(content)} characters to {full_path}"
            elif operation == "read":
                with open(full_path, "r") as f:
                    return f.read()
            elif operation == "list":
                if not os.path.exists(full_path):
                    return f"Directory '{full_path}' does not exist."
                return "\n".join(os.listdir(full_path))
            else:
                return f"Error: Invalid operation '{operation}'. Valid operations are 'write', 'read', 'list'."
        except Exception as e:
            return f"Error during '{operation}' on path '{full_path}': {e}\nTraceback:\n{traceback.format_exc()}"


class CodeTestTool(BaseTool):
    name: str = "CodeTestTool"
    description: str = (
        "A tool to test generated Python code by executing the file for syntax errors."
    )
    workspace_dir: str

    # ★★★ THE FIX IS HERE ★★★
    # The method name must be `_run` with a single underscore.
    def _run(self, file_path: str) -> str:
        full_path = os.path.join(self.workspace_dir, file_path)
        if not os.path.exists(full_path):
            return f"Error: File '{full_path}' not found for testing."
        try:
            command = f"python -m py_compile {full_path}"
            result = os.system(command)
            if result == 0:
                return "Python syntax check passed!"
            else:
                error_output = os.popen(command).read()
                return f"Python syntax check failed!\n{error_output}"
        except Exception as e:
            return f"Error running test for {full_path}: {e}\nTraceback:\n{traceback.format_exc()}"


# --- Initialize Tools ---
file_system_tool = FileSystemTool(workspace_dir=PROJECT_NAME)
code_test_tool = CodeTestTool(workspace_dir=PROJECT_NAME)

# --- Agent Definitions with Rate Limiting ---
thinking_agent = Agent(
    role="Senior Software Architect",
    goal="Break down the user's goal into a series of small, executable steps. Manage the development process by delegating coding tasks and testing the results.",
    backstory="You are an experienced software architect who excels at planning and leading complex software projects. You create clear, concise, and actionable development plans.",
    verbose=True,
    allow_delegation=True,
    llm=claude_llm,
    tools=[file_system_tool, code_test_tool],
    max_rpm=25,
)

executing_agent = Agent(
    role="Senior Python Developer",
    goal="Write clean, efficient, and correct Python code for the FastAPI framework based on the precise instructions from the architect.",
    backstory="You are a skilled Python developer with deep expertise in the FastAPI framework. You write code that is not only functional but also well-structured and maintainable.",
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm,
    tools=[file_system_tool],
    max_rpm=25,
)

# --- Task Definitions ---
goal = "Create a FastAPI application that has two endpoints: 1. A root endpoint ('/') that returns a JSON message: {'status': 'ok'}. 2. A '/items/{item_id}' endpoint that accepts an integer item_id and returns a JSON object with the received ID, like: {'item_id': 123}."
print(f"\nGoal: {goal}\nProject Path: {PROJECT_NAME}\n")


planning_task = Task(
    description=f"Create a step-by-step plan to achieve the following goal: {goal}. The plan must involve creating a `main.py` file. All file operations must be relative to the root of the project folder.",
    expected_output="A detailed, numbered list of actionable steps for the developer to follow.",
    agent=thinking_agent,
)

development_task = Task(
    description="""
    Follow the plan you've created to build the FastAPI application.
    For each step in your plan:
    1. Delegate the coding task to the Python Developer. Be very specific in your instructions for each file.
    2. Once the code is written, use the CodeTestTool to check if the `main.py` file has valid Python syntax.
    3. If there are errors, analyze the output and delegate a new task to the developer to fix the bug.
    4. Continue this process until all planned steps are complete and the application is syntactically correct.
    """,
    expected_output=f"The complete and tested FastAPI project source code located in the '{PROJECT_NAME}' directory that fulfills the goal: '{goal}'.",
    agent=thinking_agent,
    context=[planning_task],
)

# --- Crew Definition and Kickoff ---
project_crew = Crew(
    agents=[thinking_agent, executing_agent],
    tasks=[planning_task, development_task],
    process=Process.sequential,
    verbose=True,
)

# --- GLOBAL ERROR HANDLER ---
try:
    print(
        f"🚀 Kicking off the crew...\n   Project will be created at: {os.path.abspath(PROJECT_NAME)}"
    )
    result = project_crew.kickoff()
    print("\n\n########################")
    print("## Crew Finished Execution!")
    print("########################\n")
    print("Final result from the crew:")
    print(result)
except Exception as e:
    print("\n\n!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!! AN UNEXPECTED ERROR OCCURRED !!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!\n")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Details: {e}")
    print("\n--- Full Traceback ---")
    traceback.print_exc()
finally:
    print(
        f"\nExecution finished. Check the '{PROJECT_NAME}' directory for any generated files."
    )
