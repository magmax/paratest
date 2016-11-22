import os
import sys
import shutil
import tempfile
import argparse
import threading
import logging
import time
import copy
from subprocess import Popen, PIPE
try:
    import queue
except ImportError:
    import Queue as queue
from .plugins import Plugins
from .persistence import Persistence


logger = logging.getLogger('paratest')
shared_queue = queue.PriorityQueue()
shared_queue_retries = queue.PriorityQueue()
THIS_DIR = os.path.dirname(os.path.realpath(__file__))


class Abort(Exception):
    pass


class Scripts(object):
    setup = None
    setup_workspace = None
    setup_test = None
    teardown_test = None
    teardown_workspace = None
    teardown = None


class Configuration(object):
    scripts = Scripts()
    verbosity = 0
    workers = 1

    source = None
    path_db = None
    project_name = None
    output_path = None
    test_pattern = None

    workspace_path = None

    def load_from(self, config_file):
        with open(config_file) as fd:
            for line in fd.readlines():
                key, value = line.split('=', 1)
                if key.startswith('script.'):
                    setattr(self.scripts, key[len('script.'):], value)
                else:
                    setattr(self, key, value)


def configure_logging(verbosity):
    msg_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    VERBOSITIES = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    level = VERBOSITIES[min(int(verbosity), len(VERBOSITIES) - 1)]
    formatter = logging.Formatter(msg_format)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)


def main():
    parser = argparse.ArgumentParser(description='Run tests in parallel')
    parser.add_argument('action',
                        choices=('plugins', 'run', 'show'),
                        help='Action to perform')
    parser.add_argument(
        '--config',
        help="Allows to select a configuration file that gathers all options.")
    # parser.add_argument(
    #     '--connstr',
    #     help="Connection string to be used.")

    parser.add_argument(
        '--source',
        default='.',
        help='Path to tests',
    )
    parser.add_argument(
        '--project-name',
        dest='project_name',
        default=None,
        help='The project name. Allow to share results between different'
        ' sources. The source by default.')
    parser.add_argument(
        '--path-workspaces',
        dest='workspace_path',
        default=None,
        help='Path where create workers workspaces',
    )
    parser.add_argument(
        '--path-output',
        dest='output_path',
        default='output',
        help='Path where store the output file from tests execution',
    )
    parser.add_argument(
        '--path-db',
        dest='path_db',
        default=os.path.join(os.path.expanduser("~"), 'paratest.db'),
        help="Path to paratest database.",
    )
    parser.add_argument(
        '--test-pattern',
        dest='test_pattern',
        default='',
        help='Pattern to find test files on workspace',
    )
    parser.add_argument(
        '--plugin',
        help='Plugin to be activated',
    )
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=5,
        help="Number of workers to be created (tests in parallel)",
    )
    parser.add_argument(
        '-v', '--verbosity',
        action='count',
        default=0,
        help='Increase the verbosity level'
    )
    parser.add_argument(
        '--setup',
        help='Script to prepare everything;'
        ' it will be run once at the beginning'
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
        help='Script to finalize a workspace; '
        'it will be run once by worker when no more tests are available'
    )
    parser.add_argument(
        '--teardown',
        help='Script to finalize; it will be run once at the end'
    )

    parser.add_argument(
        '--retry',
        default=0,
        type=int,
        help='Times to retry a failing test'
    )

    args = parser.parse_args()
    configure_logging(args.verbosity)

    if False and args.path_db:
        logger.warning(
            'The argument db-path is deprecated. Use --connstr instead'
        )

    config = Configuration()
    config.scripts.setup = args.setup
    config.scripts.setup_workspace = args.setup_workspace
    config.scripts.setup_test = args.setup_test
    config.scripts.teardown_test = args.teardown_test
    config.scripts.teardown_workspace = args.teardown_workspace
    config.scripts.teardown = args.teardown

    config.source = args.source
    config.path_db = args.path_db
    config.project_name = args.project_name
    config.output_path = args.output_path
    config.test_pattern = args.test_pattern
    config.max_retries = args.retry

    config.workspace_path = (
        tempfile.mkdtemp()
        if args.workspace_path is None
        else None
    )
    try:
        process(config, args.action, args.plugin)
    except Abort as e:
        logger.critical(e)
        sys.exit(2)
    finally:
        if args.workspace_path is None:
            shutil.rmtree(config.workspace_path)


