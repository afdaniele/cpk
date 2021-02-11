import os
import json
from enum import Enum

import jsonschema

from .exceptions import \
    NotACPKProjectException, \
    InvalidCPKTemplateFile, InvalidCPKTemplate, \
    CPKTemplateSchemaNotSupported
from .schemas import get_template_schema
import dataclasses
from typing import Union, List, Dict


@dataclasses.dataclass
class CPKProjectInfo:
    name: str
    description: str
    owner: str
    template: 'CPKTemplateInfo'
    version: Union[None, str]
    registry: Union[None, str]
    tag: Union[None, str]


@dataclasses.dataclass
class GitRepositoryVersion:
    head: Union[None, str]
    closest: Union[None, str]


@dataclasses.dataclass
class GitRepositoryOrigin:
    url: Union[None, str]
    url_https: Union[None, str]


@dataclasses.dataclass
class GitRepositoryIndex:
    clean: bool
    num_added: Union[None, int]
    num_modified: Union[None, int]


@dataclasses.dataclass
class GitRepository:
    name: Union[None, str]
    sha: Union[None, str]
    branch: Union[None, str]
    present: bool
    detached: bool
    version: GitRepositoryVersion
    origin: GitRepositoryOrigin
    index: GitRepositoryIndex

    @staticmethod
    def default() -> 'GitRepository':
        return GitRepository(
            name=None,
            sha=None,
            branch=None,
            present=False,
            detached=False,
            version=GitRepositoryVersion(
                head=None,
                closest=None
            ),
            origin=GitRepositoryOrigin(
                url=None,
                url_https=None
            ),
            index=GitRepositoryIndex(
                clean=True,
                num_added=None,
                num_modified=None
            )
        )


class CPKFileMappingTrigger(Enum):
    DEFAULT = "default"
    RUN_MOUNT = "run:mount"


@dataclasses.dataclass
class CPKFileMapping:
    source: str
    destination: str
    triggers: List[CPKFileMappingTrigger]
    required: bool

    @staticmethod
    def from_dict(data: dict) -> 'CPKFileMapping':
        return CPKFileMapping(
            source=data['source'],
            destination=data['destination'],
            triggers=list(map(lambda t: CPKFileMappingTrigger(t),
                              data.get('triggers', ["default"]))),
            required=data.get('required', False)
        )


@dataclasses.dataclass
class CPKTemplateInfo:
    name: str
    version: str
    mappings: List[CPKFileMapping]
    url: Union[None, str]
    must_have: Dict[str, List[str]] = dataclasses.field(
        default_factory=lambda: {"files": [], "directories": []})

    @staticmethod
    def from_template_dict(data: dict) -> 'CPKTemplateInfo':
        # make sure the `schema` field is there
        if 'schema' not in data:
            raise InvalidCPKTemplate("Missing field: `schema`")
        # make sure we support that schema
        try:
            schema = get_template_schema(data["schema"])
        except FileNotFoundError:
            raise CPKTemplateSchemaNotSupported(data["schema"])
        # validate data against its declared schema
        try:
            jsonschema.validate(data, schema=schema)
        except jsonschema.ValidationError as e:
            raise InvalidCPKTemplate(str(e))
        # data is valid
        info = CPKTemplateInfo(
            name=data["name"],
            version=data["version"],
            mappings=list(map(lambda m: CPKFileMapping.from_dict(m), data.get('mappings', []))),
            url=data.get("url", None)
        )
        if "must_have" in data:
            info.must_have.update(data["must_have"])
        # ---
        return info

    @staticmethod
    def from_project_path(path: str) -> 'CPKTemplateInfo':
        metafile = os.path.join(path, "template.cpk")
        # check if the file 'template.cpk' is missing
        if not os.path.exists(metafile):
            raise NotACPKProjectException(path)
        # load 'template.cpk'
        with open(metafile, "rt") as fin:
            try:
                data = json.load(fin)
            except json.JSONDecodeError as e:
                raise InvalidCPKTemplateFile(path, f"File `{metafile}` must contain a valid JSON. "
                                                   f"DecoderError: {str(e)}")
        # make sure the `schema` field is there
        if 'schema' not in data:
            raise InvalidCPKTemplateFile(path, "Missing field: `schema`")
        # ---
        return CPKTemplateInfo.from_template_dict(data)
