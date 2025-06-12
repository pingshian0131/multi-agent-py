# AI Software Development Crew 🤖

This project demonstrates how to use a crew of autonomous AI agents, orchestrated by CrewAI, to automatically plan, develop, and test a complete FastAPI web application from a single high-level goal.

The crew consists of specialized agents, each powered by a different large language model (LLM), that collaborate to build and validate the software in a process that mirrors a real-world development team.

## Core Concepts

The system is built around a few key ideas:

**Agentic Workflow**: Instead of a single AI, we use a team of agents with distinct roles, promoting a separation of concerns and more robust outcomes.

**Specialized Roles**:

- **Architect Agent**: The project manager. It takes a high-level goal and creates a detailed technical plan, including the application’s code structure and a full suite of functional test cases.
- **Developer Agent**: The coder. It receives precise coding instructions from the Architect and writes the Python code for the application.
- **QA Engineer Agent**: The tester. It takes the code from the Developer and the test cases from the Architect, spins up a live server, and performs functional API-level tests to validate the application’s behavior.

**Dynamic Configuration**: The entire crew is highly configurable through environment variables and a central settings file, allowing you to easily swap out the AI models or even the roles themselves without changing the core logic.

## 🛠️ Setup and Configuration

Follow these steps to get the AI crew running.

### 1. Install Dependencies

First, create a requirements.txt file with the content provided in this repository. Then, install all dependencies using pip:

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

The crew requires API keys and allows for optional overrides for models and roles via environment variables.

**On Linux or macOS:**

```bash
# --- Required API Keys ---
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AIza..."
export ANTHROPIC_API_KEY="sk-ant-..."

# --- (Optional) Override Model and Role Assignments ---
# Example: Change the specific model used by each provider
export MODEL_OPENAI="gpt-3.5-turbo"
export MODEL_GOOGLE="gemini-1.5-flash"
export MODEL_ANTHROPIC="claude-3-haiku-20240307"

# Example: Re-assign roles to different providers
export ROLE_DEVELOPER="openai"
export ROLE_TESTER="google"
```

**On Windows (Command Prompt):**

```cmd
rem --- Required API Keys ---
set OPENAI_API_KEY="sk-..."
set GOOGLE_API_KEY="AIza..."
set ANTHROPIC_API_KEY="sk-ant-..."

rem --- (Optional) Override Model and Role Assignments ---
rem Example: Change the specific model used by each provider
set MODEL_OPENAI="gpt-3.5-turbo"
set MODEL_GOOGLE="gemini-1.5-flash"
set MODEL_ANTHROPIC="claude-3-haiku-20240307"

rem Example: Re-assign roles to different providers
set ROLE_DEVELOPER="openai"
set ROLE_TESTER="google"
```

### 3. Configure settings.py

This project uses a `settings.py` file to manage all configurations, such as which AI model is assigned to each role. You can examine the `settings.py` file in this repository to see the available options and their default values. Environment variables, when set, will always take precedence over the values in this file.

## 🚀 Scripts

This repository contains two primary script examples that showcase the evolution of the AI crew.

### 1. run_crew.py (Initial 2-Agent Version)

This was the first iteration of the project, demonstrating a basic two-agent collaboration.

- **Architect Agent (Claude)**: Plans the application and defines tasks.
- **Developer Agent (Gemini)**: Executes the coding tasks.
- **Process**: The Architect creates a plan, and the Developer writes the code. The testing in this version was limited to a simple syntax check to ensure the Python code could compile. This script served as the foundation for the more advanced 3-agent version.

### 2. run_crew_3_agents.py (Final Advanced Version)

This is the complete and recommended version of the project, featuring a full, three-agent team with advanced testing and configuration capabilities.

- **Architect Agent (Claude by default)**: Plans the code and a full suite of API-level functional tests.
- **Developer Agent (Gemini by default)**: Writes the application code based on the Architect’s plan.
- **QA Engineer Agent (OpenAI by default)**: Receives the code and test cases, starts a live uvicorn server, and performs real HTTP requests to validate every endpoint.
- **Dynamic Configuration**: This script uses the `settings.py` file and environment variables to let you dynamically assign any of the three AI providers to any of the three roles. You can also change the specific model used by each provider and the api_key they use.

## How to Run

1. Complete the setup steps (install dependencies from requirements.txt, set environment variables).
1. (Optional) Modify `settings.py` or set environment variables to change the default agent assignments or models.
1. Execute the main script from your terminal:
   
   ```bash
   python main.py
   ```
1. Watch as the agents collaborate in your terminal to plan, code, test, and debug the FastAPI application until it’s fully functional. The final, working code will be located in the directory specified by `PROJECT_BASE_PATH` in your settings (e.g., `~/project/crewai_fastapi_demo`).