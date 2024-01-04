#!/usr/bin/env python3
import dataclasses
import re
from typing import Optional, Dict, List, Tuple

import termcolor as tc

__version__ = "1.1.0"

from dockertown import Image
from dockertown.components.image.models import ImageHistoryLayer

LAYER_SIZE_YELLOW = 20 * 1024**2  # 20 MB
LAYER_SIZE_RED = 75 * 1024**2  # 75 MB
SEPARATORS_LENGTH = 84
SEPARATORS_LENGTH_HALF = 25

EXTRA_INFO_SEPARATOR = "-" * SEPARATORS_LENGTH_HALF


@dataclasses.dataclass
class BuildLayer:
    type: str
    command: str
    size: float
    id: Optional[str] = None
    index: Optional[int] = None


@dataclasses.dataclass
class BuildStep:
    type: str
    command: str
    cached: bool = False
    layer: Optional[BuildLayer] = None


class ImageAnalyzer:

    @staticmethod
    def size_fmt(num, suffix="B", precision=2):
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            if abs(num) < 1024.0:
                # noinspection PyStringFormat
                return f"%3.{precision}f %s%s" % (num, unit, suffix)
            num /= 1024.0
        # noinspection PyStringFormat
        return f"%.{precision}f%s%s".format(num, "Yi", suffix)

    @staticmethod
    def process(history: List[ImageHistoryLayer], build_log: List[str], codens: int = 0,
                extra_info: str = None, nocolor: bool = False):
        size_fmt = ImageAnalyzer.size_fmt

        history_log: List[Tuple[str, float, str]] = [
            (layer.id, layer.size, layer.created_by) for layer in history]

        # return if the log is empty
        if not build_log:
            raise ValueError("The build log is empty")

        # return if the image history is empty
        if not history_log:
            raise ValueError("The image history is empty")

        if nocolor:
            tc.colored = lambda s, *_: s

        # define RegEx patterns
        step_pattern = re.compile(r"^#[0-9]+ \[\s*([0-9]+)/([0-9]+)] (.*)$")
        naming_pattern = re.compile(r"^#[0-9]+ naming to (.*) (.+) done$")
        done_pattern = re.compile(r"^#[0-9]+ DONE .*$")
        cached_pattern = re.compile(r"^#[0-9]+ CACHED$")

        # sanitize log
        lines = list(map(lambda s: s.strip("\n"), build_log))

        # check if the build process succeded
        if not done_pattern.match(lines[-1]):
            exit(codens + 2)

        # find image tags
        image_names = []
        for line in reversed(lines):
            match = naming_pattern.match(line)
            if match:
                image_name = match.group(1)
                image_names.append(image_name)

        # find "Step XY/TOT" lines
        steptot = -1
        steps_idx = [i for i in range(len(lines)) if step_pattern.match(lines[i])]

        # add end of lines to complete the ranges
        steps_ranges = steps_idx + [len(lines)]

        # sanitize history log
        history_log = [
            (lid[7:19] if lid.startswith("sha256:") else lid, size, _) for (lid, size, _) in history_log
        ]

        # create map {step_id: Layer}
        buildsteps: Dict[int, BuildStep] = {}
        last_FROM = -1
        for i, j in zip(steps_ranges, steps_ranges[1:]):
            stepline = lines[i]
            steplines = lines[i:j]
            # get step info
            stepno = int(step_pattern.match(stepline).group(1))
            steptot = int(step_pattern.match(stepline).group(2))
            stepcmd = re.sub(r"\s+", " ", step_pattern.match(stepline).group(3))
            steptype, stepcmd = stepcmd.split(" ", maxsplit=1)
            # cached?
            stepcached = len(list(filter(cached_pattern.match, steplines))) == 1
            # find FROM layers
            if steptype == "FROM":
                last_FROM = stepno
            # add layer object
            buildsteps[stepno] = BuildStep(
                type=steptype,
                command=stepcmd,
                cached=stepcached,
            )

        # map steps to layers
        j = len(history_log) - 1
        base_image_size = 0
        final_image_size = 0

        for stepno in sorted(buildsteps.keys()):
            buildstep = buildsteps[stepno]
            while j >= 0:
                layerid, layersize, layercmd = history_log[j]
                layertype, layercmd = layercmd.split(" ", maxsplit=1)
                j -= 1

                final_image_size += layersize
                if stepno == last_FROM or layertype == buildstep.type:
                    buildstep.layer = BuildLayer(
                        type=layertype,
                        command=layercmd,
                        size=layersize,
                        id=layerid if "missing" not in layerid else None,
                        index=j,
                    )
                    break
                else:
                    base_image_size += layersize

        # for each Step, find the layer ID
        cached_layers = 0
        for stepno in sorted(buildsteps.keys()):
            buildstep = buildsteps[stepno]
            indent_str = "  "
            stepno_str = "Step:"
            size_str = "Size:"
            # check for cached layers
            step_cache = tc.colored("No", "red")
            if buildstep.type == "FROM":
                cached_layers += 1
                step_cache = tc.colored("--", "white")
            elif buildstep.cached:
                cached_layers += 1
                step_cache = tc.colored("Yes", "green")
            # get Step info
            print("-" * SEPARATORS_LENGTH)
            # get info about layer ID and size
            layersize = "ND"
            # ---
            if buildstep.layer is not None and buildstep.layer.size is not None:
                layersize = size_fmt(buildstep.layer.size)
                if buildstep.layer.size > LAYER_SIZE_YELLOW:
                    fg_color = "red" if buildstep.layer.size > LAYER_SIZE_RED else "yellow"
                    fg_color = "blue" if stepno == 1 else fg_color
                    layersize = tc.colored(layersize, fg_color)

            # print info about the current layer
            print(
                "%s %s/%s\n%sCommand: %s %s\n%sCached: %s\n%s%s %s"
                % (
                    stepno_str, stepno, steptot,
                    indent_str, buildstep.type, buildstep.command,
                    indent_str, step_cache,
                    indent_str, size_str, layersize,
                )
            )

        # get info about layers
        tot_layers = len(buildsteps)
        cached_layers = min(tot_layers, cached_layers)

        # print info about the whole image
        print()
        print("=" * SEPARATORS_LENGTH)
        print("Final image names:\n\t" + "\n\t".join(image_names))
        print("Base image size: " + size_fmt(base_image_size))
        print("Final image size: " + size_fmt(final_image_size))
        print("Your image added %s to the base image." % size_fmt(final_image_size - base_image_size))
        print(EXTRA_INFO_SEPARATOR)
        print("Layers total: {:d}".format(tot_layers))
        print(" - Built: {:d}".format(tot_layers - cached_layers))
        print(" - Cached: {:d}".format(cached_layers))
        if extra_info is not None and len(extra_info) > 0:
            print(EXTRA_INFO_SEPARATOR)
            print(extra_info)
        print("=" * SEPARATORS_LENGTH)
