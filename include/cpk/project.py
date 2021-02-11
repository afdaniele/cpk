import dataclasses
import os
import re
import json
from typing import Any, Dict

import jsonschema
import requests

from docker.errors import APIError, ImageNotFound

from .adapters import FileSystemAdapter, ProjectFileAdapter, GitRepositoryAdapter
from .adapters.generic import ProjectVersion, GenericAdapter
from .constants import DOCKERHUB_API_URL
from .exceptions import NotACPKProjectException, InvalidCPKProjectFile, \
    CPKProjectSchemaNotSupported, CPKMissingResourceException
from .schemas import get_project_schema
from .types import CPKProjectInfo, GitRepository, CPKTemplateInfo
from .utils.git import get_repo_info
from .utils.misc import assert_canonical_arch, parse_configurations
from .utils import docker


class CPKProject:

    must_have_files = {
        "Dockerfile"
    }
    must_have_directories = set()

    def __init__(self, path: str):
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
            10: FileSystemAdapter(self._path),
            20: ProjectFileAdapter(self._info),
            30: GitRepositoryAdapter(self._path)
        }
        # look for a git repo
        self._repo = get_repo_info(self._path)
        # find features
        self._features = CPKProjectFeatures.from_project(self)

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self._from_adapters("name")

    @property
    def owner(self):
        return self._from_adapters("owner")

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
    def url(self):
        return self._from_adapters("url")

    @property
    def adapters(self) -> Dict[str, GenericAdapter]:
        return {a.id: a for a in self._adapters.values() if a.enabled}

    @property
    def features(self) -> 'CPKProjectFeatures':
        return self._features

    def resource(self, resource: str):
        return os.path.join(self.path, resource.lstrip('/'))

    def is_release(self):
        if not self.is_clean():
            return False
        if self.version.head is None:
            return False
        return True

    def is_clean(self):
        return self._repo.index.clean

    def is_dirty(self):
        return not self.is_clean()

    def is_detached(self):
        return self._repo.detached

    def image(self, arch: str, docs: bool = False) -> str:
        assert_canonical_arch(arch)
        docs = "-docs" if docs else ""
        version = re.sub(r"[^\w\-.]", "-", self.version.tag)
        return f"{self.owner}/{self.name}:{version}{docs}-{arch}"

    def image_release(self, arch: str, docs: bool = False) -> str:
        if not self.is_release():
            raise ValueError("The project repository is not in a release state")
        assert_canonical_arch(arch)
        docs = "-docs" if docs else ""
        version = re.sub(r"[^\w\-.]", "-", self.version.head)
        return f"{self.owner}/{self.name}:{version}{docs}-{arch}"

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

    def image_metadata(self, endpoint, arch: str):
        client = docker.get_client(endpoint)
        image_name = self.image(arch)
        try:
            image = client.images.get(image_name)
            return image.attrs
        except (APIError, ImageNotFound):
            return None

    def image_labels(self, endpoint, arch: str):
        client = docker.get_client(endpoint)
        image_name = self.image(arch)
        try:
            image = client.images.get(image_name)
            return image.labels
        except (APIError, ImageNotFound):
            return None

    def remote_image_metadata(self, arch: str):
        assert_canonical_arch(arch)
        image = f"{self.owner}/{self.name}"
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
            description=data["description"],
            owner=data.get("owner", None),
            template=template,
            version=data.get("version", None),
            registry=data.get("registry", None),
            tag=data.get("version", None)
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
