import copy
import dataclasses
import json
import logging
import os
import re
import subprocess
from abc import abstractmethod, ABC
from contextlib import ExitStack, contextmanager
from datetime import timedelta
from enum import Enum
from shutil import rmtree
from tempfile import TemporaryDirectory
from typing import List, Dict, Optional, Union, Type, Iterator, Any, Tuple, ContextManager

from dacite import from_dict, Config
from mergedeep import merge, Strategy

import cpk
from cpk.utils.misc import assert_canonical_arch
from dockertown import Image, DockerClient
from dockertown.components.container.cli_wrapper import ValidPortMapping, Container, ValidContainer
from dockertown.components.image.cli_wrapper import ValidImage
from dockertown.components.network.cli_wrapper import ValidNetwork
from dockertown.utils import ValidPath
from .constants import CANONICAL_ARCH, DEFAULT_DOCKER_REGISTRY, DEFAULT_DOCKER_TAG, \
    DEFAULT_DOCKER_ORGANIZATION, DEFAULT_DOCKER_REGISTRY_PORT
from .exceptions import \
    CPKException, CPKProjectConflictException
from .models.docker.compose import Service, Volumes
from .utils.dockertown import populate_dockertown_configuration_from_docker_compose_service
from .utils.semver import SemanticVersion

Arguments = List[str]
CPKProjectGenericLayer = dict
EventName = str
NOTSET = object
BindMountDefinition = Union[Tuple[str, str], Tuple[str, str, str]]


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
class CPKProjectHooksLayer(CPKProjectLayer):
    _hooks: Dict[EventName, List['CPKProjectHooksLayer.Hook']] = dataclasses.field(default_factory=dict)

    @dataclasses.dataclass
    class Hook:
        command: Union[str, List[str]]
        required: bool = False

        def execute(self, wkdir: str, context: dict = None):
            env = os.environ.copy()
            env.update(context or {})
            subprocess.run(
                self.command,
                cwd=wkdir,
                check=self.required,
                env=env,
                shell=isinstance(self.command, str)
            )

        @classmethod
        def parse(cls, data: dict) -> 'CPKProjectHooksLayer.Hook':
            return CPKProjectHooksLayer.Hook(**data)

        def as_dict(self) -> dict:
            return dataclasses.asdict(self)

    @property
    def all(self) -> Iterator[Tuple[EventName, List[Hook]]]:
        return self._hooks.items().__iter__()

    def filter(self, event: EventName) -> Iterator[Hook]:
        return iter(self._hooks.get(event, []))

    @classmethod
    def parse(cls, data: dict) -> 'CPKProjectHooksLayer':
        hooks: Dict[EventName, List['CPKProjectHooksLayer.Hook']] = {}
        for event, items in data["hooks"].items():
            hooks[event] = []
            for item in items:
                hooks[event].append(CPKProjectHooksLayer.Hook.parse(item))
        return CPKProjectHooksLayer(
            _hooks=hooks
        )

    def as_dict(self) -> dict:
        return {
            "schema": "1.0",
            "hooks": {
                event: [
                    item.as_dict() for item in items
                ] for event, items in self._hooks.items()
            }
        }


@dataclasses.dataclass
class ManagedNamedVolume:
    name: str
    volume: Volumes

    @dataclasses.dataclass
    class ContextManager(ContextManager[TemporaryDirectory]):
        managed: 'ManagedNamedVolume'
        location: Optional[str] = None

        def __enter__(self):
            if self.location is None:
                with TemporaryDirectory() as tmpdir:
                    self.managed.volume.source = tmpdir
                    yield tmpdir
            else:
                dpath: str = os.path.join(self.location, "named_volumes", self.managed.name)
                os.makedirs(dpath, exist_ok=True)
                self.managed.volume.source = dpath
                yield dpath

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.managed.volume.source = None

    def instantiate(self, location: Optional[str] = None) -> 'ManagedNamedVolume.ContextManager':
        return ManagedNamedVolume.ContextManager(self, location=location)