def process(config, action, plugin):
    persistence = Persistence(
        config.path_db,
        config.project_name or config.source,
    )
    paratest = Paratest(
        config,
        persistence,
    )

    if action == 'plugins':
        return paratest.list_plugins(config.verbosity > 0)
    elif action == 'run':
        persistence.initialize()
        return paratest.run(plugin)
    elif action == 'show':
        return persistence.show()


class Test(object):
    FINISH = None
    INFINITE = sys.maxsize

    def __init__(self, name, command=FINISH, priority=INFINITE):
        self.name = name
        self.priority = priority
        self.command = command
        self.retries = 0

    def __lt__(self, other):
        return self.priority < other.priority

    @property
    def must_finish(self):
        return self.command is self.FINISH

    def solved_command(self, worker_id, workspace):
        return self.command.format(
            ID=worker_id,
            TID_NAME=self.name,
            WORKSPACE=workspace,
        )

    def __str__(self):
        if self.retries:
            return '%s (retry %s)' % (self.name, self.retries)
        return self.name


def run_script(script, **kwargs):
    if not script:
        return
    for k, v in kwargs.items():
        script = script.replace('{%s}' % k, v)

    logger.info("About to run script $%s", script)

    result = Popen(script, shell=True, stdout=PIPE, stderr=PIPE)
    output, err = result.communicate()

    output = output.decode("utf-8")
    err = err.decode("utf-8")

    if output != '':
        logger.info(output)
    if err != '':
        logger.warning(err)
    return result.returncode


class Paratest(object):
    def __init__(self, config, persistence):
        self._workers = []
        self.config = config
        self.persistence = persistence

        if not os.path.exists(config.source):
            os.makedirs(self.source)
        if not os.path.exists(config.output_path):
            os.makedirs(self.output_path)

    def list_plugins(self, verbose):
        plugins = Plugins()
        plugin_list = list(plugins.plugin_list)
        if len(plugin_list) == 0:
            print('No plugin was found')
            return
        msg = "Available plugins are:\n"
        for name, data in plugin_list:
            msg += (
                "  %s (%s)\n" % (name, data.version)
                if verbose
                else "  %s\n" % name
            )
        print(msg)

    def run(self, plugin_name):
        try:
            plugin = Plugins().load(plugin_name)
            self.run_script_setup()
            test_number = self.queue_tests(plugin)
            self.create_workers(self.num_of_workers(test_number))
            self.start_workers()
            self.wait_workers()
            self.run_script_teardown()
            self.assert_all_messages_were_processed()
            self.assert_all_workers_were_successful()
            logger.info("Finished successfully")
        finally:
            self.print_report()

    def run_script_setup(self):
        if run_script(self.config.scripts.setup,
                      path=self.config.workspace_path):
            raise Abort('The setup script failed. aborting.')

    def run_script_teardown(self):
        if run_script(self.config.scripts.teardown,
                      path=self.config.workspace_path):
            raise Abort('The teardown script failed, but nothing can be done.')

    def queue_tests(self, find):
        tids = 0
        pluginobjs = find(
            self.config.source,
            test_pattern=None,
            file_pattern=self.config.test_pattern,
            output_path=self.config.output_path,
        )
        for test_name, test_cmd in pluginobjs:
            test = Test(
                test_name,
                test_cmd,
                self.persistence.get_priority(test_name),
            )
            shared_queue.put(test)
            tids += 1
        return tids

    def create_workers(self, workers):
        for i in range(workers):
            t = Worker(
                config=self.config,
                persistence=self.persistence,
                name=str(i),
                queue=shared_queue,
            )
            self._workers.append(t)

    def num_of_workers(self, test_number):
        return min(self.config.workers, test_number)

    def start_workers(self):
        logger.debug("start workers")
        for t in self._workers:
            t.start()
            shared_queue.put(Test('finish'))

    def print_report(self):
        msg = 'Global Report:\n'
        durations = {}
        for t in self._workers:
            msg += 'Worker %s\n' % t.name
            durations[t] = 0
            for result in t.report:
                msg += '   %.4fs %s ... %s\n' % (
                    result.duration,
                    result.test,
                    'OK' if result.success else 'FAIL',
                )
                durations[t] += result.duration
        bucklet = max(durations.values()) if durations else 0
        total = bucklet * len(durations)
        msg += "\nIdle time: %.4fs\n" % (total - sum(durations.values()))
        print(msg)

    def wait_workers(self):
        logger.debug("wait for all workers to finish")
        for t in self._workers:
            t.join()

    def assert_all_workers_were_successful(self):
        if any(x.errors for x in self._workers):
            raise Abort('One or more workers failed')

    def assert_all_messages_were_processed(self):
        if not shared_queue.empty():
            raise Abort(
                'There were unprocessed tests, '
                'but all workers are dead. Aborting.'
            )


