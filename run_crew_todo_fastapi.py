import os
import traceback
import time
import requests
import subprocess
import shlex
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import Optional, Type, List, Dict, Any, Union

from settings import Settings

# --- Load and Verify Settings ---
try:
    settings = Settings()
except Exception as e:
    print(f"❌ Error loading settings from environment variables: {e}")
    exit()

# --- Create a dictionary of available LLM providers ---
llm_provider_map = {
    "openai": ChatOpenAI(
        model_name=settings.MODEL_OPENAI, temperature=0, api_key=settings.OPENAI_API_KEY
    ),
    "google": ChatGoogleGenerativeAI(
        model=settings.MODEL_GOOGLE, temperature=0, api_key=settings.GOOGLE_API_KEY
    ),
    "anthropic": ChatAnthropic(
        model_name=settings.MODEL_ANTHROPIC,
        temperature=0,
        api_key=settings.ANTHROPIC_API_KEY,
    ),
}


def get_model_name(
    llm_instance: Union[ChatOpenAI, ChatGoogleGenerativeAI, ChatAnthropic],
) -> str:
    """Gracefully gets the model name from a LangChain LLM instance."""
    if hasattr(llm_instance, "model_name"):
        return llm_instance.model_name
    elif hasattr(llm_instance, "model"):
        return llm_instance.model
    else:
        return "N/A"


print("✅ LLM provider roles configured:")
print(
    f"  - Architect: {settings.ROLE_ARCHITECT} (Model: {get_model_name(llm_provider_map[settings.ROLE_ARCHITECT])})"
)
print(
    f"  - Developer: {settings.ROLE_DEVELOPER} (Model: {get_model_name(llm_provider_map[settings.ROLE_DEVELOPER])})"
)
print(
    f"  - Tester:    {settings.ROLE_TESTER} (Model: {get_model_name(llm_provider_map[settings.ROLE_TESTER])})"
)

# --- Project Path Setup ---
PROJECT_NAME = os.path.expanduser(settings.PROJECT_BASE_PATH)


# --- Tool Definitions ---
class FileSystemTool(BaseTool):
    name: str = "FileSystemTool"
    description: str = (
        "A tool to read, write, and list files and directories in the project workspace."
    )
    workspace_dir: str

    def _run(self, operation: str, path: str, content: Optional[str] = None) -> str:
        full_path = os.path.join(self.workspace_dir, path)
        try:
            if operation == "write":
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
            return f"Error during '{operation}' on path '{full_path}': {e}"


class TestCase(BaseModel):
    endpoint: str = Field(...)
    method: str = Field(...)
    expected_status: int = Field(...)
    json_payload: Optional[Dict[str, Any]] = Field(None)
    expected_response: Optional[Dict[str, Any]] = Field(None)


class FunctionalTestToolInput(BaseModel):
    file_path: str = Field(...)
    test_cases: List[TestCase] = Field(...)


