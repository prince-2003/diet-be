from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    id: str
    dict_of_vars: Dict[str, str]
    prompt: str
    testResults: Optional[Dict[str, Any]] = None