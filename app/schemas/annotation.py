from pydantic import BaseModel


class GeneratePlanRequest(BaseModel):
    url: str
    prompt: str
