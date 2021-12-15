import os
import subprocess
import unittest
import docker

from cpk import CPKProject
from cpk.machine import FromEnvMachine


examples_dir = lambda e: \
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "examples", e))


class TestBuildProjectBasic(unittest.TestCase):

    def setUp(self):
        self._project_dir = examples_dir("basic")
        self._project = CPKProject(self._project_dir)
        self._machine = FromEnvMachine()
        self._image = self._project.image(self._machine.get_architecture())

    def _clean(self):
        client = self._machine.get_client()
        try:
            client.images.remove(self._image)
        except docker.errors.ImageNotFound:
            return False
        finally:
            client.close()
        # ---
        return True

    def test_build_plain(self):
        # clean
        self._clean()
        self.assertFalse(self._clean())
        # build
        subprocess.check_call([
            "cpk", "build"
        ], stdout=subprocess.DEVNULL, cwd=self._project_dir)
        # check
        self.assertTrue(self._clean())

    def test_build_from_different_dir(self):
        # clean
        self._clean()
        self.assertFalse(self._clean())
        # build
        subprocess.check_call([
            "cpk", "build", "-C", self._project_dir
        ], stdout=subprocess.DEVNULL)
        # check
        self.assertTrue(self._clean())


if __name__ == '__main__':
    unittest.main()