@dataclasses.dataclass
class DockertownContainerConfiguration:
    image: Optional[ValidImage] = None
    command: List[str] = dataclasses.field(default_factory=list)
    add_hosts: List[Tuple[str, str]] = dataclasses.field(default_factory=list)
    blkio_weight: Optional[int] = None
    blkio_weight_device: List[str] = dataclasses.field(default_factory=list)
    cap_add: List[str] = dataclasses.field(default_factory=list)
    cap_drop: List[str] = dataclasses.field(default_factory=list)
    cgroup_parent: Optional[str] = None
    cgroupns: Optional[str] = None
    cidfile: Optional[ValidPath] = None
    cpu_period: Optional[int] = None
    cpu_quota: Optional[int] = None
    cpu_rt_period: Optional[int] = None
    cpu_rt_runtime: Optional[int] = None
    cpu_shares: Optional[int] = None
    cpus: Optional[float] = None
    cpuset_cpus: Optional[List[int]] = None
    cpuset_mems: Optional[List[int]] = None
    detach: bool = False
    devices: List[str] = dataclasses.field(default_factory=list)
    device_cgroup_rules: List[str] = dataclasses.field(default_factory=list)
    device_read_bps: List[str] = dataclasses.field(default_factory=list)
    device_read_iops: List[str] = dataclasses.field(default_factory=list)
    device_write_bps: List[str] = dataclasses.field(default_factory=list)
    device_write_iops: List[str] = dataclasses.field(default_factory=list)
    content_trust: bool = False
    dns: List[str] = dataclasses.field(default_factory=list)
    dns_options: List[str] = dataclasses.field(default_factory=list)
    dns_search: List[str] = dataclasses.field(default_factory=list)
    domainname: Optional[str] = None
    entrypoint: Optional[str] = None
    envs: Dict[str, str] = dataclasses.field(default_factory=dict)
    env_files: Union[ValidPath, List[ValidPath]] = dataclasses.field(default_factory=list)
    expose: Union[int, List[int]] = dataclasses.field(default_factory=list)
    gpus: Union[int, str, None] = None
    groups_add: List[str] = dataclasses.field(default_factory=list)
    healthcheck: bool = True
    health_cmd: Optional[str] = None
    health_interval: Union[None, int, timedelta] = None
    health_retries: Optional[int] = None
    health_start_period: Union[None, int, timedelta] = None
    health_timeout: Union[None, int, timedelta] = None
    hostname: Optional[str] = None
    init: bool = False
    interactive: bool = False
    ip: Optional[str] = None
    ip6: Optional[str] = None
    ipc: Optional[str] = None
    isolation: Optional[str] = None
    kernel_memory: Union[int, str, None] = None
    labels: Dict[str, str] = dataclasses.field(default_factory=dict)
    label_files: List[ValidPath] = dataclasses.field(default_factory=list)
    link: List[ValidContainer] = dataclasses.field(default_factory=list)
    link_local_ip: List[str] = dataclasses.field(default_factory=list)
    log_driver: Optional[str] = None
    log_options: List[str] = dataclasses.field(default_factory=list)
    mac_address: Optional[str] = None
    memory: Union[int, str, None] = None
    memory_reservation: Union[int, str, None] = None
    memory_swap: Union[int, str, None] = None
    memory_swappiness: Optional[int] = None
    mounts: List[List[str]] = dataclasses.field(default_factory=list)
    name: Optional[str] = None
    networks: List[ValidNetwork] = dataclasses.field(default_factory=list)
    network_aliases: List[str] = dataclasses.field(default_factory=list)
    oom_kill: bool = True
    oom_score_adj: Optional[int] = None
    pid: Optional[str] = None
    pids_limit: Optional[int] = None
    platform: Optional[str] = None
    privileged: bool = False
    publish: List[ValidPortMapping] = dataclasses.field(default_factory=list)
    publish_all: bool = False
    pull: str = "missing"
    read_only: bool = False
    restart: Optional[str] = None
    remove: bool = False
    runtime: Optional[str] = None
    security_options: List[str] = dataclasses.field(default_factory=list)
    shm_size: Union[int, str, None] = None
    sig_proxy: bool = True
    stop_signal: Optional[str] = None
    stop_timeout: Optional[int] = None
    storage_options: List[str] = dataclasses.field(default_factory=list)
    stream: bool = False
    sysctl: Dict[str, str] = dataclasses.field(default_factory=dict)
    tmpfs: List[ValidPath] = dataclasses.field(default_factory=list)
    tty: bool = False
    ulimit: List[str] = dataclasses.field(default_factory=list)
    user: Optional[str] = None
    userns: Optional[str] = None
    uts: Optional[str] = None
    volumes: List[BindMountDefinition] = dataclasses.field(default_factory=list)
    volume_driver: Optional[str] = None
    volumes_from: List[ValidContainer] = dataclasses.field(default_factory=list)
    workdir: Optional[ValidPath] = None
    x_passthrough_args: List[str] = dataclasses.field(default_factory=list)

    # auxiliary data
    _named_volumes: Dict[str, ManagedNamedVolume] = dataclasses.field(init=False, default_factory=dict)
    _deployment_dir: str = dataclasses.field(init=False, default=None)

    # managed data (things that are created and destroyed by this class)
    _managed: dict = dataclasses.field(init=False, default_factory=dict)

    @dataclasses.dataclass
    class Context(ContextManager[dict]):
        _project: 'cpk.CPKProject'
        _config: 'DockertownContainerConfiguration'

        _stack: Optional[ExitStack] = dataclasses.field(init=False, default=None)

        def __enter__(self) -> dict:
            if self._stack is not None:
                raise ValueError("You cannot enter a container configuration twice.")
            self._stack = ExitStack()
            # make temporary volumes
            self._config._managed["mounts"] = []
            for volume in self._config._named_volumes.values():
                tmpdir: TemporaryDirectory = self._stack.enter_context(
                    volume.instantiate(self._config._deployment_dir))
                self._config._managed["mounts"].append([tmpdir.name, volume.volume.target])
            # ---
            return self._config.compile(self._project)

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self._stack is None:
                return
            self._stack.__exit__(exc_type, exc_val, exc_tb)
            # clear
            self._config._managed["mounts"] = []
            self._stack = None

    def set(self, key: str, value: Any):
        if not hasattr(self, key):
            raise KeyError(f"Invalid configuration key '{key}'.")
        # ---
        setattr(self, key, value)

    def get(self, key: str):
        if not hasattr(self, key):
            raise KeyError(f"Invalid configuration key '{key}'.")
        # ---
        return getattr(self, key)

    def add_named_volume(self, name: str, volume: Volumes):
        self._named_volumes[name] = ManagedNamedVolume(name, volume)

    def compile(self, project: 'cpk.CPKProject') -> dict:
        cfg: dict = {}
        for field in dataclasses.fields(self):
            # exclude - private fields
            if not field.init:
                continue
            # exclude - optional fields with default constructor
            if field.default_factory in [list, dict] and len(self.get(field.name)) == 0:
                continue
            # exclude - optional fields with default value
            if field.default is not dataclasses.MISSING and self.get(field.name) == field.default:
                continue
            # ---
            cfg[field.name] = self.get(field.name)
        # TODO: add named volumes
        # convert relative paths in volumes to absolute paths
        abs = lambda p: os.path.abspath(p if os.path.isabs(p) else os.path.join(project.path, p))
        cfg["volumes"] = [(abs(v[0]), *v[1:]) for v in cfg.get("volumes", [])]
        # ---
        return cfg

    def for_project(self, project: 'cpk.CPKProject') -> 'DockertownContainerConfiguration.Context':
        return DockertownContainerConfiguration.Context(_project=project, _config=self)

    def merge(self, config: 'DockertownContainerConfiguration', project: 'cpk.CPKProject',
              only: List[str] = None, exclude: List[str] = None):
        for field in dataclasses.fields(self):
            # exclude - private fields
            if not field.init:
                continue
            # exclude specific fields
            if only is not None and field.name not in only:
                continue
            if exclude is not None and field.name in exclude:
                continue
            # volumes are treated separately
            if field.name == "volumes":
                continue
            # merge
            ours: Any = self.get(field.name)
            theirs: Any = config.get(field.name)
            # merge lists and dicts
            if isinstance(ours, list):
                ours.extend(theirs)
            if isinstance(ours, dict):
                ours.update(theirs)
            # replace other fields
            if theirs is not None:
                self.set(field.name, theirs)
        # convert relative paths in volumes to absolute paths
        abs = lambda p: os.path.abspath(p if os.path.isabs(p) else os.path.join(project.path, p))
        new_volumes: List[BindMountDefinition] = [(abs(v[0]), *v[1:]) for v in config.volumes]
        self.volumes += new_volumes
        # named volumes are merged as well as long as they are not already defined
        for name, volume in config._named_volumes.items():
            if name in self._named_volumes:
                raise CPKProjectConflictException(f"Some of the projects you are mounting reuse the name "
                                                  f"'{name}' for a named volume. This is not allowed.")
            self._named_volumes[name] = volume

    @classmethod
    def from_service(cls, service: Service) -> 'DockertownContainerConfiguration':
        cfg: DockertownContainerConfiguration = DockertownContainerConfiguration()
        populate_dockertown_configuration_from_docker_compose_service(cfg, service)
        return cfg