class CodeTestTool(BaseTool):
    name: str = "FunctionalAPITestTool"
    description: str = (
        "A powerful tool to perform functional tests on a live FastAPI application."
    )
    args_schema: Type[BaseModel] = FunctionalTestToolInput
    workspace_dir: str

    def _run(self, file_path: str, test_cases: List[TestCase]) -> str:
        full_path = os.path.join(self.workspace_dir, file_path)
        if not os.path.exists(full_path):
            return f"Error: Test file '{full_path}' not found."
        app_name = os.path.splitext(os.path.basename(file_path))[0]
        server_command = f"uvicorn {app_name}:app --host 127.0.0.1 --port 8000"
        server_process = None
        try:
            print(f"\n🚀 Starting FastAPI server: {server_command}")
            server_process = subprocess.Popen(
                shlex.split(server_command),
                cwd=self.workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(5)
            if server_process.poll() is not None:
                stderr_output = server_process.stderr.read().decode()
                return f"Error: Server failed to start. Return code: {server_process.poll()}\nError Log:\n{stderr_output}"
            results = []
            base_url = "http://127.0.0.1:8000"
            for case in test_cases:
                test_result = self._execute_test_case(base_url, case)
                results.append(test_result)
                if "FAIL" in test_result:
                    break
            return "\n".join(results)
        except Exception as e:
            return f"An unexpected error occurred during testing: {e}\n{traceback.format_exc()}"
        finally:
            if server_process:
                print("🛑 Shutting down FastAPI server...")
                server_process.terminate()
                server_process.wait()

    def _execute_test_case(self, base_url: str, case: TestCase) -> str:
        url = base_url + case.endpoint
        try:
            response = requests.request(
                method=case.method, url=url, json=case.json_payload, timeout=10
            )
            status_match = response.status_code == case.expected_status
            body_match = True
            if case.expected_response is not None:
                try:
                    body_match = response.json() == case.expected_response
                except requests.exceptions.JSONDecodeError:
                    body_match = False
            if status_match and body_match:
                return f"✅ PASS: {case.method} {case.endpoint}"
            else:
                return f"❌ FAIL: {case.method} {case.endpoint}\n  - Expected Status: {case.expected_status}, Got: {response.status_code}\n  - Expected Response: {case.expected_response}, Got: {response.text}"
        except requests.RequestException as e:
            return f"❌ FAIL: {case.method} {case.endpoint} - Request Error: {e}"


# --- Initialize Tools ---
file_system_tool = FileSystemTool(workspace_dir=PROJECT_NAME)
code_test_tool = CodeTestTool(workspace_dir=PROJECT_NAME)

# --- Agent Definitions ---
architect_agent = Agent(
    role="Senior Software Architect",
    goal="Plan the entire software development process, from code structure to functional tests, and manage the execution by delegating tasks.",
    backstory="You are a master architect who designs robust, testable applications.",
    verbose=True,
    allow_delegation=True,
    llm=llm_provider_map[settings.ROLE_ARCHITECT],
    tools=[file_system_tool],
    max_rpm=25,
)
developer_agent = Agent(
    role="Senior Python Developer",
    goal="Write clean, efficient, and correct Python code for the FastAPI framework based on the precise instructions from the architect.",
    backstory="You are a skilled Python developer who produces high-quality code.",
    verbose=True,
    allow_delegation=False,
    llm=llm_provider_map[settings.ROLE_DEVELOPER],
    tools=[file_system_tool],
    max_rpm=10,
)
qa_agent = Agent(
    role="Software Quality Assurance Engineer",
    goal="Thoroughly test the FastAPI application using the provided functional test tool and report any bugs or successful test runs.",
    backstory="You are a meticulous QA engineer who executes tests flawlessly.",
    verbose=True,
    allow_delegation=False,
    llm=llm_provider_map[settings.ROLE_TESTER],
    tools=[code_test_tool],
    max_rpm=25,
)

# --- Task Definitions ---
goal = """
Create a complete FastAPI application that functions as an in-memory To-Do list manager.
The application should store the to-do items in a simple list in memory. Each to-do item should be a dictionary with an 'id' and a 'task' description.

It must have the following three endpoints:
1.  **`GET /todos`**: Returns a JSON list of all current to-do items. For example: `[{"id": 1, "task": "Learn CrewAI"}]`. If there are no tasks, it should return an empty list `[]`.
2.  **`POST /todos`**: Accepts a JSON body with a 'task' description. For example: `{"task": "Build an amazing app"}`. It should add this new task to the in-memory list with a unique ID and return the newly created to-do item. For example: `{"id": 2, "task": "Build an amazing app"}`. Use a Pydantic model for the request body.
3.  **`DELETE /todos/{item_id}`**: Accepts an integer `item_id` from the URL path. It should find and remove the corresponding to-do item from the list. It should return a success message, for example: `{"status": "success", "message": "To-Do item with id 2 deleted"}`.
"""
print(f"\nGoal: {goal}\nProject Path: {PROJECT_NAME}\n")
planning_task = Task(
    description=f"Create a step-by-step plan to achieve the following goal: {goal}. The plan MUST include a code implementation plan and functional test cases for ALL FIVE endpoints.",
    expected_output="A detailed, numbered list of the code plan and API test cases.",
    agent=architect_agent,
)
development_and_testing_task = Task(
    description="Follow the plan to manage building and testing the FastAPI application. Orchestrate the developer and QA engineer in a `code -> test -> debug` cycle until all tests pass.",
    expected_output=f"A final report confirming all functional tests passed. The final code should be in the '{PROJECT_NAME}' directory.",
    agent=architect_agent,
    context=[planning_task],
)

# --- Crew Definition and Kickoff ---
project_crew = Crew(
    agents=[architect_agent, developer_agent, qa_agent],
    tasks=[planning_task, development_and_testing_task],
    process=Process.sequential,
    # ### <<< START: FIX FOR THE VALIDATION ERROR >>>
    # The `verbose` parameter now requires a boolean. `True` enables detailed logging.
    verbose=True,
    # ### <<< END: FIX FOR THE VALIDATION ERROR >>>
)

try:
    print(f"🚀 Kicking off the dynamically configured 3-agent crew...")
    result = project_crew.kickoff()
    print("\n\n########################")
    print("## Crew Finished Execution!")
    print("########################\n")
    print("Final result from the crew:")
    print(result)
except Exception as e:
    print(f"\n\nAN UNEXPECTED ERROR OCCURRED: {e}")
    traceback.print_exc()
finally:
    print(
        f"\nExecution finished. Check the '{PROJECT_NAME}' directory for any generated files."
    )
