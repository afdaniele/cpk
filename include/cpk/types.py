import copy
import os
import json
from enum import Enum

import jsonschema

from .constants import CANONICAL_ARCH
from .exceptions import \
    NotACPKProjectException, \
    InvalidCPKTemplateFile, InvalidCPKTemplate, \
    CPKTemplateSchemaNotSupported
from .schemas import get_template_schema
import dataclasses
from typing import List, Dict, Optional


@dataclasses.dataclass
class CPKProjectInfo:
    name: str
    organization: Optional[str]
    description: Optional[str]
    maintainer: Optional[str]
    template: 'CPKTemplateInfo'
    version: Optional[str]
    registry: Optional[str]
    tag: Optional[str]
    mappings: List['CPKFileMapping'] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class GitRepositoryVersion:
    head: Optional[str]
    closest: Optional[str]


@dataclasses.dataclass
class GitRepositoryOrigin:
    url: Optional[str]
    url_https: Optional[str]
    organization: Optional[str]


@dataclasses.dataclass
class GitRepositoryIndex:
    clean: bool
    num_added: Optional[int]
    num_modified: Optional[int]


@dataclasses.dataclass
class GitRepository:
    name: Optional[str]
    sha: Optional[str]
    branch: Optional[str]
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

    def compile(self, allow_defaults: bool = False) -> Optional[str]:
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

    def __str__(self) -> str:
        return self.compile(allow_defaults=True)


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
    arch: Optional[str] = None

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
        # add - arch
        if self.arch:
            name += f"-{self.arch}"
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
        image.repository, tag, *_ = image_tag.split(':') + ["latest"]
        for arch in set(CANONICAL_ARCH.values()):
            if tag.endswith(f"-{arch}"):
                tag = tag[:-(len(arch) + 1)]
                image.arch = arch
                break
        image.tag = tag
        if registry:
            image.registry.hostname, image.registry.port, *_ = registry.split(':') + [5000]
        # ---
        return image

    def __str__(self) -> str:
        return f"""\
Registry:\t{str(self.registry)}
User:\t\t{self.user}
Repository:\t{self.repository}
Tag:\t\t{self.tag}
Arch:\t\t{self.arch}
        """


class CPKFileMappingTrigger(Enum):
    DEFAULT = "default"
    RUN_MOUNT = "run:mount"


@dataclasses.dataclass
class CPKFileMapping:
    source: str
    destination: str
    triggers: List[CPKFileMappingTrigger]
    required: bool

    def __copy__(self):
        return self.__deepcopy__({})

    def __deepcopy__(self, memo):
        return CPKFileMapping(
            source=self.source,
            destination=self.destination,
            triggers=copy.deepcopy(self.triggers),
            required=self.required
        )

    @staticmethod
    def from_dict(data: dict) -> 'CPKFileMapping':
        return CPKFileMapping(
            source=data['source'],
            destination=data['destination'],
            triggers=list(map(CPKFileMappingTrigger, data.get('triggers', ["default"]))),
            required=data.get('required', False)
        )


@dataclasses.dataclass
class CPKTemplateInfo:
    name: str
    version: str
    mappings: List[CPKFileMapping]
    url: Optional[str]
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
