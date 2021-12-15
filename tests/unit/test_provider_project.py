import os
import subprocess
import unittest
import docker
from cpk.exceptions import InvalidCPKProjectFile

from cpk import CPKProject
from cpk.machine import FromEnvMachine


test_projects_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "projects"))


class TestProviderProjectFile(unittest.TestCase):

    def setUp(self):
        self._machine = FromEnvMachine()

    @staticmethod
    def get_project(name: str) -> CPKProject:
        return CPKProject(os.path.join(test_projects_dir, name))

    def get_image_name(self, project: CPKProject):
        return project.image(self._machine.get_architecture())

    def _clean(self, project: CPKProject):
        client = self._machine.get_client()
        try:
            client.images.remove(self.get_image_name(project))
        except docker.errors.ImageNotFound:
            return False
        finally:
            client.close()
        # ---
        return True

    def test_load_bad_schema_project(self):
        self.assertRaises(InvalidCPKProjectFile, self.get_project, "project_file_schema_violation")


if __name__ == '__main__':
    unittest.main()
