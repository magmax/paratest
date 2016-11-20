import pexpect
import unittest


class PluginsTest(unittest.TestCase):
    def test_simple(self):
        p = pexpect.spawn('paratest plugins')
        p.expect('dummy')
        p.expect(pexpect.EOF)
