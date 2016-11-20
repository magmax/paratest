import pkg_resources


class PluginException(Exception):
    pass


class PluginNotFoundException(PluginException):
    def __init__(self, plugin, *args, **kwargs):
        super(PluginNotFoundException, self).__init__(*args, **kwargs)
        self.plugin == plugin

    def __str__(self):
        return 'The plugin %s is not available' % self.plugin


class Plugins(object):
    def __init__(self, package='paratest', plugin_path=None):
        self._package = package
        self._plugin_path = plugin_path
        self._plugins = dict()

    def load(self, plugin_name):
        if plugin_name not in self._plugins:
            plugin = self.get_plugin(plugin_name)
            self._plugins[plugin_name] = plugin.load_entry_point(
                self._package, 'find'
            )
        return self._plugins[plugin_name]

    def get_plugin(self, plugin_name):
        for name, plugin in self.plugin_list:
            if name == plugin_name:
                return plugin
        raise PluginNotFoundException(plugin_name)

    @property
    def plugin_list(self):
        dists, errors = pkg_resources.WorkingSet().find_plugins(
            self.plugin_path
        )
        for dist in dists:
            if self._package in dist.get_entry_map():
                name = (
                    dist.project_name[len(self._package) + 1:]
                    if dist.project_name.startswith(self._package)
                    else dist.project_name
                )
                yield name, dist

    @property
    def plugin_path(self):
        return pkg_resources.Environment(self._plugin_path)


def main():
    plugins = Plugins()
    print(plugins.plugin_path)
    print(list(plugins.plugin_list))
    plugin = plugins.load('dummy')
    print(plugin)


if __name__ == '__main__':
    main()
