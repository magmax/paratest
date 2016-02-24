import os
import sys
import shutil
import tempfile
import argparse
import queue
import threading
import subprocess
import logging
from yapsy.PluginManager import PluginManager

logger = logging.getLogger(__name__)
shared_queue = queue.Queue()


class Abort(Exception):
    pass


def configure_logging(verbosity):
    VERBOSITIES = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    level = VERBOSITIES[min(int(verbosity), len(VERBOSITIES) -1)]
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)


def main(tmpdir):
    parser = argparse.ArgumentParser(description='Run tests in parallel')
    parser.add_argument('action',
                        choices=('plugins', 'run'),
                        help='Action to perform')
    parser.add_argument(
        '--source',
        default='.',
        help='Path to tests',
    )
    parser.add_argument(
        '--path-workspaces',
        dest='workspace_path',
        default=tmpdir,
        help='Path to search for plugins',
    )
    parser.add_argument(
        '--path-plugins',
        dest='plugins',
        default='plugins',
        help='Path to search for plugins',
    )
    parser.add_argument(
        '--plugin',
        help='Plugin to be activated',
    )
    parser.add_argument(
        '-w', '--workspaces',
        type=int,
        default=5,
        help="Number of workspaces to be created (tests in parallel)",
    )
    parser.add_argument(
        '-v', '--verbosity',
        action='count',
        default=0,
        help='Increase the verbosity level'
    )
    parser.add_argument(
        '--setup',
        help='Script to prepare everything; it will be run once at the beginning'
    )
    parser.add_argument(
        '--setup-workspace',
        dest='setup_workspace',
        help='Script to prepare the workspace; it will be run once by worker',
    )
    parser.add_argument(
        '--setup-test',
        dest='setup_test',
        help='Script to prepare a test; it will be run before each test'
    )
    parser.add_argument(
        '--teardown-test',
        dest='teardown_test',
        help='Script to finalize a test; it will be run after each test'
    )
    parser.add_argument(
        '--teardown-workspace',
        dest='teardown_workspace',
        help='Script to finalize a workspace; it will be run once by worker when no more tests are available'
    )
    parser.add_argument(
        '--teardown',
        help='Script to finalize; it will be run once at the end'
    )

    args = parser.parse_args()
    configure_logging(args.verbosity)
    scripts = Scripts(
        setup=args.setup,
        setup_workspace=args.setup_workspace,
        setup_test=args.setup_test,
        teardown_test=args.teardown_test,
        teardown_workspace=args.teardown_workspace,
        teardown=args.teardown,
    )
    paratest = Paratest(args.workspaces, scripts, args.source, args.workspace_path)
    if args.action == 'plugins':
        return paratest.list_plugins()
    if args.action == 'run':
        return paratest.run(args.plugin)
    return paratest.process(args)


def run_script(script, **kwargs):
    if not script:
        return
    for k, v in kwargs.items():
        script = script.replace('{%s}' % k, v)
    logger.debug("About to run script %s", script)
    result = subprocess.run(script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stdout:
        logger.debug(result.stdout)
    if result.stderr:
        logger.warning(result.stderr)
    return result.returncode


class Scripts(object):
    def __init__(self, setup, setup_workspace, setup_test, teardown_test, teardown_workspace, teardown):
        self.setup = setup
        self.setup_workspace = setup_workspace
        self.setup_test = setup_test
        self.teardown_test = teardown_test
        self.teardown_workspace = teardown_workspace
        self.teardown = teardown


class Paratest(object):
    def __init__(self, workspace_num, scripts, source_path, workspace_path):
        self.workspace_num = workspace_num
        self.workspace_path = workspace_path
        self.scripts = scripts
        self.source_path = source_path
        self._workers = []
        self.pluginmgr = PluginManager()
        self.pluginmgr.setPluginInfoExtension('paratest')
        self.pluginmgr.setPluginPlaces(["plugins", ""])
        self.pluginmgr.collectPlugins()

    def list_plugins(self):
        msg = "Available plugins are:\n"
        for plugin in self.pluginmgr.getAllPlugins():
            msg += "  %s" % plugin.name
        print(msg)


    def run(self, plugin):
        plugin = self.pluginmgr.getPluginByName(plugin)
        pluginobj = plugin.plugin_object

        self.run_script_setup()
        test_number = self.queue_tests(pluginobj)
        self.create_workers(pluginobj, self.num_of_workers(test_number))
        self.start_workers()
        self.wait_workers()
        self.run_script_teardown()
        self.assert_all_messages_were_processed()

    def run_script_setup(self):
        if run_script(self.scripts.setup, path=self.workspace_path):
            raise Abort('The setup script failed. aborting.')

    def run_script_teardown(self):
        if run_script(self.scripts.teardown, path=self.workspace_path):
            raise Abort('The teardown script failed, but nothing can be done.')

    def queue_tests(self, pluginobj):
        tids = 0
        for tid in pluginobj.find(self.source_path):
            shared_queue.put(tid)
            tids += 1
        return tids

    def create_workers(self, pluginobj, workers):
        for i in range(workers):
            t = Worker(
                pluginobj,
                scripts=self.scripts,
                workspace_path=self.workspace_path,
                name=str(i),
            )
            self._workers.append(t)

    def num_of_workers(self, test_number):
        return min(self.workspace_num, test_number)

    def start_workers(self):
        logger.debug("start workers")
        for t in self._workers:
            t.start()
            shared_queue.put(None)

    def wait_workers(self):
        logger.debug("wait for all workers to finish")
        for t in self._workers:
            t.join()

    def assert_all_messages_were_processed(self):
        if not shared_queue.empty():
            raise Abort('There were unprocessed tests, but all workers are dead. Aborting.')


class Worker(threading.Thread):
    def __init__(self, plugin, scripts, workspace_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin = plugin
        self.scripts = scripts
        self.workspace_path = os.path.join(workspace_path, self.name)

    def run(self):
        logger.debug("%s START" % self.name)
        self.plugin.init_environment(self.name, self.workspace_path)
        item = object()
        self.run_script_setup_workspace()
        while item:
            self.run_script_setup_test()

            item = shared_queue.get()
            self.process(item)
            shared_queue.task_done()

            self.run_script_teardown_test()
        self.run_script_teardown_workspace()

    def run_script_setup_workspace(self):
        self._run_script(
            self.scripts.setup_workspace,
            'Setup workspace failed on worker %s and could not initialize the environment. Worker is dead' % self.name
        )

    def run_script_teardown_workspace(self):
        self._run_script(
            self.scripts.teardown_workspace,
            'Teardown workspace failed on worker %s. Worker is dead' % self.name
        )

    def run_script_setup_test(self):
        self._run_script(
            self.scripts.setup_test,
            "setup_test failed on worker %s. Worker is dead" % self.name
        )

    def run_script_teardown_test(self):
        self._run_script(
            self.scripts.teardown_test,
            "teardown_test failed on worker %s. Worker is dead" % self.name
        )

    def _run_script(self, script, message):
        if run_script(script, workspace=self.name, path=self.workspace_path):
            raise Abort(message)

    def process(self, tid):
        if tid is None:
            return
        try:
            self.plugin.run(tid)
        except Exception as e:
            logger.exception(e)


if __name__ == '__main__':
    tmpdir = tempfile.mkdtemp()
    try:
        main(tmpdir)
    except Abort as e:
        logger.critical(e)
        sys.exit(2)
    finally:
        shutil.rmtree(tmpdir)
