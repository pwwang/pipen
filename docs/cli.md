`pipen` has a CLI tool that you can run from command line.

To run it:

```
❯ pipen

DESCRIPTION:
  CLI Tool for pipen v0.1.0

USAGE:
  pipen [OPTIONS] COMMAND [OPTIONS]

OPTIONAL OPTIONS:
  -h, --help                      - Print help information for this command

COMMANDS:
  profile                         - List available profiles.
  help                            - Print help of sub-commands
```

## Writing a plugin to extend the cli

### hooks

- `add_commands(params)`

    Add commands and options to the params object. We use [`pyparam`][1] to parse the CLI arguments, see more details on how to add commands/options to `params` object.

- `exec_cmd(command, args)`

    Execute the subcommand with the command and parsed arguments.

    Note that you need to check the `command` to write specific code for that command. You can add and execute multiple commands in a plugin.

### loading CLI plugins

Like pipen [plugins][2], [templates][3], and [schedulers][4], there are two ways to load the CLI plugins:

1. Use the plugin directly:

    ```python
    from pipen.cli import cli_plugin

    cli_plugin.register(<your plugin>)
    ```

2. Use the entry points with group name `pipen-cli`


## The `profile` subcommand

It is used to list the configurations/profiles in current directory. Run `pipen profile` or `pipen help profile` to get more information.


[1]: https://github.com/pwwang/pyparam
[2]: ../plugin
[3]: ../templating
[4]: ../scheduler
