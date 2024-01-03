import argparse


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
