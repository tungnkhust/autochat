import logging
from typing import Any, Type, cast, Optional
from pydantic import BaseModel, Field, create_model

from autogen_core.components.tools import BaseTool
from autogen_core.base import CancellationToken
from autogen_core.components.tools import ToolSchema, ParametersSchema

from autochat.models.action import ActionMethod, ActionParam, ActionBodyType
from autochat.models.authentication import ActionAuthentication
from autochat.models.chat_completion_function import ChatCompletionFunction
from .openapi_call import call_action_api
from .openapi_utils import build_action_struct, split_openapi_schema, replace_openapi_refs

_logger = logging.getLogger(__name__)


def normalize_type_string(type_s: str):
    "string|number|integer|boolean"
    if type_s == "string":
        return str
    elif type_s == "number":
        return float
    elif type_s == "integer":
        return int
    elif type_s == "boolean":
        return bool

    return str

def args_base_model_from_func_def(func_def: ChatCompletionFunction) -> Type[BaseModel]:
    fields: dict[str, tuple[Type[Any], Any]] = {}
    for name, param in func_def.parameters.properties.items():
        # This is handled externally
        if name == "cancellation_token":
            continue
        type = normalize_type_string(param.type)
        description = param.description
        if name not in func_def.parameters.required:
            type = Optional[type]
            fields[name] = (type, Field(description=description, default=None))
        else:
            fields[name] = (type, Field(description=description))

    return cast(BaseModel, create_model(func_def.name + "_args", **fields))  # type: ignore


class Action(BaseTool[BaseModel, BaseModel]):
    def __init__(
            self,
            name: str,
            description: str,
            url: str,
            method: ActionMethod,
            path_param_schema: dict[str, ActionParam],
            query_param_schema: dict[str, ActionParam],
            body_type: ActionBodyType,
            body_param_schema: dict[str, ActionParam],
            headers: dict[str, Any],
            authentication: ActionAuthentication,
            function_def: ChatCompletionFunction,
            **kwargs
    ):
        self.url = url
        self.method = method
        self.path_param_schema = path_param_schema
        self.query_param_schema = query_param_schema
        self.body_type = body_type
        self.body_param_schema = body_param_schema
        self.headers = headers
        self.authentication = authentication
        self.function_def = function_def

        args_model = args_base_model_from_func_def(function_def)

        super().__init__(
            name=name,
            description=description,
            args_type=args_model,
            return_type=None
        )

    @property
    def schema(self) -> ToolSchema:
        properties = {}
        for name, property in self.function_def.parameters.properties.items():
            properties[name] = property.model_dump()

        tool_schema = ToolSchema(
            name=self._name,
            description=self._description,
            parameters=ParametersSchema(
                type="object",
                properties=properties,
            ),
        )
        tool_schema["parameters"]["required"] = self.function_def.parameters.required

        return tool_schema

    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> Any:
        output = await call_action_api(
            url=self.url,
            method=self.method,
            path_param_schema=self.path_param_schema,
            query_param_schema=self.query_param_schema,
            body_type=self.body_type,
            body_param_schema=self.body_param_schema,
            parameters=args.model_dump(),
            headers=self.headers,
            authentication=self.authentication
        )
        data = output.get("data", output)
        data = data.get("data", data)

        return data

    @classmethod
    def create(cls, openapi_schema: dict[str, Any], authentication: ActionAuthentication):
        openapi_schema = replace_openapi_refs(openapi_schema)
        schemas = split_openapi_schema(openapi_schema)

        if not schemas:
            raise Exception("Failed to parse OpenAPI schema")

        if len(schemas) > 1:
            _logger.warning("Have more than one path then parse first path schema")

        schema = schemas[0]


        action_struct = build_action_struct(schema)

        path_param_dict = None
        if action_struct.path_param_schema:
            path_param_dict = {k: v.model_dump() for k, v in action_struct.path_param_schema.items()}

        query_param_dict = None
        if action_struct.query_param_schema:
            query_param_dict = {k: v.model_dump() for k, v in action_struct.query_param_schema.items()}

        body_param_dict = None
        if action_struct.body_param_schema:
            body_param_dict = {k: v.model_dump() for k, v in action_struct.body_param_schema.items()}

        create_dict = {
            "openapi_schema": action_struct.openapi_schema,
            "authentication": authentication,
            "name": action_struct.name,
            "description": action_struct.description,
            "url": action_struct.url,
            "method": action_struct.method,
            "path_param_schema": path_param_dict,
            "query_param_schema": query_param_dict,
            "body_type": action_struct.body_type,
            "body_param_schema": body_param_dict,
            "function_def": action_struct.function_def,
            "headers": {}
        }

        return cls(**create_dict)

