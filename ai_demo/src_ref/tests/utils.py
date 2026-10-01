from pipen_cli_run.entry import ENTRY_POINT_GROUP


def plugin_to_entrypoint(plugin):
    class EntryPoint:
        module = plugin
        name = plugin.__name__
        group = ENTRY_POINT_GROUP
        load = lambda x: plugin  # noqa: E731

    return EntryPoint()
