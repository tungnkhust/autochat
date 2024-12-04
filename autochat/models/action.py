from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel


from autochat.models.chat_completion_function import ChatCompletionFunction


__all__ = [
    "EXAMPLE_OPENAPI_SCHEMA",
    "ActionMethod",
    "ActionBodyType",
    "ActionParam",
    "ActionStruct"
]


EXAMPLE_OPENAPI_SCHEMA = {
    "openapi": "3.1.0",
    "servers": [{"url": "https://www.example.com"}],
    "info": {"title": "My Action", "description": "This is an action."},
    "paths": {
        "/": {
            "get": {
                "operationId": "get_data",
                "description": "The action to get data.",
                "responses": {"200": {"description": "OK"}},
            }
        }
    },
}


class ActionMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    NONE = "NONE"


class ActionBodyType(str, Enum):
    JSON = "JSON"
    FORM = "FORM"
    NONE = "NONE"


class ActionParam(BaseModel):
    type: str
    description: str
    enum: Optional[List[str]] = None
    required: bool


class ActionStruct(BaseModel):
    name: str
    description: str
    url: str
    method: ActionMethod
    path_param_schema: Optional[Dict[str, ActionParam]]
    query_param_schema: Optional[Dict[str, ActionParam]]
    body_param_schema: Optional[Dict[str, ActionParam]]
    body_type: ActionBodyType
    function_def: ChatCompletionFunction
    openapi_schema: Dict
