import copy
import dataclasses
import json
import logging
import os
import re
from abc import abstractmethod, ABC
from enum import Enum
from shutil import rmtree
from typing import List, Dict, Optional, Union, Type, Iterator, Any

import jsonschema
from cpk.utils.misc import assert_canonical_arch

import cpk

from cpk.utils.progress_bar import ProgressBar
from .constants import CANONICAL_ARCH, DEFAULT_DOCKER_REGISTRY, DEFAULT_DOCKER_TAG, \
    DEFAULT_DOCKER_ORGANIZATION, DEFAULT_DOCKER_REGISTRY_PORT
from .exceptions import \
    NotACPKProjectException, \
    InvalidCPKTemplateFile, InvalidCPKTemplate, \
    CPKTemplateSchemaNotSupported, CPKException
from .utils.semver import SemanticVersion

from dockertown import Image, DockerClient

Arguments = List[str]
CPKProjectGenericLayer = dict
NOTSET = object


@dataclasses.dataclass
class Maintainer:
    name: str
    email: str

    @classmethod
    def parse(cls, data: dict) -> 'Maintainer':
        return Maintainer(name=data["name"], email=data["email"])

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class CPKProjectLayer:

    @classmethod
    @abstractmethod
    def parse(cls, data: dict) -> 'CPKProjectLayer':
        pass

    def as_dict(self) -> dict:
        unpack = lambda v: v.as_dict() if isinstance(v, CPKProjectLayer) else v
        return {
            field.name: unpack(getattr(self, field.name)) for field in dataclasses.fields(self)
        }


@dataclasses.dataclass
class CPKProjectSelfLayer(CPKProjectLayer):
    name: str
    description: str
    organization: str
    maintainer: Maintainer
    version: SemanticVersion
    distribution: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def parse(cls, data: dict) -> 'CPKProjectSelfLayer':
        return CPKProjectSelfLayer(
            name=data["name"],
            description=data["description"],
            organization=data["organization"],
            maintainer=Maintainer.parse(data["maintainer"]),
            version=SemanticVersion.parse(data["version"]),
            distribution=data.get("distribution", None),
            url=data.get("url", None),
        )


@dataclasses.dataclass
class CPKProjectFormatLayer(CPKProjectLayer):
    version: SemanticVersion

    @classmethod
    def parse(cls, data: dict) -> 'CPKProjectFormatLayer':
        return CPKProjectFormatLayer(
            version=SemanticVersion.parse(data["version"]),
        )


@dataclasses.dataclass
class CPKProjectTemplateLayer(CPKProjectLayer):
    provider: str
    organization: str
    name: str
    version: str
    url: Optional[str] = None

    @property
    def git_url(self) -> str:
        return f"https://{self.provider}/{self.organization}/{self.name}.git"

    @property
    def compact(self) -> str:
        return f"{self.provider}:{self.organization}/{self.name}@{self.version}"

    @classmethod
    def parse(cls, data: dict) -> 'CPKProjectTemplateLayer':
        return CPKProjectTemplateLayer(
            provider=data["provider"],
            organization=data["organization"],
            name=data["name"],
            version=data["version"],
            url=data.get("url", None),
        )


@dataclasses.dataclass
class CPKProjectStructureLayer(CPKProjectLayer):
    _structure: List['CPKProjectStructureLayer.Item']

    class Kind(Enum):
        FILE = "file"
        DIRECTORY = "directory"

    @dataclasses.dataclass
    class Item:
        kind: 'CPKProjectStructureLayer.Kind'
        required: bool = False
        description: Optional[str] = None

        @classmethod
        def parse(cls, data: dict) -> 'CPKProjectStructureLayer.Item':
            attrs = copy.copy(data)
            kind: CPKProjectStructureLayer.Kind = CPKProjectStructureLayer.Kind(attrs.pop("kind"))
            return CPKProjectStructureLayer.Item(
                kind=kind,
                **attrs
            )

        def as_dict(self) -> dict:
            return dataclasses.asdict(self)

    @property
    def items(self) -> Iterator[Item]:
        return iter(self._structure)

    @property
    def files(self) -> Iterator[Item]:
        return iter(filter(lambda item: item.kind is CPKProjectStructureLayer.Kind.FILE, self.items))

    @property
    def directories(self) -> Iterator[Item]:
        return iter(filter(lambda item: item.kind is CPKProjectStructureLayer.Kind.DIRECTORY, self.items))

    @classmethod
    def parse(cls, data: dict) -> 'CPKProjectStructureLayer':
        struct: List[CPKProjectStructureLayer.Item] = []
        for item in data["structure"]:
            struct.append(CPKProjectStructureLayer.Item.parse(item))
        return CPKProjectStructureLayer(
            _structure=struct
        )

    def as_dict(self) -> dict:
        return {
            "schema": "1.0",
            "structure": [
                item.as_dict() for item in self.items
            ]
        }


@dataclasses.dataclass
class CPKProjectBaseLayer(CPKProjectLayer):
    registry: str
    organization: str
    repository: str
    tag: str

    @classmethod
    def parse(cls, data: dict) -> 'CPKProjectBaseLayer':
        return CPKProjectBaseLayer(
            registry=data["registry"],
            organization=data["organization"],
            repository=data["repository"],
            tag=data["tag"],
        )


