import os
import pexpect
import unittest


class PluginsTest(unittest.TestCase):
    def test_simple(self):
        p = pexpect.spawn('paratest plugins')
        p.expect('Dummy')
