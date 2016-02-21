import argparse
import queue
import threading
import logging
from yapsy.PluginManager import PluginManager

logger = logging.getLogger(__name__)
shared_queue = queue.Queue()


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
        default=5,
        help="Number of environments to be created",
    )
    parser.add_argument(
        '-v', '--verbosity',
        action='count',
        default=0,
        help='Increase the verbosity level'
    )

    args = parser.parse_args()
    configure_logging(args.verbosity)
    process(args)


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

        workers = []
        tids = 0
        for tid in po.find(args.path):
            shared_queue.put(tid)
            tids += 1

        for i in range(min(args.environments, tids)):
            t = Worker(po, name=str(i))
            workers.append(t)

        logger.debug("start workers")
        for t in workers:
            t.start()
            shared_queue.put(None)
        logger.debug("wait for all events to be processed")
        shared_queue.join()
        logger.debug("wait for all workers")
        for t in workers:
            t.join()


class Worker(threading.Thread):
    def __init__(self, plugin, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin = plugin

    def run(self):
        logger.debug("%s START" % self.name)
        self.plugin.init_environment(1)
        item = object()
        while item:
            item = shared_queue.get()
            self.process(item)
            shared_queue.task_done()

    def process(self, tid):
        if tid is None:
            return
        try:
            self.plugin.run(tid)
        except Exception as e:
            logger.exception(e)


if __name__ == '__main__':
    main()
