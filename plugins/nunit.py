import time
import os
import re
import logging
from yapsy.IPlugin import IPlugin
from subprocess import Popen, PIPE

logger = logging.getLogger('paratest')

class Nunit(IPlugin):
    def find(self, path, test_pattern, file_pattern, output_path):
        c_file_pattern = re.compile(file_pattern)

        for root, _, files in os.walk(path):
            for file in files:
                relative = os.path.join(root, file).replace(path, '')
                if (c_file_pattern.match(f)):
                    output_file = os.path.join(output_path, 'output_{ID}_{TID_NAME}.xml')
                    tid_file = '%s\%s' % (workspace, file)
                    cmdline = 'nunit3-console %s --process:Single --result:%s;format=nunit2' % (relative, output_file)
                    yield cmdline

