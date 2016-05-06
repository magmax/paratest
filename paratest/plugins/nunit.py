import os
import re
import logging
from yapsy.IPlugin import IPlugin

logger = logging.getLogger('paratest')

class Nunit(IPlugin):
    def find(self, path, test_pattern, file_pattern, output_path):
        logger.debug('Processing path %s with %s/%s', path, test_pattern, file_pattern)
        c_file_pattern = re.compile(file_pattern)
        for root, _, files in os.walk(path):
            for n, filename in enumerate(files):
                relative = os.path.join(root, filename).replace(path, '').lstrip('\\/')

                if (c_file_pattern.match(relative)):
                    logger.debug('File %s added', relative)
                    cmdline = 'nunit3-console --process:Single --result:{out}\\output_{{ID}}_{n}.xml;format=nunit2 {{WORKSPACE}}\\{lib}'.format(lib=relative, out=output_path, n=n)
                    yield (relative, cmdline)
                else:
                    logger.debug('File %s SKIPPED', relative)