@dataclasses.dataclass
class CPKProjectLayersContainer:
    _others: Dict[str, dict]
    _self: CPKProjectSelfLayer
    _format: CPKProjectFormatLayer
    _base: CPKProjectBaseLayer
    _template: Optional[CPKProjectTemplateLayer] = None
    _structure: Optional[CPKProjectStructureLayer] = None

    @property
    def self(self) -> CPKProjectSelfLayer:
        return self._self

    @property
    def format(self) -> CPKProjectFormatLayer:
        return self._format

    @property
    def base(self) -> CPKProjectBaseLayer:
        return self._base

    @property
    def template(self) -> Optional[CPKProjectTemplateLayer]:
        return self._template

    @property
    def structure(self) -> Optional[CPKProjectStructureLayer]:
        return self._structure

    def get(self, layer: str, default: Any = NOTSET) -> Union[CPKProjectLayer, dict]:
        try:
            return self.__getitem__(layer)
        except KeyError as e:
            if default is NOTSET:
                raise e
            return default

    @classmethod
    def parse(cls, layers: dict) -> 'CPKProjectLayersContainer':
        known_layers: Dict[str, Type[CPKProjectLayer]] = {
            "self": CPKProjectSelfLayer,
            "format": CPKProjectFormatLayer,
            "template": CPKProjectTemplateLayer,
            "structure": CPKProjectStructureLayer,
            "base": CPKProjectBaseLayer,
        }
        parsed_layers: Dict[str, Union[CPKProjectLayer, dict]] = {}
        other_layers: Dict[str, dict] = {}
        for layer_name, layer in layers.items():
            if layer_name in known_layers:
                parsed_layers[f"_{layer_name}"] = known_layers[layer_name].parse(layer)
            else:
                other_layers[layer_name] = layer
        # ---
        return CPKProjectLayersContainer(
            _others=other_layers,
            **parsed_layers
        )

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        else:
            if item not in self._others:
                raise KeyError(f"Layer with name '{item}' not found.")
            return self._others[item]


@dataclasses.dataclass
class GitRepositoryVersion:
    head: Optional[str]
    closest: Optional[str]
    sha: Optional[str]


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
                closest=None,
                sha=None
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
class DockerRegistry:
    hostname: str = DEFAULT_DOCKER_REGISTRY
    port: int = DEFAULT_DOCKER_REGISTRY_PORT

    def is_default(self) -> bool:
        defaults = DockerRegistry()
        # add - registry
        if self.hostname != defaults.hostname or self.port != defaults.port:
            return False
        return True

    def compile(self, allow_defaults: bool = False) -> Optional[str]:
        defaults = DockerRegistry()
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

        [REGISTRY[:PORT] /] ORGANIZATION / REPO [:TAG]

    """
    repository: str
    organization: str = DEFAULT_DOCKER_ORGANIZATION
    tag: str = DEFAULT_DOCKER_TAG
    arch: Optional[str] = None
    registry: DockerRegistry = dataclasses.field(default_factory=DockerRegistry)
    extras: List[str] = dataclasses.field(default_factory=list)

    def compile(self, allow_defaults: bool = False) -> str:
        name = ""
        defaults = DockerImageName("_")
        # add - registry
        registry = self.registry.compile(allow_defaults=allow_defaults)
        if registry:
            name += f"{registry}/"
        # add - organization
        if self.organization != defaults.organization:
            name += f"{self.organization}/"
        # add - repository
        name += self.repository
        # add - tag
        if self.tag != defaults.tag or self.arch or self.extras:
            name += f":{self.tag}"
            for extra in self.extras:
                name += f"-{extra}"
        # add - arch
        if self.arch:
            name += f"-{self.arch}"
        # ---
        return name.lower()

    @staticmethod
    def parse(name: str) -> 'DockerImageName':
        input_parts = name.split('/')
        image = DockerImageName(
            # TODO: X ?
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

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.compile() or other == self.compile(allow_defaults=True)
        elif isinstance(other, DockerImageName):
            return other.compile(allow_defaults=True) == self.compile(allow_defaults=True)
        return False

    def __str__(self) -> str:
        return f"""\