@dataclasses.dataclass
class CPKContainerConfiguration:
    _raw: dict = dataclasses.field(default_factory=dict)
    service: Service = dataclasses.field(default_factory=Service)
    extends: List[str] = dataclasses.field(default_factory=list)

    def as_docker_compose_file(self, service_name: str = "service", **kwargs) \
            -> dict:
        return {
            "version": "3.7",
            "services": {
                service_name: merge(self._raw, kwargs, strategy=Strategy.ADDITIVE)
            }
        }

    def as_dockertown_configuration(self) -> DockertownContainerConfiguration:
        return DockertownContainerConfiguration.from_service(self.service)

    @classmethod
    def parse(cls, data: dict) -> 'CPKContainerConfiguration':
        data = copy.copy(data)
        extends: List[str] = data.pop("__extends__", [])
        service: Service = from_dict(Service, data, config=Config(cast=[Enum]))
        return CPKContainerConfiguration(
            _raw=data,
            service=service,
            extends=extends
        )

    def as_dict(self) -> dict:
        return {
            **self._raw,
            **({"__extends__": self.extends} if self.extends else {})
        }

    def __eq__(self, other):
        if not isinstance(other, CPKContainerConfiguration):
            return False
        return self.as_dict() == other.as_dict()


@dataclasses.dataclass
class CPKProjectContainersLayer(CPKProjectLayer):
    _containers: Dict[str, 'CPKContainerConfiguration'] = \
        dataclasses.field(default_factory=dict)

    def __post_init__(self):
        # make default container configuration if it does not exist
        if "default" not in self._containers:
            self._containers["default"] = CPKContainerConfiguration()

    def has(self, name: str) -> bool:
        return name in self._containers

    def get(self, name: str, default: Any = NOTSET) -> CPKContainerConfiguration:
        if name not in self._containers and default is NOTSET:
            raise KeyError(f"Container configuration with name '{name}' not found.")
        return self._containers.get(name, default)

    @property
    def all(self) -> Iterator[Tuple[str, CPKContainerConfiguration]]:
        return self._containers.items().__iter__()

    @property
    def keys(self) -> Iterator[str]:
        return self._containers.keys().__iter__()

    @classmethod
    def parse(cls, data: dict) -> 'CPKProjectContainersLayer':
        containers: Dict[str, 'CPKContainerConfiguration'] = {}
        for name, configuration in data["containers"].items():
            containers[name] = CPKContainerConfiguration.parse(configuration)
        return CPKProjectContainersLayer(
            _containers=containers
        )

    def as_dict(self) -> dict:
        return {
            "schema": "1.0",
            "containers": {
                name: configuration.as_dict()
                for name, configuration in self._containers.items()
            }
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
    _hooks: Optional[CPKProjectHooksLayer] = dataclasses.field(default_factory=CPKProjectHooksLayer)
    _containers: Optional[CPKProjectContainersLayer] = dataclasses.field(
        default_factory=CPKProjectContainersLayer)

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

    @property
    def hooks(self) -> CPKProjectHooksLayer:
        return self._hooks

    @property
    def containers(self) -> CPKProjectContainersLayer:
        return self._containers

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
            "hooks": CPKProjectHooksLayer,
            "containers": CPKProjectContainersLayer,
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
            registry, image.organization, image_tag = input_parts
        elif len(input_parts) == 2:
            image.organization, image_tag = input_parts
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
Registry:      {str(self.registry)}
Organization:  {self.organization}
Repository:    {self.repository}
Tag:           {self.tag}
Arch:          {self.arch}
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

    def run(self, machine: 'CPKMachine', configuration: DockertownContainerConfiguration) \
            -> Union[str, Container]:
        cfg: dict = configuration.compile(self._project)
        # add image if needed
        if "image" not in cfg:
            cfg["image"] = self.image.name(arch=machine.get_architecture()).compile()
        # run container
        return machine.get_client().container.run(**cfg)

    @contextmanager
    def container(self, machine: 'CPKMachine', configuration: DockertownContainerConfiguration) -> \
            Union[str, Container]:
        # ---
        with configuration.for_project(self._project) as cfg:
            # add image if needed
            if "image" not in cfg:
                cfg["image"] = self.image.name(arch=machine.get_architecture()).compile()
            # run container
            result: Union[str, Container] = machine.get_client().container.run(**cfg)
            try:
                yield result
            finally:
                pass


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
