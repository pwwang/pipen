"""An example using python as interpreter for the script"""

from pipen import Pipen, Proc


class PythonScriptProc(Proc):
    """A process using python interpreter for script"""
    input = "a"
    input_data = [1]
    output = "outfile:file:{{in.a}}.txt"
    lang = "python"
    script = """
        from pathlib import Path
        Path("{{out.outfile}}").write_text("{{in.a}}")
    """


if __name__ == "__main__":
    Pipen().set_starts(PythonScriptProc).run()
