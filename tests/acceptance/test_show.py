import os
import pexpect
import unittest


class ShowTest(unittest.TestCase):
    db_file = 'test.db'

    def setUp(self):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

    def test_without_previous_run(self):
        p = pexpect.spawn('paratest show --path-db=%s' % self.db_file)
        p.expect('No database was found')

    def test_after_run(self):
        s = pexpect.spawn('paratest run --path-db=%s --plugin Dummy -vv' % self.db_file)
        s.expect(pexpect.EOF)
        p = pexpect.spawn('paratest show --path-db=%s' % self.db_file)
        p.expect('bazz')
