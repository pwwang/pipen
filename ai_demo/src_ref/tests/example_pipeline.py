from pipen import Proc
from pipen_args import ProcGroup

some_other_value = 123


class ExampleProcGroup(ProcGroup):
    """This is a pipeline

    Args:
        input (list): The input
    """
    DEFAULTS = {"input": ["100"]}

    @ProcGroup.add_proc
    def p1(self):

        class P1(Proc):
            input = "a"
            input_data = self.opts.input
            output = "outfile:file:out.txt"
            script = "echo {{in.a}} > {{out.outfile}}"

        return P1

    @ProcGroup.add_proc
    def build_p2(self):

        class P2(Proc):
            requires = self.p1
            input = "infile:file"
            output = "outfile:file:out.txt"
            script = (
                "cat {{in.infile}} > {{out.outfile}}; "
                "echo 123 >> {{out.outfile}}"
            )

        return P2


class ExampleProcGroup2(ExampleProcGroup):

    @ProcGroup.add_proc
    def p1(self):

        class P1(Proc):
            input = "a"
            # Avoid adding it as start process
            requires = [Proc]
            output = "outfile:file:out.txt"
            script = "echo {{in.a}} > {{out.outfile}}"

        return P1


if __name__ == "__main__":
    ExampleProcGroup().as_pipen().run()
