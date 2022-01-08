import logging
from logging import getLogger

from termcolor import colored

from cpk.constants import DEBUG

# create logger
cpklogger = getLogger('cpk')

colors = {
    'critical': 'red',
    'debug': 'magenta',
    'error': 'red',
    'info': None,
    'notice': 'magenta',
    'spam': 'green',
    'success': 'green',
    'verbose': 'blue',
    'warning': 'yellow'
}

# color parts of the left bar
levelname = colored("%(levelname)8s", "grey")
filename_lineno = colored("%(filename)15s:%(lineno)-4s", "blue")

# compile format
format = f"%(name)3s|{filename_lineno} - %(funcName)-15s : %(message)s" \
    if DEBUG else f"%(name)3s|{levelname} : %(message)s"
indent = " " * (43 if DEBUG else 13)


class CustomFilter(logging.Filter):
    def filter(self, record):
        lines = record.msg.split("\n")
        color = colors[record.levelname.lower()]
        lines = map(lambda l: colored(l, color) if color else l, lines)
        record.msg = f"\n{indent}: ".join(lines)
        return super(CustomFilter, self).filter(record)


# handle multi-line messages
cpklogger.addFilter(CustomFilter())

# create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter(format)
ch.setFormatter(formatter)
# add the handlers to logger
cpklogger.addHandler(ch)


def update_logger(level: int):
    # set level
    cpklogger.setLevel(level)
    ch.setLevel(level)


# set INFO as default level
update_logger(logging.INFO)


__all__ = [
    "cpklogger",
    "update_logger"
]
