import os
import unittest

import yaml

from cpk import CPKProject
from cpk.types import CPKProjectSelfLayer, CPKProjectTemplateLayer, CPKProjectFormatLayer, \
    CPKProjectBaseLayer, CPKProjectStructureLayer

TEST_PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "projects"))
DEFAULT_ARCH: str = "amd64"


class TestBasicProject(unittest.TestCase):

    @staticmethod
    def get_project(name: str) -> CPKProject:
        return CPKProject(os.path.join(TEST_PROJECTS_DIR, name))

    @staticmethod
    def get_project_layer_raw(name: str, layer: str) -> dict:
        yaml_fpath: str = os.path.join(TEST_PROJECTS_DIR, name, "cpk", f"{layer}.yaml")
        with open(yaml_fpath, "rt") as fin:
            return yaml.safe_load(fin)

    def test_layer_self(self):
        project: CPKProject = self.get_project("basic")
        layer: CPKProjectSelfLayer = project.layers.self
        layer_raw: dict = self.get_project_layer_raw("basic", "self")
        self.assertEqual(layer.name, layer_raw["name"])
        self.assertEqual(layer.description, layer_raw["description"])
        self.assertEqual(layer.organization, layer_raw["organization"])
        self.assertEqual(layer.maintainer.as_dict(), layer_raw["maintainer"])
        self.assertEqual(layer.version, layer_raw["version"])
        self.assertEqual(layer.distribution, layer_raw.get("distribution", None))
        self.assertEqual(layer.url, layer_raw.get("url", None))

    def test_layer_template(self):
        project: CPKProject = self.get_project("basic")
        layer: CPKProjectTemplateLayer = project.layers.template
        layer_raw: dict = self.get_project_layer_raw("basic", "template")
        self.assertEqual(layer.provider, layer_raw["provider"])
        self.assertEqual(layer.organization, layer_raw["organization"])
        self.assertEqual(layer.name, layer_raw["name"])
        self.assertEqual(layer.version, layer_raw["version"])
        self.assertEqual(layer.url, layer_raw.get("url", None))

    def test_layer_format(self):
        project: CPKProject = self.get_project("basic")
        layer: CPKProjectFormatLayer = project.layers.format
        layer_raw: dict = self.get_project_layer_raw("basic", "format")
        self.assertEqual(layer.version, layer_raw["version"])

    def test_layer_base(self):
        project: CPKProject = self.get_project("basic")
        layer: CPKProjectBaseLayer = project.layers.base
        layer_raw: dict = self.get_project_layer_raw("basic", "base")
        self.assertEqual(layer.registry, layer_raw["registry"])
        self.assertEqual(layer.organization, layer_raw["organization"])
        self.assertEqual(layer.repository, layer_raw["repository"])
        self.assertEqual(layer.tag, layer_raw["tag"])

    def test_layer_structure(self):
        project: CPKProject = self.get_project("basic")
        layer: CPKProjectStructureLayer = project.layers.structure
        layer_raw: dict = self.get_project_layer_raw("basic", "structure")
        self.assertEqual(layer.as_dict(), layer_raw)

    def test_layer_custom_0(self):
        project: CPKProject = self.get_project("basic")
        layer: dict = project.layers["custom_layer_0"]
        layer_raw: dict = self.get_project_layer_raw("basic", "custom_layer_0")
        self.assertEqual(layer, layer_raw)

    def test_layer_custom_1(self):
        project: CPKProject = self.get_project("basic")
        layer: dict = project.layers["custom_layer_1"]
        layer_raw: dict = self.get_project_layer_raw("basic", "custom_layer_1")
        self.assertEqual(layer, layer_raw)

    def test_layer_not_found(self):
        project: CPKProject = self.get_project("basic")
        # raises if we do not specify a default
        self.assertRaises(KeyError, lambda: project.layers.get("not_existent"))
        # does not raise if we give it a default
        project.layers.get("not_existent", {})


if __name__ == '__main__':
    unittest.main()
