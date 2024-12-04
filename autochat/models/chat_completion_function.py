from typing import Any
from pydantic import BaseModel, Field

__all__ = [
    "ChatCompletionFunctionCall",
    "ChatCompletionFunctionParametersProperty",
    "ChatCompletionFunctionParameters",
    "ChatCompletionFunction",
]


class ChatCompletionFunctionCall(BaseModel):
    id: str = Field(
        ...,
        description="The id of the function call.",
        examples=["call_abc123"],
    )
    arguments: dict[str, Any] = Field(
        ...,
        description="The arguments of the function call.",
        examples=[{"a": 1, "b": 2}],
    )
    name: str = Field(
        ...,
        description="The name of the function.",
        examples=["plus_a_and_b"],
    )


class ChatCompletionFunctionParametersProperty(BaseModel):
    type: str = Field(
        ...,
        pattern="^(string|number|integer|boolean)$",
        description="The type of the parameter.",
    )

    description: str = Field(
        "",
        max_length=256,
        description="The description of the parameter.",
    )


class ChatCompletionFunctionParameters(BaseModel):
    type: str = Field(
        "object",
        Literal="object",
        description="The type of the parameters, which is always 'object'.",
    )

    properties: dict[str, ChatCompletionFunctionParametersProperty] = Field(
        ...,
        description="The properties of the parameters.",
    )

    required: list[str] = Field(
        [],
        description="The required parameters.",
    )



class ChatCompletionFunction(BaseModel):
    name: str = Field(
        ...,
        description="The name of the function.",
        examples=["plus_a_and_b"],
    )

    description: str = Field(
        ...,
        description="The description of the function.",
        examples=["Add two numbers"],
    )

    parameters: ChatCompletionFunctionParameters = Field(
        ...,
        description="The function's parameters are represented as an object in JSON Schema format.",
        examples=[
            {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"},
                },
                "required": ["a", "b"],
            }
        ],
    )
