import copy
import time
from collections.abc import Callable
from typing import Any


from autochat.models.messages import HandoffMessage, UserMessage


def color_red(text: str) -> str:
    return f"\033[91m{text}\033[00m"


def color_green(text: str) -> str:
    return f"\033[92m{text}\033[00m"


def color_yellow(text: str) -> str:
    return f"\033[93m{text}\033[00m"


def color_light_purple(text: str) -> str:
    return f"\033[94m{text}\033[00m"


def color_purple(text: str) -> str:
    return f"\033[95m{text}\033[00m"


def color_cyan(text: str) -> str:
    return f"\033[96m{text}\033[00m"


def color_light_gray(text: str) -> str:
    return f"\033[97m{text}\033[00m"


def color_black(text: str) -> str:
    return f"\033[98m{text}\033[00m"


def print_warn(text: str, sleep: float = 0, print_fun: Callable[[str], None] = print) -> None:
    """Warns the user using stdout."""
    print_fun(f"\033[91m\n[WARN] {text}\n \033[00m")
    if sleep > 0:
        time.sleep(sleep)


def print_red(text: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun(f"\033[91m{text}\033[00m")


def print_green(text: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun(f"\033[92m{text}\033[00m")


def print_yellow(text: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun(f"\033[93m{text}\033[00m")


def print_light_purple(text: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun(f"\033[94m{text}\033[00m")


def print_purple(text: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun(f"\033[95m{text}\033[00m")


def print_cyan(text: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun(f"\033[96m{text}\033[00m")


def print_light_gray(text: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun(f"\033[97m{text}\033[00m")


def print_black(text: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun(f"\033[98m{text}\033[00m")


def print_dict(title: str = "", startswith: str = "", print_fun: Callable[[str], None] = print, **kwargs: Any) -> None:
    if title:
        print_fun(title)
    for key, value in kwargs.items():
        print_fun(f"{startswith}{key}: {value}")


def print_style_free(message: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun("")
    print_fun(f"░▒▓█  {message}")


def print_style_time(message: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun("")
    print_fun(f"⏰  {message}")
    print_fun("")


def print_style_warning(message: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun("")
    print_fun(f"⛔️  {message}")
    print_fun("")


def print_style_notice(message: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun("")
    print_fun(f"📌  {message}")
    print_fun("")


def print_line(text: str, print_fun: Callable[[str], None] = print) -> None:
    print_fun("")
    print_fun(f"➖➖➖➖➖➖➖➖➖➖ {text.upper()} ➖➖➖➖➖➖➖➖➖➖")
    print_fun("")


def print_boxed(text: str, print_fun: Callable[[str], None] = print) -> None:
    box_width = len(text) + 2
    print_fun("")
    print_fun("╒{}╕".format("═" * box_width))
    print_fun(f"  {text.upper()}  ")
    print_fun("╘{}╛".format("═" * box_width))
    print_fun("")


def print_logs(
        source,
        message,
        print_fun: Callable[[str], None] = print,
        trace_messages: list[Any] = None,
        color_source: Callable[[str], str] = color_green,
        debug: bool = True
):
    message = copy.deepcopy(message)

    if not debug:
        return

    if isinstance(message, str):
        mes = message
    elif isinstance(message, UserMessage):
        mes = message.content[-1]
        message.traces = []
    elif isinstance(message, HandoffMessage):
        mes = message.message.content[-1]
        message.traces = []
        message.message.traces = []
    else:
        mes = message.content
        message.traces = []

    if isinstance(mes, list):
        mes = mes[-1]

    _source = color_source(source)
    print_fun(f"Agent {_source}:")
    print_fun(f"        {mes}")

    trace_messages.append({source: message})


