import os
import re
import tempfile
import shutil
import logging
from yapsy.IPlugin import IPlugin
from subprocess import Popen, PIPE
from xml.dom.minidom import parse, parseString

logger = logging.getLogger('paratest')

class NunitSuites(IPlugin):
    tmp = tempfile.mkdtemp()
    tests_xml = os.path.join(tmp, 'nunit_test_list.xml')
    
    def extract_suites_from_xml(self):
        xml = parse(self.tests_xml)
        for suite in xml.getElementsByTagName('test-suite'):
            #logger.debug("%s / %s ", suite.getAttribute('fullname'), suite.getAttribute('type'))
            if suite.getAttribute('type') == 'TestFixture':
                yield suite.getAttribute('fullname')
    
    def get_suites_for_project(self, path, project):
        cmd = "nunit3-console --explore=%s %s" % (self.tests_xml, project)
        logger.debug("Running on %s: %s", path, cmd)
        result = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, cwd=path)
        stdout, stderr = result.communicate()
        return self.extract_suites_from_xml()
        
    def find_test_projects(self, path, file_pattern):
        c_file_pattern = re.compile(file_pattern)
        for root, _, files in os.walk(path):
            for filename in files:
                absolute = os.path.join(root, filename)
                relative = absolute.replace(path, '').lstrip('\\/')
                if (not file_pattern or c_file_pattern.match(relative)):
                    for suite in self.get_suites_for_project(path, absolute):
                        logger.info("Found suite %s on %s", suite, relative)
                        yield (relative, suite)
    
    def find(self, path, test_pattern, file_pattern, output_path):
        id = 1
        for relative, suite in self.find_test_projects(path, file_pattern):
            cmd = 'nunit3-console --process:Single --result:{out}/{test}_{n}.xml;format=nunit2 {{WORKSPACE}}\\{lib}  --test={test}'.format(lib=relative, test=suite, out=output_path, n=id)
            logger.debug("Adding suite %s with command %s", suite, cmd)
            yield (suite, cmd)
            id += 1
            
        shutil.rmtree(self.tmp)
