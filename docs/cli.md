`pipen` has a CLI tool that you can run from command line.

To run it:

```
❯ pipen

DESCRIPTION:
  CLI Tool for pipen v0.1.4

USAGE:
  pipen [OPTIONS] COMMAND [OPTIONS]

OPTIONAL OPTIONS:
  -h, --help                      - Print help information for the CLI tool.

COMMANDS:
  profile                         - List available profiles.
  plugins                         - List installed plugins
  help                            - Print help for commands
```

## Writing a plugin to extend the cli

### CLI plugin abstract class

A CLI plugin has to be a subclass of `pipen.cli.CLIPlugin`.

A CLI plugin has to define a `name` property, which also is the sub-command of the plugin.

Then a `params` property is also needed to define the commands and arguments of this plugin. To see how to define a `Params` object, see `pyparam`'s [documentation][5].

You may also define a method `parse_args()` to parse CLI arguments by yourself. By default, it just calls `Params.parse()` to parse the arguments.

Finally, define `exec_command()`, which takes the parsed arguments as argument, to execute the command as you wish.

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


[1]: https://github.com/pwwang/pyparam
[2]: ../plugin
[3]: ../templating
[4]: ../scheduler
[5]: https://pwwang.github.io/pyparam
