import unittest

from cpk.utils.semver import SemanticVersion


class TestInternal_SemanticVersion(unittest.TestCase):

    def test_instantiate_0(self):
        SemanticVersion(1)

    def test_instantiate_1(self):
        SemanticVersion(1, 2)

    def test_instantiate_2(self):
        SemanticVersion(1, 2, 3)

    def test_instantiate_3(self):
        SemanticVersion(1, 2, 3, "rc-1")

    def test_parse_0(self):
        SemanticVersion.parse("1")

    def test_parse_1(self):
        SemanticVersion.parse("1.2")

    def test_parse_2(self):
        SemanticVersion.parse("1.2.3")

    def test_parse_3(self):
        SemanticVersion.parse("1.2.3.rc-1")

    def test_cross_0(self):
        self.assertTrue(SemanticVersion.parse("1") == "1")
        self.assertTrue(SemanticVersion.parse("1") == SemanticVersion(1))

    def test_cross_1(self):
        self.assertTrue(SemanticVersion.parse("1.2") == "1.2")
        self.assertTrue(SemanticVersion.parse("1.2") == SemanticVersion(1, 2))

    def test_cross_2(self):
        self.assertTrue(SemanticVersion.parse("1.2.3") == "1.2.3")
        self.assertTrue(SemanticVersion.parse("1.2.3") == SemanticVersion(1, 2, 3))

    def test_cross_3(self):
        self.assertTrue(SemanticVersion.parse("1.2.3.rc-1") == "1.2.3.rc-1")
        self.assertTrue(SemanticVersion.parse("1.2.3.rc-1") == SemanticVersion(1, 2, 3, "rc-1"))

    def test_lt_0(self):
        self.assertTrue(SemanticVersion.parse("1") < SemanticVersion.parse("2"))
        self.assertFalse(SemanticVersion.parse("2") < SemanticVersion.parse("1"))

    def test_lt_1(self):
        self.assertTrue(SemanticVersion.parse("1.2") < SemanticVersion.parse("1.3"))
        self.assertFalse(SemanticVersion.parse("1.3") < SemanticVersion.parse("1.2"))

    def test_lt_2(self):
        self.assertTrue(SemanticVersion.parse("1.2.3") < SemanticVersion.parse("1.2.4"))
        self.assertFalse(SemanticVersion.parse("1.2.4") < SemanticVersion.parse("1.2.3"))

    def test_lt_3(self):
        self.assertTrue(SemanticVersion.parse("1.2.3.rc-1") < SemanticVersion.parse("1.2.3.rc-2"))
        self.assertFalse(SemanticVersion.parse("1.2.3.rc-2") < SemanticVersion.parse("1.2.3.rc-1"))

    def test_lt_4(self):
        self.assertTrue(SemanticVersion.parse("1.2.3.rc-0001") < SemanticVersion.parse("1.2.3.rc-2"))
        self.assertFalse(SemanticVersion.parse("1.2.3.rc-2000") < SemanticVersion.parse("1.2.3.rc-1"))

    def test_gt_0(self):
        self.assertTrue(SemanticVersion.parse("2") > SemanticVersion.parse("1"))
        self.assertFalse(SemanticVersion.parse("1") > SemanticVersion.parse("2"))

    def test_gt_1(self):
        self.assertTrue(SemanticVersion.parse("1.3") > SemanticVersion.parse("1.2"))
        self.assertFalse(SemanticVersion.parse("1.2") > SemanticVersion.parse("1.3"))

    def test_gt_2(self):
        self.assertTrue(SemanticVersion.parse("1.2.4") > SemanticVersion.parse("1.2.3"))
        self.assertFalse(SemanticVersion.parse("1.2.3") > SemanticVersion.parse("1.2.4"))

    def test_gt_3(self):
        self.assertTrue(SemanticVersion.parse("1.2.3.rc-2") > SemanticVersion.parse("1.2.3.rc-1"))
        self.assertFalse(SemanticVersion.parse("1.2.3.rc-1") > SemanticVersion.parse("1.2.3.rc-2"))

    def test_gt_4(self):
        self.assertTrue(SemanticVersion.parse("1.2.3.rc-2000") > SemanticVersion.parse("1.2.3.rc-1"))
        self.assertFalse(SemanticVersion.parse("1.2.3.rc-0001") > SemanticVersion.parse("1.2.3.rc-2"))


if __name__ == '__main__':
    unittest.main()
