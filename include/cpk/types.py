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
    organization: str
    description: Union[None, str]
    maintainer: str
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
    organization: Union[None, str]


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
                url_https=None,
                organization=None
            ),
            index=GitRepositoryIndex(
                clean=True,
                num_added=None,
                num_modified=None
            )
        )


@dataclasses.dataclass
class DockerImageRegistry:
    hostname: str = "docker.io"
    port: int = 5000

    def is_default(self) -> bool:
        defaults = DockerImageRegistry()
        # add - registry
        if self.hostname != defaults.hostname or self.port != defaults.port:
            return False
        return True

    def compile(self, allow_defaults: bool = False) -> Union[None, str]:
        defaults = DockerImageRegistry()
        name = None if not allow_defaults else f"{defaults.hostname}"
        # add - registry
        if self.hostname != defaults.hostname:
            if self.port != defaults.port:
                name += f"{self.hostname}:{self.port}"
            else:
                name += f"{self.hostname}"
        # ---
        return name


@dataclasses.dataclass
class DockerImageName:
    """
    The official Docker image naming convention is:

        [REGISTRY[:PORT] /] USER / REPO [:TAG]

    """
    repository: str
    user: str = "library"
    registry: DockerImageRegistry = dataclasses.field(default_factory=DockerImageRegistry)
    tag: str = "latest"

    def compile(self) -> str:
        name = ""
        defaults = DockerImageName("_")
        # add - registry
        registry = self.registry.compile()
        if registry:
            name += f"{registry}/"
        # add - user
        if self.user != defaults.user:
            name += f"{self.user}/"
        # add - repository
        name += self.repository
        # add - tag
        if self.tag != defaults.tag:
            name += f":{self.tag}"
        # ---
        return name

    @staticmethod
    def from_image_name(name: str) -> 'DockerImageName':
        input_parts = name.split('/')
        image = DockerImageName(
            repository="X"
        )
        # ---
        registry = None
        # ---
        if len(input_parts) == 3:
            registry, image.user, image_tag = input_parts
        elif len(input_parts) == 2:
            image.user, image_tag = input_parts
        elif len(input_parts) == 1:
            image_tag = input_parts[0]
        else:
            raise ValueError("Invalid Docker image name")
        image.repository, image.tag, *_ = image_tag.split(':') + ["latest"]
        if registry:
            image.registry.hostname, image.registry.port, *_ = registry.split(':') + [5000]
        # ---
        return image


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
