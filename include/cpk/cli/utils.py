import argparse
import json
import traceback
from typing import Any

from functools import partial
from typing import Callable


def remove_argument(parser: argparse.ArgumentParser, arg: str, suppress_errors: bool = True):
    try:
        for action in parser._actions:
            opts = action.option_strings
            if (opts and opts[0] == arg) or action.dest == arg:
                parser._remove_action(action)
                break

        for action in parser._action_groups:
            for group_action in action._group_actions:
                opts = group_action.option_strings
                if (opts and opts[0] == arg) or group_action.dest == arg:
                    action._group_actions.remove(group_action)
                    return
    except Exception as e:
        if not suppress_errors:
            raise e


def hide_argument(parser: argparse.ArgumentParser, arg: str, suppress_errors: bool = True):
    try:
        for action in parser._actions:
            opts = action.option_strings
            if (opts and opts[0] == arg) or action.dest == arg:
                action.help = argparse.SUPPRESS
                break

        for action in parser._action_groups:
            for group_action in action._group_actions:
                opts = group_action.option_strings
                if (opts and opts[0] == arg) or group_action.dest == arg:
                    action.help = argparse.SUPPRESS
                    return
    except Exception as e:
        if not suppress_errors:
            raise e


def combine_args(parsed: argparse.Namespace, kwargs: dict) -> argparse.Namespace:
    # combine arguments
    for k, v in kwargs.items():
        parsed.__setattr__(k, v)
    # ---
    return parsed


def indent_block(s: str, indent_len: int = 4) -> str:
    space: str = " " * indent_len
    return space + f"\n{space}".join(s.splitlines() if s is not None else ["None"])


def pretty_json(data: Any, indent_len: int = 0) -> str:
    return indent_block(json.dumps(data, sort_keys=True, indent=4), indent_len=indent_len)


def pretty_exc(exc: Exception, indent_len: int = 0) -> str:
    return indent_block(
        ''.join(traceback.TracebackException.from_exception(exc).format()), indent_len=indent_len)


def as_table(data: dict, title: str, indent_len: int = 2) -> str:
    space: str = " " * indent_len
    w = "\033[37m"
    x = "\033[0m"
    width: int = 36
    half_header: int = (width - len(title) - 2) // 2
    # table template
    table: str = f"""
{'-' * half_header} {title} {'-' * (width - half_header - len(title) - 2)}
{{content}}
{'-' * width}
    """
    row: str = "{s}{w}{key}:{x} {value}"
    # produce content
    content: str = ""
    for k, v in data.items():
        content += row.format(s=space, w=w, x=x, key=k, value=v) + "\n"
    content = content.strip("\n")
    # ---
    return table.format(content=content)


# coloring functions
color: Callable[[str], str] = lambda c, x: f"\033[{c}m{x}\033[0m"
green: Callable[[str], str] = partial(color, "32")
red: Callable[[str], str] = partial(color, "31")
white: Callable[[str], str] = partial(color, "37")
blue: Callable[[str], str] = partial(color, "34")
orange: Callable[[str], str] = partial(color, "33")
