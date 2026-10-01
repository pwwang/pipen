from pipen import Proc
from pipen_args import ProcGroup

some_other_value = 123


class P1(Proc):
    input = "a"
    output = "outfile:file:out.txt"
    script = "echo {{in.a}} > {{out.outfile}}"


class P2(Proc):
    input = "infile:file"
    output = "outfile:file:out.txt"
    script = "cat {{in.infile}} > {{out.outfile}}; echo 123 >> {{out.outfile}}"


class ExampleProcGroup(ProcGroup):
    """This is a process group
    with 2 processes

    Args:
        input (list): The input
    """
    DEFAULTS = {"input": ["100"]}

    @ProcGroup.add_proc
    def p1(self):
        P1.input_data = self.opts.input
        return P1

    @ProcGroup.add_proc
    def p2(self):
        P2.requires = self.p1
        return P2


if __name__ == "__main__":
    ExampleProcGroup().as_pipen().run()
