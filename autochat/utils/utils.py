from typing import Any
import json
import string
import random
import pytz
import datetime
import importlib
import re
from autochat.utils.string_utils import parser_string_to_json, jaccard_similarity, extract_json_from_markdown


def get_time_vn_now(strftime: str = "iso") -> Any:
    utc_time = datetime.datetime.now(pytz.utc)
    vietnam_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    vietnam_time = utc_time.astimezone(vietnam_tz)
    if strftime == "iso":
        return vietnam_time.isoformat()
    elif strftime:
        return vietnam_time.strftime(strftime)

    return vietnam_time


def generate_random_id(length):
    first_letter = string.ascii_uppercase + string.ascii_lowercase
    letters = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return random.choice(first_letter) + "".join(random.choice(letters) for _ in range(length - 1))


def get_handoff_tool_name(agent_name: str):
    return f"handoff_to_{agent_name}"


def load_json_attr(row: dict, key: str, default_value: Any = None):
    data = row.get(key)
    if data:
        if isinstance(data, str):
            return json.loads(data)
        elif isinstance(data, dict) or isinstance(data, list):
            return data
        else:
            return default_value
    else:
        return default_value


def get_function(module_name, function_name):
    try:
        # Import the module dynamically
        module = importlib.import_module(module_name)

        # Retrieve the function by name
        func = getattr(module, function_name)

        # Ensure the retrieved attribute is callable
        if callable(func):
            return func
        else:
            raise TypeError(f"{function_name} is not a callable function in {module_name}")
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not find function '{function_name}' in module '{module_name}': {e}")



def get_message_content(message: dict[str, Any], ignore_clear_msg: bool = False) -> str:
    if ignore_clear_msg:
        return "\n".join(item["text"] for item in message["content"] if item["type"] == "text")
    return "\n".join(item["text"] for item in message["content"] if item["type"] == "text")


def sub_quotes_mark(match: re.Match[Any]) -> str:
    text = match.group().strip('"').replace('"', '\\"')
    return f'"{text}"'


def merge_response(text_1: str, text_2: str) -> str:
    score = jaccard_similarity(text_1.lower(), text_2.lower())
    if score >= 0.65:
        if len(text_1) > len(text_2):
            merge_text = text_1
        else:
            merge_text = text_2
    else:
        merge_text = f"{text_1}\n{text_2}"
    return merge_text


def parser_assistant_message(text: str) -> dict[str, Any]:
    """
    Combine multiple responses into one response
    Args:
        text: the original assistant response message with multiple responses in json format
        {
            "content": ...,
            "is_exit": True/False
        }

        {
            "content": ...,
            "is_exit": True/False
        }

    Returns:
        Following the format:
        {
            "content": ...,
            "is_exit": True/False
        }
    """
    text = text.replace("“", '"').replace("”", '"')

    pattern = re.compile(r"(```json(.*?)```)|(\{.*?})", re.DOTALL)

    # find all the json/dict objects in the text with response schema
    matches = list(re.finditer(pattern, text))
    if not matches:
        return {"response": text}

    response_dicts = []

    for match in matches:
        value = match.group()

        if "json" in value:
            value = extract_json_from_markdown(value)

        value = re.sub('"".*?""', sub_quotes_mark, value)
        value = value.replace("false", "False")
        value = value.replace("true", "True")

        value_dict = parser_string_to_json(value)

        if value_dict:
            text = text.replace(match.group(), "").strip(' \n\t"')
            response_dicts.append(value_dict)

    text = re.sub(" {2,}", " ", text)
    text = re.sub("\n{3,}", "\n\n", text)
    output: dict[str, Any] = {"response": text}

    for res_dict in response_dicts:
        for k, v in res_dict.items():
            if k in output:
                if k == "response" or k == "message":
                    output[k] = merge_response(output[k], v)
                elif isinstance(v, str):
                    output[k] += "\n" + v
                elif isinstance(v, bool):
                    output[k] = output[k] | v
                else:
                    output[k] = v
            else:
                output[k] = v
    return output



def build_system_prompt(
    system_prompt_template: list[str],
    system_prompt_variables: dict,
) -> str:
    # Initialize an empty list to collect the finalized prompt segments.
    final_prompt_list = []

    # Replace all the variable placeholders in the template with their values.
    for prompt in system_prompt_template:
        var_names = re.findall(r"{{(.*?)}}", prompt)
        for var in var_names:
            if var in system_prompt_variables and system_prompt_variables[var] is not None:
                prompt = prompt.replace("{{" + var + "}}", str(system_prompt_variables[var]))
            else:
                break
        else:
            final_prompt_list.append(prompt)

    final_prompt = "\n\n".join(final_prompt_list)

    return final_prompt
