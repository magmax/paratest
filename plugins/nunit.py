import os
import re
import logging
from yapsy.IPlugin import IPlugin

logger = logging.getLogger('paratest')

class Nunit(IPlugin):
    def find(self, path, test_pattern, file_pattern, output_path):
        c_file_pattern = re.compile(file_pattern)
        for root, _, files in os.walk(path):
            for filename in files:
                relative = os.path.join(root, filename).replace(path, '')

                if (c_file_pattern.match(filename)):
                    output_file = os.path.join(output_path, 'output_{ID}_{TID_NAME}.xml')
                    cmdline = 'nunit3-console %s --process:Single --result:%s;format=nunit2' % (relative, output_file)
                    yield (relative, cmdline)
