import unittest
from subprocess import run


class TestInstall(unittest.TestCase):
    def test_library_installed(self):
        import promptedgraphs

        self.assertIsNotNone(promptedgraphs)

    def test_module(self):
        run(["python3", "-m", "promptedgraphs", "--help"])

    # def test_consolescript(self):
    #     run(["promptedgraphs", "--help"])
