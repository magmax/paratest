import time
from yapsy.IPlugin import IPlugin


class Dummy(IPlugin):
    def find(self, path):
        return ['foo', 'bar', 'bazz']

    def run(self, id, tid, workspace, output_path):
        print("Worker %s: Running test %s" % (id, tid))
