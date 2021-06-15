import argparse
import copy
import dataclasses
import os
import re
import json
from pathlib import Path
from typing import Any, Dict, Union, List, Optional

import jsonschema
import requests

from docker.errors import APIError, ImageNotFound

from .adapters import FileSystemAdapter, ProjectFileAdapter, GitRepositoryAdapter, CLIAdapter
from .adapters.generic import ProjectVersion, GenericAdapter
from .constants import DOCKERHUB_API_URL
from .exceptions import NotACPKProjectException, InvalidCPKProjectFile, \
    CPKProjectSchemaNotSupported, CPKMissingResourceException
from .schemas import get_project_schema
from .types import CPKProjectInfo, GitRepository, CPKTemplateInfo, CPKFileMapping, Machine
from .utils.git import get_repo_info
from .utils.misc import assert_canonical_arch, parse_configurations, cpk_label


class CPKProject:
    must_have_files = {
        "Dockerfile"
    }
    must_have_directories = set()

    def __init__(self, path: str, parsed: argparse.Namespace = None):
        # make sure the directory exists
        self._path = os.path.abspath(path)
        if not os.path.isdir(self._path):
            raise NotACPKProjectException(self._path)
        # try to read the project info from the project file
        self._info = self._get_info(self._path)
        # validate structure
        self._validate_project_structure()
        # define adapters
        self._adapters = {
            0: GenericAdapter("generic"),
            10: FileSystemAdapter(self._path),
            20: ProjectFileAdapter(self._info),
            30: GitRepositoryAdapter(self._path),
            40: CLIAdapter(parsed)
        }
        # look for a git repo
        self._repo = get_repo_info(self._path)
        # find features
        self._features = CPKProjectFeatures.from_project(self)

    @property
    def path(self) -> str:
        return self._path

    @property
    def name(self) -> str:
        return self._from_adapters("name")

    @property
    def registry(self) -> str:
        return self._from_adapters("registry")

    @property
    def organization(self) -> str:
        return self._from_adapters("organization")

    @property
    def description(self) -> Optional[str]:
        return self._from_adapters("description")

    @property
    def maintainer(self) -> Optional[str]:
        return self._from_adapters("maintainer")

    @property
    def version(self) -> ProjectVersion:
        return self._from_adapters("version")

    @property
    def template(self) -> CPKTemplateInfo:
        return self._info.template

    @property
    def repository(self) -> GitRepository:
        return self._repo

    @property
    def url(self) -> Optional[str]:
        return self._from_adapters("url")

    @property
    def adapters(self) -> Dict[str, GenericAdapter]:
        return {a.id: a for a in self._adapters.values() if a.enabled}

    @property
    def features(self) -> 'CPKProjectFeatures':
        return self._features

    @property
    def mappings(self) -> List[CPKFileMapping]:
        project_maps = self._info.mappings
        template_maps = []
        # project mappings have the priority over template mappings,
        # keep only the template mappings whose destination does not collide with any
        # of the project mappings
        for tmapping in self._info.template.mappings:
            collision = False
            for pmapping in project_maps:
                if pmapping.destination == tmapping.destination:
                    collision = True
                    break
            if not collision:
                template_maps.append(tmapping)
        # replace placeholders in mappings
        placeholders = {
            "project_name": self.name
        }
        mappings = []
        for mapping in template_maps + project_maps:
            cmapping = copy.deepcopy(mapping)
            cmapping.source = mapping.source.format(**placeholders)
            cmapping.destination = mapping.destination.format(**placeholders)
            mappings.append(cmapping)
        # ---
        return mappings

    def resource(self, resource: str) -> str:
        return os.path.join(self.path, resource.lstrip('/'))

    def is_release(self) -> bool:
        if not self.is_clean():
            return False
        if self.version.head is None:
            return False
        return True

    def is_clean(self) -> bool:
        return self._repo.index.clean

    def is_dirty(self) -> bool:
        return not self.is_clean()

    def is_detached(self) -> bool:
        return self._repo.detached

    def image(self, arch: str, docs: bool = False) -> str:
        assert_canonical_arch(arch)
        docs = "-docs" if docs else ""
        version = re.sub(r"[^\w\-.]", "-", self.version.tag)
        return f"{self.registry}/{self.organization}/{self.name}:{version}{docs}-{arch}"

    def image_release(self, arch: str, docs: bool = False) -> str:
        if not self.is_release():
            raise ValueError("The project repository is not in a release state")
        assert_canonical_arch(arch)
        docs = "-docs" if docs else ""
        version = re.sub(r"[^\w\-.]", "-", self.version.head)
        return f"{self.registry}/{self.organization}/{self.name}:{version}{docs}-{arch}"

    def configurations(self) -> dict:
        configurations = {}
        configurations_file = os.path.join(self._path, "configurations.yaml")
        if os.path.isfile(configurations_file):
            configurations = parse_configurations(configurations_file)
        # ---
        return configurations

    def configuration(self, name: str) -> dict:
        configurations = self.configurations()
        if name not in configurations:
            raise KeyError(f"Configuration with name '{name}' not found.")
        return configurations[name]

    def label(self, key: Union[List[str], str]) -> str:
        if isinstance(key, (list, tuple)):
            key = ".".join(key)
        return cpk_label(f"project.{self.organization}.{self.name}.{key}")

    def build_labels(self) -> Dict[str, str]:
        return {
            self.label("code.vcs"): "git" if self.repository.present else "ND",
            self.label("code.version.tag"): self.version.tag or "ND",
            self.label("code.version.head"): self.version.head or "ND",
            self.label("code.version.closest"): self.version.closest or "ND",
            self.label("code.version.sha"): self.version.sha if (self.version.sha and
                                                                 self.is_clean()) else "ND",
            self.label("code.vcs.repository"): self.repository.name or "ND",
            self.label("code.vcs.branch"): self.repository.branch or "ND",
            self.label("code.vcs.url"): self.repository.origin.url_https or "ND",
            self.label("template.name"): self.template.name,
            self.label("template.version"): self.template.version,
            self.label("template.url"): self.template.url or "ND",
            **self._launchers_labels(),
            **self._configurations_labels()
        }

    def launchers(self) -> List[str]:
        launchers_dir = os.path.join(self.path, "launchers")
        files = (
            [
                os.path.join(launchers_dir, f)
                for f in os.listdir(launchers_dir)
                if os.path.isfile(os.path.join(launchers_dir, f))
            ]
            if os.path.isdir(launchers_dir)
            else []
        )

        def _has_shebang(f):
            with open(f, "rt") as fin:
                return fin.readline().startswith("#!")

        launchers = [Path(f).stem for f in files if os.access(f, os.X_OK) or _has_shebang(f)]
        return launchers

    def image_metadata(self, machine: Machine, arch: str):
        image_name = self.image(arch)
        try:
            image = machine.get_client().images.get(image_name)
            return image.attrs
        except (APIError, ImageNotFound):
            return None

    def image_labels(self, machine: Machine, arch: str):
        image_name = self.image(arch)
        try:
            image = machine.get_client().images.get(image_name)
            return image.labels
        except (APIError, ImageNotFound):
            return None

    def remote_image_metadata(self, arch: str):
        assert_canonical_arch(arch)
        image = f"{self.organization}/{self.name}"
        tag = f"{self.version.tag}-{arch}"
        return self.inspect_remote_image(image, tag)

    def _from_adapters(self, key: str, default: Any = None) -> Any:
        for priority in sorted(self._adapters.keys(), reverse=True):
            adapter = self._adapters[priority]
            value = getattr(adapter, key)
            if value is not None:
                return value
        return default

    def _validate_project_structure(self):
        must_have_files = {
            "project": self.must_have_files,
            "template": self.template.must_have['files']
        }
        must_have_directories = {
            "project": self.must_have_directories,
            "template": self.template.must_have['directories']
        }
        # check "must_have" files
        for owner, files in must_have_files.items():
            for file in files:
                if not os.path.isfile(self.resource(file)):
                    msg = f"CPK {owner} requires the following file, but this was not found."
                    raise CPKMissingResourceException(file, explanation=msg)
        # check "must_have" directories
        for owner, directories in must_have_directories.items():
            for directory in directories:
                if not os.path.isdir(self.resource(directory)):
                    msg = f"CPK {owner} requires the following directory, but this was not found."
                    raise CPKMissingResourceException(directory, explanation=msg)

    def _launchers_labels(self) -> Dict[str, str]:
        return {self.label("code.launchers"): ",".join(self.launchers())}

    def _configurations_labels(self) -> Dict[str, str]:
        labels = {}
        # add configuration labels
        for cfg_name, cfg_data in self.configurations().items():
            labels[self.label(f"configuration.{cfg_name}")] = json.dumps(cfg_data)
        # ---
        return labels

    @staticmethod
    def _get_info(path: str) -> CPKProjectInfo:
        metafile = os.path.join(path, "project.cpk")
        # check if the file 'project.cpk' is missing
        if not os.path.exists(metafile):
            raise NotACPKProjectException(path)
        # load 'project.cpk'
        with open(metafile, "rt") as fin:
            try:
                data = json.load(fin)
            except json.JSONDecodeError as e:
                raise InvalidCPKProjectFile(path, f"File `{metafile}` must contain a valid JSON. "
                                                  f"DecoderError: {str(e)}")
        # make sure the `schema` field is there
        if 'schema' not in data:
            raise InvalidCPKProjectFile(path, "Missing field: `schema`")
        # make sure we support that schema
        try:
            schema = get_project_schema(data["schema"])
        except FileNotFoundError:
            raise CPKProjectSchemaNotSupported(data["schema"])
        # validate metadata against its declared schema
        try:
            jsonschema.validate(data, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            raise InvalidCPKProjectFile(path, str(e))
        # parse template
        template = CPKTemplateInfo.from_template_dict(data['template']) \
            if data.get("template", None) else CPKTemplateInfo.from_project_path(path)
        # metadata is valid
        return CPKProjectInfo(
            name=data["name"],
            organization=data.get("organization", None),
            description=data.get("description", None),
            maintainer=data.get("maintainer", None),
            template=template,
            version=data.get("version", None),
            registry=data.get("registry", None),
            tag=data.get("version", None),
            mappings=list(map(lambda m: CPKFileMapping.from_dict(m), data.get('mappings', [])))
        )

    @staticmethod
    def inspect_remote_image(image, tag):
        res = requests.get(DOCKERHUB_API_URL["token"].format(image=image)).json()
        token = res["token"]
        # ---
        res = requests.get(
            DOCKERHUB_API_URL["digest"].format(image=image, tag=tag),
            headers={
                "Accept": "application/vnd.docker.distribution.manifest.v2+json",
                "Authorization": "Bearer {0}".format(token),
            },
        ).text
        digest = json.loads(res)["config"]["digest"]
        # ---
        res = requests.get(
            DOCKERHUB_API_URL["inspect"].format(image=image, tag=tag, digest=digest),
            headers={"Authorization": "Bearer {0}".format(token)},
        ).json()
        return res


@dataclasses.dataclass
class CPKProjectFeatures:
    launchers: bool
    setup: bool
    configurations: bool
    assets: bool

    @staticmethod
    def from_project(project: CPKProject) -> 'CPKProjectFeatures':
        return CPKProjectFeatures(
            launchers=os.path.isdir(os.path.join(project.path, 'launchers')),
            setup=os.path.isfile(os.path.join(project.path, 'setup.sh')),
            configurations=os.path.isfile(os.path.join(project.path, 'configurations.yaml')),
            assets=os.path.isdir(os.path.join(project.path, 'assets'))
        )
