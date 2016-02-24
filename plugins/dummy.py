import time
from yapsy.IPlugin import IPlugin


class Dummy(IPlugin):
    def find(self, path):
        return ['foo', 'bar', 'bazz']

    def init_environment(self, id, tmpdir):
        self.id = id
        self.tmpdir = tmpdir
        time.sleep(1)

    def run(self, tid):
        print("Running test %s" % tid)
