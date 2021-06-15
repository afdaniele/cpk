import os
import json

import cpk

_SCHEMAS_DIR = os.path.join(os.path.dirname(cpk.__file__), 'schemas')


def _get_schema(schema_fpath: str) -> dict:
    if not os.path.isfile(schema_fpath):
        raise FileNotFoundError(schema_fpath)
    with open(schema_fpath, 'r') as fin:
        return json.load(fin)


def get_project_schema(schema: str) -> dict:
    schema_fpath = os.path.join(_SCHEMAS_DIR, "project.cpk", f"{schema}.json")
    return _get_schema(schema_fpath)


def get_template_schema(schema: str) -> dict:
    schema_fpath = os.path.join(_SCHEMAS_DIR, "template.cpk", f"{schema}.json")
    return _get_schema(schema_fpath)


def get_machine_schema(schema: str) -> dict:
    schema_fpath = os.path.join(_SCHEMAS_DIR, "machine", f"{schema}.json")
    return _get_schema(schema_fpath)


__all__ = [
    "get_project_schema",
    "get_template_schema",
    "get_machine_schema"
]
