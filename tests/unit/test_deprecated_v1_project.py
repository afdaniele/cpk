import os
import unittest

from cpk import CPKProject
from cpk.exceptions import DeprecatedCPKProjectFormat1Exception

TEST_PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "projects"))


class TestDeprecatedV1Project(unittest.TestCase):

    @staticmethod
    def get_project(name: str) -> CPKProject:
        return CPKProject(os.path.join(TEST_PROJECTS_DIR, name))

    def test_loading_project(self):
        self.assertRaises(DeprecatedCPKProjectFormat1Exception, self.get_project, "deprecated-v1")


if __name__ == '__main__':
    unittest.main()