Registry:\t{str(self.registry)}
Organization:\t\t{self.organization}
Repository:\t{self.repository}
Tag:\t\t{self.tag}
Arch:\t\t{self.arch}
        """


@dataclasses.dataclass
class DockerImage:
    _project: 'cpk.CPKProject'

    def fetch(self) -> Image:
        # TODO: implement this
        raise NotImplementedError()

    @staticmethod
    def _safe_string(s: str) -> str:
        return re.sub(r"[^\w\-]", "-", s)

    def name(self, arch: str, registry: str = DEFAULT_DOCKER_REGISTRY, extras: List[str] = None) \
            -> DockerImageName:
        assert_canonical_arch(arch)
        extras = extras or []
        return DockerImageName(
            registry=DockerRegistry(hostname=registry),
            repository=self._safe_string(self._project.name),
            organization=self._safe_string(self._project.organization),
            tag=self._safe_string(self._project.layers.self.distribution or DEFAULT_DOCKER_TAG),
            arch=arch,
            extras=extras,
        )

    def release_name(self, arch: str, registry: str = DEFAULT_DOCKER_REGISTRY, extras: List[str] = None) \
            -> DockerImageName:
        if not self._project.is_release():
            raise ValueError("The project repository is not in a release state")
        assert_canonical_arch(arch)
        extras = extras or []
        return DockerImageName(
            registry=DockerRegistry(hostname=registry),
            repository=self._safe_string(self._project.name),
            organization=self._safe_string(self._project.organization),
            tag=self._safe_string(self._project.repository.version.head),
            arch=arch,
            extras=extras,
        )


@dataclasses.dataclass
class CPKProjectDocker:
    _project: 'cpk.CPKProject'

    @property
    def registry(self) -> DockerRegistry:
        return DockerRegistry()

    @property
    def image(self) -> DockerImage:
        return DockerImage(_project=self._project)


class CPKFileMappingTrigger(Enum):
    DEFAULT = "default"
    RUN_MOUNT = "run:mount"


@dataclasses.dataclass
class CPKFileMapping:
    source: str
    destination: str
    triggers: List[str]
    required: bool
    mode: str = "rw"

    def __copy__(self):
        return self.__deepcopy__({})

    def __deepcopy__(self, memo):
        return CPKFileMapping(
            source=self.source,
            destination=self.destination,
            triggers=copy.deepcopy(self.triggers),
            required=self.required,
            mode=self.mode
        )

    @staticmethod
    def from_dict(data: dict) -> 'CPKFileMapping':
        return CPKFileMapping(
            source=data['source'],
            destination=data['destination'],
            triggers=data.get('triggers', ["default"]),
            required=data.get('required', False),
            mode=data.get('mode', "rw")
        )


class CPKMachine(ABC):
    type: str

    def __init__(self, name: str, base_url: Optional[str] = None,
                 configuration: Optional[Dict] = None):
        self._name = name
        self._base_url = base_url
        self._configuration = configuration or {}
        # cache
        self._arch = None

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def is_local(self) -> bool:
        pass

    @property
    def config_path(self) -> str:
        from cpk import cpkconfig
        return os.path.join(cpkconfig.path, "machines", self.name)

    @property
    def base_url(self) -> Optional[str]:
        return self._base_url

    @abstractmethod
    def get_client(self) -> DockerClient:
        raise NotImplementedError("Method 'get_client' needs to be implemented by child class")

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def save(self, logger: Optional[logging.Logger] = None):
        from . import cpkconfig
        path = os.path.join(cpkconfig.path, "machines", self.name)
        # make directory
        if logger:
            logger.debug(f"Creating directory '{path}'")
        os.makedirs(path, mode=0o700, exist_ok=True)
        # dump config.json
        cfg_fpath = os.path.join(path, "config.json")
        if logger:
            logger.debug(f"Creating machine descriptor file '{cfg_fpath}'")
        with open(cfg_fpath, "wt") as fout:
            json.dump({
                "version": "1.0",
                "type": self.type,
                "description": "",
                "configuration": self._configuration
            }, fout, indent=4, sort_keys=True)
        os.chmod(cfg_fpath, 0o600)

    def remove(self, logger: Optional[logging.Logger] = None):
        from . import cpkconfig
        path = os.path.join(cpkconfig.path, "machines", self.name)
        if logger:
            logger.debug(f"Removing machine directory '{path}'")
        if os.path.exists(path):
            rmtree(path)

    def get_architecture(self) -> str:
        if self._arch is not None:
            return self._arch
        # get client
        client = self.get_client()
        # fetch architecture from client
        endpoint_arch = client.info().architecture
        if endpoint_arch not in CANONICAL_ARCH:
            raise CPKException(f"Unsupported architecture '{endpoint_arch}'.")
        self._arch = CANONICAL_ARCH[endpoint_arch]
        return self._arch

    def get_ncpus(self, ) -> Optional[int]:
        # noinspection PyBroadException
        try:
            return self.get_client().info()["NCPU"]
        except BaseException:
            return None

    def login_client(self):
        username = os.environ.get('DOCKER_USERNAME', None)
        password = os.environ.get('DOCKER_PASSWORD', None)
        if username is not None and password is not None:
            self.get_client().login(username=username, password=password)

    def pull_image(self, image: str, progress: bool = True):
        docker: DockerClient = self.get_client()
        docker.image.pull(image, quiet=not progress)

    def push_image(self, image: str, progress: bool = True):
        docker: DockerClient = self.get_client()
        docker.image.push(image, quiet=not progress)

    def __str__(self):
        return """
Machine:
    Type:\t{}
    Name:\t{}
    URL:\t{}
""".format(type(self).__name__, self.name, self.base_url)

    def __eq__(self, other):
        if not isinstance(other, CPKMachine):
            return False
        return other.base_url == self.base_url


@dataclasses.dataclass
class CPKConfiguration:
    path: str
    machines: Dict[str, CPKMachine]
