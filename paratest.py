import sys
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


def main():
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
    paratest = Paratest(args.workspaces, scripts, args.source)
    if args.action == 'plugins':
        return paratest.list_plugins()
    if args.action == 'run':
        return paratest.run(args.plugin)
    return paratest.process(args)


def run_script(script):
    if not script:
        return
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
    def __init__(self, workspace_num, scripts, source_path):
        self.workspace_num = workspace_num
        self.scripts = scripts
        self.source_path = source_path
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
        po = plugin.plugin_object

        if run_script(self.scripts.setup):
            raise Abort('The setup script failed. aborting.')
        workers = []
        tids = 0
        for tid in po.find(self.source_path):
            shared_queue.put(tid)
            tids += 1

        for i in range(min(self.workspace_num, tids)):
            t = Worker(
                po,
                setup=self.scripts.setup_workspace,
                setup_test=self.scripts.setup_test,
                teardown_test=self.scripts.teardown_test,
                teardown=self.scripts.teardown_workspace,
                name=str(i),
            )
            workers.append(t)

        logger.debug("start workers")
        for t in workers:
            t.start()
            shared_queue.put(None)
        logger.debug("wait for all workers to finish")
        for t in workers:
            t.join()
        if run_script(self.scripts.teardown):
            raise Abort('The teardown script failed, but nothing can be done.')

        if not shared_queue.empty():
            raise Abort('There were unprocessed tests, but all workers are dead. Aborting.')


class Worker(threading.Thread):
    def __init__(self, plugin, setup, setup_test, teardown, teardown_test, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin = plugin
        self.setup = setup
        self.setup_test = setup_test
        self.teardown = teardown
        self.teardown_test = teardown_test

    def run(self):
        logger.debug("%s START" % self.name)
        self.plugin.init_environment(1)
        item = object()
        if run_script(self.setup):
            raise Abort('Setup workspace failed on worker %s and could not initialize the environment. Worker is dead')
        while item:
            if run_script(self.setup_test):
                raise Abort("setup_test failed on worker %s. Worker is dead", self.name)
            item = shared_queue.get()
            self.process(item)
            shared_queue.task_done()
            if run_script(self.teardown_test):
                raise Abort("teardown_test failed on worker %s. Worker is dead", self.name)
        if run_script(self.teardown):
            raise Abort('Teardown workspace failed on worker %s. Worker is dead')

    def process(self, tid):
        if tid is None:
            return
        try:
            self.plugin.run(tid)
        except Exception as e:
            logger.exception(e)


if __name__ == '__main__':
    try:
        main()
    except Abort as e:
        logger.critical(e)
        sys.exit(2)
