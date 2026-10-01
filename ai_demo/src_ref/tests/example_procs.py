from pipen import Proc


class UndescribedProc(Proc):
    input = "a"


class P1(Proc):
    """The first process

    Input:
        infile: The input file

    Envs:
        a: Environment variable A
    """

    input = "infile:file"
    output = "outfile:file:out.txt"
    envs = {"a": 1}
    plugin_opts = {"a": 2}
    scheduler_opts = {"a": 3}
    script = "cp {{in.infile}} {{out.outfile}}"


class P2(Proc):
    """

    Another process"""

    input = "a"
