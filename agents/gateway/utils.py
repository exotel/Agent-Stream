from pydantic import BaseModel
from typing import Optional

class OutgoingCall(BaseModel):
    mobile: str
    run_id: str
    name: Optional[str] = None
