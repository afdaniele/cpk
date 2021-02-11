import logging
import platform
import sys
from functools import partial
from logging import Logger, StreamHandler, Formatter, getLogger

from cpk.constants import DEBUG


# create logger
logging.basicConfig()
cpklogger = getLogger('cpk')
cpklogger.setLevel(logging.INFO)


def setup_logging_format(fmt: str):
    logging.basicConfig(format=fmt)
    # noinspection PyUnresolvedReferences
    root = Logger.root
    if root.handlers:
        for handler in root.handlers:
            if isinstance(handler, StreamHandler):
                formatter = Formatter(fmt)
                handler.setFormatter(formatter)
    else:
        logging.basicConfig(format=fmt)


def add_coloring_to_emit_ansi(fn, indent: int = 0):

    # add methods we need to the class
    def new(*args):
        levelno = args[1].levelno
        if levelno >= 50:
            color = "\x1b[31m"  # red
        elif levelno >= 40:
            color = "\x1b[31m"  # red
        elif levelno >= 30:
            color = "\x1b[33m"  # yellow
        elif levelno >= 20:
            color = "\x1b[32m"  # green
        elif levelno >= 10:
            color = "\x1b[35m"  # pink
        else:
            color = "\x1b[0m"  # normal
        msg = str(args[1].msg)
        lines = msg.split("\n")

        def color_line(enum_line):
            i, line = enum_line
            tab = " " * (indent - 2) + ": " if i > 0 else ""
            return "%s%s%s%s" % (tab, color, line, "\x1b[0m")

        lines = list(map(color_line, enumerate(lines)))
        args[1].msg = "\n".join(lines)
        return fn(*args)
    # ---
    return new


format_indent = 15
setup_logging_format("%(name)3s|%(levelname)8s : %(message)s")
if DEBUG:
    format_indent = 44
    setup_logging_format("%(name)3s|%(filename)15s:%(lineno)-4s - %(funcName)-15s| %(message)s")

if platform.system() != "Windows":
    emit2 = add_coloring_to_emit_ansi(StreamHandler.emit, format_indent)
    StreamHandler.emit = emit2


def plain(text: str = "", end: str = ""):
    if end == "" and text.rstrip(" ").endswith("\n"):
        text = text.rstrip("\n")
        end = "\n"
    text = "\n".join([
        (" " * 3 + "| " + line)
        for line in text.split('\n')
    ]) + end
    sys.stdout.write(text)
    sys.stdout.flush()


setattr(cpklogger, "print", partial(plain, end="\n"))
setattr(cpklogger, "write", plain)

__all__ = [
    "cpklogger"
]
