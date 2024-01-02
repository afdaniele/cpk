import os
import unittest

import yaml

from cpk import CPKProject
from cpk.types import CPKProjectSelfLayer, CPKProjectTemplateLayer, CPKProjectFormatLayer, CPKProjectBaseLayer

TEST_PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "projects"))
DEFAULT_ARCH: str = "amd64"


class TestMinimalProject(unittest.TestCase):

    @staticmethod
    def get_project(name: str) -> CPKProject:
        return CPKProject(os.path.join(TEST_PROJECTS_DIR, name))

    @staticmethod
    def get_project_layer_raw(name: str, layer: str) -> dict:
        yaml_fpath: str = os.path.join(TEST_PROJECTS_DIR, name, "cpk", f"{layer}.yaml")
        with open(yaml_fpath, "rt") as fin:
            return yaml.safe_load(fin)

    def test_layer_self(self):
        project: CPKProject = self.get_project("minimal")
        layer: CPKProjectSelfLayer = project.layers.self
        layer_raw: dict = self.get_project_layer_raw("minimal", "self")
        self.assertEqual(layer.name, layer_raw["name"])
        self.assertEqual(layer.description, layer_raw["description"])
        self.assertEqual(layer.organization, layer_raw["organization"])
        self.assertEqual(layer.maintainer.as_dict(), layer_raw["maintainer"])
        self.assertEqual(layer.version, layer_raw["version"])
        self.assertEqual(layer.distribution, layer_raw.get("distribution", None))
        self.assertEqual(layer.url, layer_raw.get("url", None))

    def test_layer_template(self):
        project: CPKProject = self.get_project("minimal")
        layer: CPKProjectTemplateLayer = project.layers.template
        layer_raw: dict = self.get_project_layer_raw("minimal", "template")
        self.assertEqual(layer.provider, layer_raw["provider"])
        self.assertEqual(layer.organization, layer_raw["organization"])
        self.assertEqual(layer.name, layer_raw["name"])
        self.assertEqual(layer.version, layer_raw["version"])
        self.assertEqual(layer.url, layer_raw.get("url", None))

    def test_layer_format(self):
        project: CPKProject = self.get_project("minimal")
        layer: CPKProjectFormatLayer = project.layers.format
        layer_raw: dict = self.get_project_layer_raw("minimal", "format")
        self.assertEqual(layer.version, layer_raw["version"])

    def test_layer_base(self):
        project: CPKProject = self.get_project("minimal")
        layer: CPKProjectBaseLayer = project.layers.base
        layer_raw: dict = self.get_project_layer_raw("minimal", "base")
        self.assertEqual(layer.registry, layer_raw["registry"])
        self.assertEqual(layer.organization, layer_raw["organization"])
        self.assertEqual(layer.repository, layer_raw["repository"])
        self.assertEqual(layer.tag, layer_raw["tag"])


if __name__ == '__main__':
    unittest.main()
