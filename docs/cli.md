`pipen` has a CLI tool that you can run from command line.

To run it:

```shell
❯ pipen --help
Usage: pipen [-h] {version,profile,plugins,help} ...

CLI Tool for pipen v0.4.2

Optional Arguments:
  -h, --help            show help message and exit

Subcommands:
    version             Print versions of pipen and its dependencies
    profile             List available profiles.
    plugins             List installed plugins
    help                Print help for commands
```

## Writing a plugin to extend the cli

### CLI plugin abstract class

A CLI plugin has to be a subclass of `pipen.cli.CLIPlugin`.

A CLI plugin has to define a `name` property, which also is the sub-command of the plugin.

There are a couple of methods of `pipen.cli.CLIPlugin` to extend for a plugin:

- `__init__(self, parser, subparser)`: initialize the plugin
  It takes the main parser and the subparser of the sub-command as arguments. You can add arguments to the parser or subparser here.
  Check [argx][1] for more information about how to define arguments.

- `parse_args(self, known_parsed, unparsed_argv)`: parse the arguments
  It takes the known parsed arguments and the unparsed argument vector as arguments, allowing
  you to do custom parsing. It should return the parsed arguments.
  By default, `known_parsed` is returned.

- `exec_command(self, args)`: execute the command
  It takes the parsed arguments as argument. It should execute the command as you wish.

### loading CLI plugins

Like pipen [plugins][2], [templates][3], and [schedulers][4], there are two ways to load the CLI plugins:

1. Use the plugin directly:

    ```python
    from pipen.cli import cli_plugin

    cli_plugin.register(<your plugin>)
    ```

2. Use the entry points with group name `pipen_cli`


## The `profile` subcommand

It is used to list the configurations/profiles in current directory. Run `pipen profile` or `pipen help profile` to get more information.

## The `plugins` subcommand

This subcommand is used to list the plugins for `pipen` itself, templates, scheduler and cli. Run `pipen plugins` or `pipen help plugins` to get more information.

## The `version` subcommand

This command prints the versions of `pipen` and its dependencies.

## CLI plugin gallery

- [`pipen-cli-init`][5]: A pipen CLI plugin to create a pipen project (pipeline)
- [`pipen-cli-ref`][6]: Make reference documentation for processes
- [`pipen-cli-require`][7]: A pipen cli plugin check the requirements of a pipeline
- [`pipen-cli-run`][8]: A pipen cli plugin to run a process or a pipeline

[1]: https://github.com/pwwang/argx
[2]: plugin.md
[3]: templating.md
[4]: scheduler.md
[5]: https://github.com/pwwang/pipen-cli-init
[6]: https://github.com/pwwang/pipen-cli-ref
[7]: https://github.com/pwwang/pipen-cli-require
[8]: https://github.com/pwwang/pipen-cli-run
