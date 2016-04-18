import os
import pexpect
import unittest


class RunTest(unittest.TestCase):
    db_file = 'test.db'

    def setUp(self):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

    def test_basic(self):
        p = pexpect.spawn('paratest run --plugin Dummy --path-db=%s -vv' % self.db_file)
        p.expect('Global Report')
        p.expect(pexpect.EOF)
        assert not p.isalive()
