import unittest
from subprocess import run


class TestInstall(unittest.TestCase):
    def test_library_installed(self):
        import quantready_api

        self.assertIsNotNone(quantready_api)

    def test_module(self):
        run(["python", "-m", "quantready_api", "--help"])

    def test_consolescript(self):
        run(["quantready-api", "--help"])
