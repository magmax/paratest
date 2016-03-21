import time
import os
import re
import logging
from yapsy.IPlugin import IPlugin
from subprocess import Popen, PIPE

logger = logging.getLogger('paratest')

class Nunit(IPlugin):
    def find(self, path, pattern):
        p = re.compile(pattern)

        tests = []

        for root, _, files in os.walk(path):
            for file in files:
                f = os.path.join(root, file).replace(path, '')
                if (p.match(f)):
                    tests.append(f)

        return tests

    def run(self, id, tid, workspace, output_path):
        pass
        output_file = os.path.join(output_path, 'output_%s_%s' % (id, tid.replace('\\', '.')))
        tid_file = '%s\%s' % (workspace, tid)
        
        logger.debug("Worker %s: workspace %s" % (id,workspace))
        logger.debug("Worker %s: Running test %s" % (id, tid_file))

        cmdline = 'nunit3-console %s --process:Single --result:%s.xml;format=nunit2' % (tid_file, output_file)
        
        logger.debug(cmdline)
        
        result = Popen(cmdline, shell=True, stdout=PIPE, stderr=PIPE)
        output, err = result.communicate()

        output = output.decode("utf-8")
        err = err.decode("utf-8")

        if output != '':
            logger.info(output)
        if err != '':
            logger.warning(err)
        if result.returncode != 0:
            raise Exception("nunit returned %s instead of 0", result.errorcode)
        
