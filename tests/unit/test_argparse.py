import unittest
import cpk


class TestArgparse(unittest.TestCase):

    def setUp(self):
        self.parser = cpk.cli.get_parser()

    def test_A(self):
        self.assertTrue(True)

    def test_B(self):
        self.assertFalse(False)


if __name__ == '__main__':
    unittest.main()
