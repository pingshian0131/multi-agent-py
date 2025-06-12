from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal

# Define the allowed provider names. This ensures type safety.
Provider = Literal["openai", "google", "anthropic"]

class Settings(BaseSettings):
    """
    Manages application settings and secrets by reading from system environment variables.
    Allows for dynamic assignment of AI providers to different agent roles.
    """
    # --- API Keys
    OPENAI_API_KEY: str = Field(..., repr=False)
    GOOGLE_API_KEY: str = Field(..., repr=False)
    ANTHROPIC_API_KEY: str = Field(..., repr=False)

    # ### <<< START: MODULAR CONFIGURATION >>>
    # --- Model Name for each provider ---
    # You can set which specific model each provider should use.
    MODEL_OPENAI: str = "gpt-4o"
    MODEL_GOOGLE: str = "gemini-1.5-pro-latest"
    MODEL_ANTHROPIC: str = "claude-3-5-haiku-20241022"

    # --- Assign a provider to each role ---
    # This is where you control which agent gets which AI.
    ROLE_ARCHITECT: Provider = "anthropic"
    ROLE_DEVELOPER: Provider = "google"
    ROLE_TESTER: Provider = "openai"
    # ### <<< END: MODULAR CONFIGURATION >>>

    # --- Project Configuration
    PROJECT_BASE_PATH: str = "~/project/dynamic_agent_demo"
    
    class Config:
        extra = 'ignore'


