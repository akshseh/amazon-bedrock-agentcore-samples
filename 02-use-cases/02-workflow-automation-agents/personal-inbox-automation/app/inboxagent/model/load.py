"""Cost-efficient model routing based on email priority."""
from strands.models.bedrock import BedrockModel
from config import AGENT_MODEL_ID, FAST_MODEL_ID


def load_model(priority: str = "MEDIUM") -> BedrockModel:
    """LOW → Haiku (junk detection), MEDIUM+ → Sonnet (full reasoning)."""
    model_id = FAST_MODEL_ID if priority == "LOW" else AGENT_MODEL_ID
    return BedrockModel(model_id=model_id)