class Report(object):
    def __init__(self, test, duration, success):
        self.test = copy.copy(test)
        self.duration = duration
        self.success = success


class Worker(threading.Thread):
    def __init__(
            self,
            name,
            config,
            queue,
            persistence,
            *args,
            **kwargs
    ):
        super(Worker, self).__init__(*args, **kwargs)
        self.config = config
        self.persistence = persistence
        self.workspace_path = os.path.join(config.workspace_path, self.name)
        if not os.path.exists(self.workspace_path):
            os.makedirs(self.workspace_path)
        self.errors = None
        self.report = []
        self.queue = queue

    def run(self):
        print("%s START" % self.name)
        logger.debug("%s START" % self.name)
        self.run_script_setup_workspace()
        self.errors = False
        while True:
            self.run_script_setup_test()

            test = self.queue.get()
            if test.must_finish:
                break
            try:
                self.process(test)
            except Exception:
                self.errors = True
                if test.retries < self.config.max_retries:
                    test.retries += 1
                    self.queue.put(test)

            self.queue.task_done()

            self.run_script_teardown_test()
        self.run_script_teardown_workspace()
        logger.info("Worker %s has finished.", self.name)

    def run_script_setup_workspace(self):
        self._run_script(
            self.config.scripts.setup_workspace,
            'Setup workspace failed on worker %s '
            'and could not initialize the environment. Worker is dead'
            % self.name
        )

    def run_script_teardown_workspace(self):
        self._run_script(
            self.config.scripts.teardown_workspace,
            'Teardown workspace failed on worker %s. Worker is dead'
            % self.name
        )

    def run_script_setup_test(self):
        self._run_script(
            self.config.scripts.setup_test,
            "setup_test failed on worker %s. Worker is dead" % self.name
        )

    def run_script_teardown_test(self):
        self._run_script(
            self.config.scripts.teardown_test,
            "teardown_test failed on worker %s. Worker is dead" % self.name
        )

    def _run_script(self, script, message):
        if run_script(
                script,
                id=self.name,
                workspace=self.workspace_path,
                source=self.config.source,
                output=self.config.output_path,
        ):
            raise Abort(message)

    def process(self, test):
        logger.info(
            'Runner {runner} running test {test} on {workspace}.'
            ' {left} tests left'
            .format(
                runner=self.name,
                test=test.name,
                workspace=self.workspace_path,
                left=shared_queue.qsize(),
            )
        )
        try:
            start = time.time()
            self.execute(test)
            duration = time.time() - start
            self.persistence.add(test.name, duration)
            report = Report(test=test, duration=duration, success=True)
        except Exception as e:
            duration = time.time() - start
            logger.error("Suite %s failed due to: %s", test, e)
            report = Report(test=test, duration=duration, success=False)
            raise
        finally:
            self.report.append(report)

    def execute(self, test):
        command = test.solved_command(self.name, self.workspace_path)
        logger.debug("Running command: %s", command)
        result = Popen(
            command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            cwd=self.workspace_path,
        )
        stdout, stderr = result.communicate()
        if stdout:
            logger.debug(stdout.decode("utf-8"))
        if stderr:
            logger.warning(stderr.decode("utf-8"))
        if result.returncode != 0:
            raise Exception(
                "Test %s failed with code %s",
                test.name,
                result.returncode,
            )


if __name__ == '__main__':
    main()
