import dataclasses
import glob
import json
import os
from pathlib import Path
from typing import Dict, Union, List, Optional

import jsonschema
import requests
import yaml

from .constants import DOCKERHUB_API_URL
from .exceptions import NotACPKProjectException, DeprecatedCPKProjectFormat1Exception, \
    InvalidCPKProjectLayerFile, CPKProjectLayerSchemaNotSupported
from .schemas import get_layer_schema, have_schemas_for_layer
from .types import GitRepository, CPKProjectLayersContainer, Maintainer, CPKProjectDocker, \
    CPKProjectStructureLayer
from .utils.git import get_repo_info
from .utils.misc import parse_configurations, cpk_label
from .utils.semver import SemanticVersion


class CPKProject:

    def __init__(self, path: str):
        # make sure the directory exists
        self._path = os.path.abspath(path)
        if not os.path.isdir(self._path):
            raise NotADirectoryError(self._path)
        # make sure this is not an old CPK project
        if os.path.isfile(os.path.join(self._path, "project.cpk")):
            raise DeprecatedCPKProjectFormat1Exception(self._path)
        # make sure this is a CPK project
        if not os.path.isdir(os.path.join(self._path, "cpk")):
            raise NotACPKProjectException(self._path)
        # read layers
        layers_raw: Dict[str, dict] = self._read_layers(self._path)
        self._layers: CPKProjectLayersContainer = CPKProjectLayersContainer.parse(layers_raw)
        # validate structure
        if self._layers.structure:
            self._validate_project_structure(self._layers.structure)
        # look for a git repo
        self._repo = get_repo_info(self._path)
        # docker stuff
        self._docker = CPKProjectDocker(_project=self)
        # find features
        self._features = CPKProjectFeatures.from_project(self)

    @property
    def path(self) -> str:
        return self._path

    @property
    def name(self) -> str:
        return self.layers.self.name

    @property
    def description(self) -> str:
        return self.layers.self.description

    @property
    def organization(self) -> str:
        return self.layers.self.organization

    @property
    def maintainer(self) -> Maintainer:
        return self.layers.self.maintainer

    @property
    def version(self) -> SemanticVersion:
        return self.layers.self.version

    @property
    def url(self) -> Optional[str]:
        return self.layers.self.url

    # ---

    @property
    def layers(self) -> CPKProjectLayersContainer:
        return self._layers

    # ---

    @property
    def docker(self) -> CPKProjectDocker:
        return self._docker

    # @property
    # def template(self) -> CPKTemplateInfo:
    #     return self._info.template

    @property
    def repository(self) -> GitRepository:
        return self._repo

    @property
    def features(self) -> 'CPKProjectFeatures':
        return self._features

    # @property
    # def mappings(self) -> List[CPKFileMapping]:
    #     project_maps = self._info.mappings
    #     template_maps = []
    #     # project mappings have the priority over template mappings,
    #     # keep only the template mappings whose destination does not collide with any
    #     # of the project mappings
    #     for tmapping in self._info.template.mappings:
    #         collision = False
    #         for pmapping in project_maps:
    #             if pmapping.destination == tmapping.destination:
    #                 collision = True
    #                 break
    #         if not collision:
    #             template_maps.append(tmapping)
    #     # replace placeholders in mappings
    #     placeholders = {
    #         "project_name": self.name
    #     }
    #     mappings = []
    #     for mapping in template_maps + project_maps:
    #         cmapping = copy.deepcopy(mapping)
    #         cmapping.source = mapping.source.format(**placeholders)
    #         cmapping.destination = mapping.destination.format(**placeholders)
    #         mappings.append(cmapping)
    #     # ---
    #     return mappings

    def resource(self, resource: str) -> str:
        return os.path.join(self.path, resource.lstrip('/'))

    def is_release(self) -> bool:
        if not self.is_clean():
            return False
        if self.repository.version.head is None:
            return False
        return True

    def is_clean(self) -> bool:
        return self._repo.index.clean

    def is_dirty(self) -> bool:
        return not self.is_clean()

    def is_detached(self) -> bool:
        return self._repo.detached

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
        sha: str = self.repository.version.sha if (self.repository.version.sha and self.is_clean()) else "ND"
        return {
            self.label("code.vcs"): "git" if self.repository.present else "ND",
            self.label("code.version.head"): self.repository.version.head or "ND",
            self.label("code.version.closest"): self.repository.version.closest or "ND",
            self.label("code.version.sha"): sha,
            #
            # cpk.label.current="${ORGANIZATION}.${NAME}" \
            # cpk.label.project.${ORGANIZATION}.${NAME}.description="${DESCRIPTION}" \
            # cpk.label.project.${ORGANIZATION}.${NAME}.code.location="${PROJECT_PATH}" \
            # cpk.label.project.${ORGANIZATION}.${NAME}.base.registry="${BASE_REGISTRY}" \
            # cpk.label.project.${ORGANIZATION}.${NAME}.base.organization="${BASE_ORGANIZATION}" \
            # cpk.label.project.${ORGANIZATION}.${NAME}.base.project="${BASE_REPOSITORY}" \
            # cpk.label.project.${ORGANIZATION}.${NAME}.base.tag="${BASE_TAG}" \
            # cpk.label.project.${ORGANIZATION}.${NAME}.maintainer="${MAINTAINER}"
            #

            self.label("code.vcs.repository"): self.repository.name or "ND",
            self.label("code.vcs.branch"): self.repository.branch or "ND",
            self.label("code.vcs.url"): self.repository.origin.url_https or "ND",
            self.label("template.provider"): self.layers.template.provider,
            self.label("template.organization"): self.layers.template.organization,
            self.label("template.name"): self.layers.template.name,
            self.label("template.version"): self.layers.template.version,
            self.label("template.url"): self.layers.template.url or "ND",
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

    # def image_metadata(self, machine: Machine, arch: str):
    #     image_name = self.image(arch)
    #     try:
    #         image = machine.get_client().images.get(image_name)
    #         return image.attrs
    #     except (APIError, ImageNotFound):
    #         return None
    #
    # def image_labels(self, machine: Machine, arch: str):
    #     image_name = self.image(arch)
    #     try:
    #         image = machine.get_client().images.get(image_name)
    #         return image.labels
    #     except (APIError, ImageNotFound):
    #         return None
    #
    # def remote_image_metadata(self, arch: str):
    #     assert_canonical_arch(arch)
    #     image = f"{self.organization}/{self.name}"
    #     tag = f"{self.version.tag}-{arch}"
    #     return self.inspect_remote_image(image, tag)

    def _validate_project_structure(self, structure: CPKProjectStructureLayer):
        return

        # must_have_files = {
        #     "project": self.must_have_files,
        #     "template": self.template.must_have['files']
        # }
        # must_have_directories = {
        #     "project": self.must_have_directories,
        #     "template": self.template.must_have['directories']
        # }
        # # check "must_have" files
        # for owner, files in must_have_files.items():
        #     for file in files:
        #         if not os.path.isfile(self.resource(file)):
        #             msg = f"CPK {owner} requires the following file, but this was not found."
        #             raise CPKMissingResourceException(file, explanation=msg)
        # # check "must_have" directories
        # for owner, directories in must_have_directories.items():
        #     for directory in directories:
        #         if not os.path.isdir(self.resource(directory)):
        #             msg = f"CPK {owner} requires the following directory, but this was not found."
        #             raise CPKMissingResourceException(directory, explanation=msg)

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
    def _read_layers(path: str) -> Dict[str, dict]:
        layers: Dict[str, dict] = {}
        layers_pattern: str = os.path.join(path, "cpk", "*.yaml")
        for layer_fpath in glob.glob(layers_pattern):
            # get layer name and content
            layer_name: str = Path(layer_fpath).stem
            with open(layer_fpath, "rt") as fin:
                layer_content: str = fin.read()
            # parse layer content
            layer: dict = yaml.safe_load(layer_content)
            # make sure the `schema` field is there
            if 'schema' not in layer:
                raise InvalidCPKProjectLayerFile(path, "Missing field: `schema`")
            layer_schema_version: str = layer["schema"]
            # make sure we support that schema
            if have_schemas_for_layer(layer_name):
                try:
                    layer_schema = get_layer_schema(layer_name, layer_schema_version)
                except FileNotFoundError:
                    raise CPKProjectLayerSchemaNotSupported(layer_name, layer_schema_version)
                # validate metadata against its declared schema
                try:
                    jsonschema.validate(layer, schema=layer_schema)
                except jsonschema.exceptions.ValidationError as e:
                    raise InvalidCPKProjectLayerFile(path, str(e))
            # add layer to list
            layers[layer_name] = layer
        return layers

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
