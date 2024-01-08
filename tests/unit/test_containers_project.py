import os
import unittest

import yaml
from mergedeep import merge, Strategy

from cpk import CPKProject
from cpk.types import CPKProjectContainersLayer, CPKContainerConfiguration

TEST_PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "projects"))
DEFAULT_ARCH: str = "amd64"


class TestContainersProject(unittest.TestCase):

    @staticmethod
    def get_project(name: str) -> CPKProject:
        return CPKProject(os.path.join(TEST_PROJECTS_DIR, name))

    @staticmethod
    def get_project_layer_raw(name: str, layer: str) -> dict:
        yaml_fpath: str = os.path.join(TEST_PROJECTS_DIR, name, "cpk", f"{layer}.yaml")
        with open(yaml_fpath, "rt") as fin:
            return yaml.safe_load(fin)

    def test_layer_containers(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        layer_raw: dict = self.get_project_layer_raw("containers", "containers")
        self.assertEqual(layer.as_dict(), layer_raw)

    def test_container_configuration_default(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        self.assertEqual(layer.get("default"), CPKContainerConfiguration())

    def test_container_configuration_development(self):
        project: CPKProject = self.get_project("containers")
        layer: CPKProjectContainersLayer = project.layers.containers
        self.assertEqual(layer.get("development"), CPKContainerConfiguration(
            _raw={
                "volumes": [
                    "./:${CPK_PROJECT_PATH}"
                ]
            }
        ))

    def test_layer_containers_enumerated_0(self):
        project: CPKProject = self.get_project("enumerated-layers")
        layer: CPKProjectContainersLayer = project.layers.containers
        layer0_raw: dict = self.get_project_layer_raw("enumerated-layers", "containers.template")
        layer1_raw: dict = self.get_project_layer_raw("enumerated-layers", "containers.this")
        layer_raw = merge(layer1_raw, layer0_raw, strategy=Strategy.ADDITIVE)
        self.assertEqual(layer.as_dict(), layer_raw)


if __name__ == '__main__':
    unittest.main()
