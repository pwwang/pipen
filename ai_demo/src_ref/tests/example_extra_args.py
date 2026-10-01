from pipen import Proc
from pipen_args import ProcGroup, parser


class example_pipeline(ProcGroup):
    """This is a pipeline"""

    @ProcGroup.add_proc
    def p1(self):
        parser.add_argument("--extra")

        parsed, _ = parser.parse_known_args()

        class P1(Proc):
            desc = parsed.extra
            input = "a"
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


if __name__ == "__main__":
    example_pipeline().as_pipen().run()
