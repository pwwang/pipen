from pathlib import Path
import pytest
from time import sleep
from pipen import Proc, Pipen
from pipen.exceptions import ProcInputTypeError

class Process(Proc):
    input_keys = 'infiles:files, infile:file, indir:file'
    input = [(list(Path(__file__).parent.glob("test_*.py")),
              Path(__file__).parent / 'conftest.py',
              Path(__file__).parent)]
    output = ['outfile:file:f', 'outdir:file:d', 'outvar:x']
    script = ("echo {{in.infiles[0]}} > {{out.outfile}};"
              "echo {{in.infiles[1]}} >> {{out.outfile}};"
              "echo {{in.infiles[2]}} >> {{out.outfile}};"
              "mkdir -p {{out.outdir}}")


def test_caching(tmp_path, caplog):
    proc = Process()
    pipen = Pipen(starts=proc, workdir=tmp_path, loglevel='debug')
    pipen.run()

    # trigger caching
    pipen.run()
    assert caplog.text.count('Not cached') == 1
    caplog.clear()

    # force cache
    jobscript = proc.workdir / '0' / 'job.script'
    jobscript.touch()
    proc.cache = 'force'
    pipen.run()
    assert 'Not cached' not in caplog.text

def test_not_cached(tmp_path, caplog):
    proc1 = Process('proc1')
    pipen = Pipen(starts=proc1, workdir=tmp_path, loglevel='debug')
    pipen.run()

    proc2 = Process('proc1', output=['outfile:file:f', 'outdir:file:d'])
    pipen = Pipen(starts=proc2, workdir=tmp_path, loglevel='debug')
    pipen.run()
    assert 'Not cached (input or output is different)' in caplog.text
    caplog.clear()

    (Path(__file__).parent / 'conftest.py').write_text('')
    pipen.run()
    assert 'Not cached (Input file is newer' in caplog.text
    caplog.clear()

    Path(__file__).touch()
    pipen.run()
    assert 'Not cached (One of the input files is newer' in caplog.text
    caplog.clear()

    sleep(1e-2)
    (Path(pipen.outdir) / proc2.name / 'f').touch()
    pipen.run()
    assert 'Not cached (Output file is newer' in caplog.text
    caplog.clear()

def test_input_type_error():

    class Process2(Proc):
        input_keys = 'infile:file'
        input = [1]

    pipen = Pipen(starts=Process2, loglevel='debug')
    with pytest.raises(ProcInputTypeError):
        pipen.run()

    class Process3(Proc):
        input_keys = 'infiles:files'
        input = [1]

    pipen = Pipen(starts=Process3, loglevel='debug')
    with pytest.raises(ProcInputTypeError):
        pipen.run()

    # not exist
    class Process4(Process2):
        input = ['nosuchfile']

    pipen = Pipen(starts=Process4, loglevel='debug')
    with pytest.raises(FileNotFoundError):
        pipen.run()
    # not exist
    class Process5(Process3):
        input = [['nosuchfile']]

    pipen = Pipen(starts=Process5, loglevel='debug')
    with pytest.raises(FileNotFoundError):
        pipen.run()
