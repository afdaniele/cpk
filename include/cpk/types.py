import abc
import copy
import dataclasses
import json
import logging
import os
from enum import Enum
from shutil import rmtree
from typing import List, Dict, Optional

import jsonschema
from docker import DockerClient

from cpk.utils.progress_bar import ProgressBar
from .constants import CANONICAL_ARCH
from .exceptions import \
    NotACPKProjectException, \
    InvalidCPKTemplateFile, InvalidCPKTemplate, \
    CPKTemplateSchemaNotSupported, CPKException
from .schemas import get_template_schema

Arguments = List[str]


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
        if self.tag != defaults.tag or self.arch:
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


class Machine(abc.ABC):
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
    @abc.abstractmethod
    def is_local(self) -> bool:
        pass

    @property
    def config_path(self) -> str:
        from cpk import cpkconfig
        return os.path.join(cpkconfig.path, "machines", self.name)

    @property
    def base_url(self) -> Optional[str]:
        return self._base_url

    @abc.abstractmethod
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
        try:
            # fetch architecture from client
            endpoint_arch = client.info()["Architecture"]
            if endpoint_arch not in CANONICAL_ARCH:
                raise CPKException(f"Unsupported architecture '{endpoint_arch}'.")
        finally:
            client.close()
        return CANONICAL_ARCH[endpoint_arch]

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

    def pull_image(self, image, progress=True) -> bool:
        client = self.get_client()
        layers = set()
        pulled = set()
        pbar = ProgressBar() if progress else None
        for line in client.api.pull(image, stream=True, decode=True):
            if "id" not in line or "status" not in line:
                continue
            layer_id = line["id"]
            layers.add(layer_id)
            if line["status"] in ["Already exists", "Pull complete"]:
                pulled.add(layer_id)
            # update progress bar
            if progress:
                percentage = max(0.0, min(1.0, len(pulled) / max(1.0, len(layers)))) * 100.0
                pbar.update(percentage)
        if progress:
            pbar.done()
        return True

    def push_image(self, image, progress=True, **kwargs):
        client = self.get_client()
        layers = set()
        pushed = set()
        pbar = ProgressBar() if progress else None
        for line in client.api.push(*image.split(":"), stream=True, decode=True, **kwargs):
            if "id" not in line or "status" not in line:
                continue
            layer_id = line["id"]
            layers.add(layer_id)
            if line["status"] in ["Layer already exists", "Pushed"]:
                pushed.add(layer_id)
            # update progress bar
            if progress:
                percentage = max(0.0, min(1.0, len(pushed) / max(1.0, len(layers)))) * 100.0
                pbar.update(percentage)
        if progress:
            pbar.done()

    def __str__(self):
        return """
Machine:
    Type:\t{}
    Name:\t{}
    URL:\t{}
""".format(type(self).__name__, self.name, self.base_url)


@dataclasses.dataclass
class CPKConfiguration:
    path: str
    machines: Dict[str, Machine]
