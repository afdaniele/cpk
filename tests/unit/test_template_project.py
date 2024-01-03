import os
import tempfile
import unittest

from cpk import CPKProject, CPKTemplate
from cpk.types import CPKProjectTemplateLayer

TEST_PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "projects"))


class TestTemplateProject(unittest.TestCase):

    @staticmethod
    def get_project(name: str) -> CPKProject:
        return CPKProject(os.path.join(TEST_PROJECTS_DIR, name))

    def test_no_template(self):
        project: CPKProject = self.get_project("minimal")
        self.assertEqual(project.layers.template, None)
        self.assertEqual(project.fetch_template(), None)

    def test_template_git_url(self):
        project: CPKProject = self.get_project("basic")
        template_layer: CPKProjectTemplateLayer = project.layers.template
        git_url = f"https://{template_layer.provider}/{template_layer.organization}/{template_layer.name}.git"
        self.assertEqual(template_layer.git_url, git_url)

    def test_template_download(self):
        project: CPKProject = self.get_project("basic")
        template_layer: CPKProjectTemplateLayer = project.layers.template
        self.assertNotEqual(template_layer, None)
        with tempfile.TemporaryDirectory() as tmp_dir:
            template_dir: str = os.path.join(tmp_dir, "cpk", "templates", template_layer.provider,
                                             template_layer.organization, template_layer.name,
                                             template_layer.version)
            # make sure the template directory does not exist
            self.assertFalse(os.path.exists(template_dir))
            template: CPKTemplate = project.fetch_template(tmp_dir=tmp_dir)
            # make sure the directories match
            self.assertEqual(template.path, template_dir)
            # make sure the template directory exists now
            self.assertTrue(os.path.exists(template_dir))

    def test_template_update(self):
        project: CPKProject = self.get_project("basic")
        template_layer: CPKProjectTemplateLayer = project.layers.template
        self.assertNotEqual(template_layer, None)
        with tempfile.TemporaryDirectory() as tmp_dir:
            template_dir: str = os.path.join(tmp_dir, "cpk", "templates", template_layer.provider,
                                             template_layer.organization, template_layer.name,
                                             template_layer.version)
            # make sure the template directory does not exist
            self.assertFalse(os.path.exists(template_dir))
            # this should trigger a download
            project.fetch_template(tmp_dir=tmp_dir)
            # make sure the template directory exists now
            self.assertTrue(os.path.exists(template_dir))
            # this should trigger an update instead
            project.fetch_template(tmp_dir=tmp_dir)
            # make sure the template directory is still there
            self.assertTrue(os.path.exists(template_dir))


if __name__ == '__main__':
    unittest.main()
