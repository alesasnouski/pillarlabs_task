from fastapi import Form
from pydantic import BaseModel, model_validator


class GeneratePlanRequest(BaseModel):
    url: str
    prompt: str


class ActionCreate(BaseModel):
    action_type: str
    click_axis_x: int | None = None
    click_axis_y: int | None = None
    input_text: str | None = None
    description: str
    final_result: str = ""

    # Using classmethod to map FastAPI Form easily without dependency overrides
    @classmethod
    def as_form(
        cls,
        action_type: str = Form(...),
        description: str = Form(...),
        click_axis_x: int | None = Form(None),
        click_axis_y: int | None = Form(None),
        input_text: str | None = Form(None),
        final_result: str = Form(""),
    ) -> "ActionCreate":
        return cls(
            action_type=action_type,
            description=description,
            click_axis_x=click_axis_x,
            click_axis_y=click_axis_y,
            input_text=input_text,
            final_result=final_result,
        )

    @model_validator(mode="after")
    def validate_action(self) -> "ActionCreate":
        from app.services.browser import VIEWPORT

        if self.action_type == "click":
            if self.click_axis_x is None or self.click_axis_y is None:
                raise ValueError("Missing click coordinates")
            if not (0 <= self.click_axis_x <= VIEWPORT["width"]):
                raise ValueError(f"X coordinate {self.click_axis_x} is out of bounds (0 - {VIEWPORT['width']})")
            if not (0 <= self.click_axis_y <= VIEWPORT["height"]):
                raise ValueError(f"Y coordinate {self.click_axis_y} is out of bounds (0 - {VIEWPORT['height']})")

        elif self.action_type == "type":
            if not self.input_text:
                raise ValueError("Missing input text")

        return self
