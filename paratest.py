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
        '--path',
        default='.',
        help='Path where tests are placed in.',
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
        '-n', '--environments',
        type=int,
        default=5,
        help="Number of environments to be created",
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
    return process(args)


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


def process(args):
    simplePluginManager = PluginManager()
    simplePluginManager.setPluginInfoExtension('paratest')
    simplePluginManager.setPluginPlaces(["plugins", ""])
    simplePluginManager.collectPlugins()

    if args.action == 'plugins':
        msg = "Available plugins are:\n"
        for plugin in simplePluginManager.getAllPlugins():
            msg += "  %s" % plugin.name
        print(msg)
        return

    if args.action == 'run':
        plugin = simplePluginManager.getPluginByName(args.plugin)
        po = plugin.plugin_object

        if run_script(args.setup):
            raise Abort('The setup script failed. aborting.')
        workers = []
        tids = 0
        for tid in po.find(args.path):
            shared_queue.put(tid)
            tids += 1

        for i in range(min(args.environments, tids)):
            t = Worker(
                po,
                setup=args.setup_workspace,
                setup_test=args.setup_test,
                teardown_test=args.teardown_test,
                teardown=args.teardown_workspace,
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
        if run_script(args.teardown):
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
