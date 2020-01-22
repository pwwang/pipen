import time
import pytest
from pathlib import Path
from os import path, utime
from diot import Diot, OrderedDiot
from simpleconf import Config
import cmdy
from pyppl.config import config
from pyppl.runner import use_runner
from pyppl.job import Job
from pyppl._job import RC_NO_RCFILE, _link_infile
from pyppl.proc import Proc
from pyppl.utils import fs, filesig
from pyppl.exception import JobInputParseError, JobOutputParseError


@pytest.fixture
def proc_factory(tmp_path):
    def wrapper(id='p', **kwargs):
        runtime_config = Config()
        runtime_config._load(config)
        runtime_config.pop('logger', None)
        runtime_config.pop('plugins', None)
        configs = Diot(
            input={'a': [1]},
            output='out:var:1',
        )
        configs.update(kwargs)
        if 'workdir' not in configs:
            configs.workdir = tmp_path.joinpath(id)
        ret = Proc(id, **configs)
        ret.runtime_config = runtime_config
        return ret

    return wrapper


def test_init(proc_factory, caplog):
    use_runner('local')
    proc = proc_factory('pInit')
    job = Job(0, proc)
    assert job.runner == 'local'
    assert job.dir.resolve() == proc.workdir.joinpath('1').resolve()
    assert job.input == {'a': ('var', 1)}
    assert job.output == {'out': ('var', '1')}
    assert job.script == [str(job.dir / 'job.script.local')]
    assert job.rc == RC_NO_RCFILE
    assert job.script_parts == {
        'command':
        ['{0}/job.script \\\n'.format(job.dir) +
         '        1> "$jobdir/job.stdout" \\\n'
         '        2> "$jobdir/job.stderr"\n'
         '        '],
        'header':
        '',
        'post':
        '',
        'pre':
        '',
        'saveoe':
        True
    }
    assert job.signature.i == {'a:var': '1'}
    assert job.signature.o == {'out:var': '1'}
    assert job.pid == ''
    assert job.config == {}

    job.logger('HAHA', level='INFO', pbar=True)
    assert 'pInit: [1/1] HAHA' in caplog.text


def test_link_infile(proc_factory, tmp_path):
    proc = proc_factory('pLinkInfile')
    job = Job(0, proc)
    # clear up the input directory
    fs.mkdir(job.dir / 'input', overwrite=True)
    infile1 = tmp_path / 'indir1' / 'test_link_infile.infile.txt'
    infile1.parent.mkdir()
    infile1.write_text('')
    assert _link_infile(
        infile1,
        job.dir / 'input') == job.dir / 'input' / 'test_link_infile.infile.txt'

    # rename existing file with same name
    infile2 = tmp_path / 'indir2' / 'test_link_infile.infile.txt'
    infile2.parent.mkdir()
    infile2.write_text('')
    assert _link_infile(
        infile2, job.dir /
        'input') == job.dir / 'input' / '[1]test_link_infile.infile.txt'
    # do it again and it will detect infile2 and [1]... are the same file
    assert _link_infile(
        infile2, job.dir /
        'input') == job.dir / 'input' / '[1]test_link_infile.infile.txt'

    # if a malformat file exists
    (job.dir / 'input' / '[a]test_link_infile.infile.txt').write_text('')
    infile3 = tmp_path / 'indir3' / 'test_link_infile.infile.txt'
    infile3.parent.mkdir()
    infile3.write_text('')
    assert _link_infile(
        infile3, job.dir /
        'input') == job.dir / 'input' / '[2]test_link_infile.infile.txt'


def test_dir(proc_factory):
    proc = proc_factory('pDir')
    job = Job(0, proc)
    assert job.dir.is_dir()


def test_input(tmp_path, proc_factory, caplog):
    infile1 = tmp_path / 'test_prepinput.txt'
    infile1.write_text('')
    infile2 = tmp_path / 'renaming' / 'test_prepinput.txt'
    infile2.parent.mkdir()
    infile2.write_text('')
    proc = proc_factory('pInput',
                        input={
                            'invar:var': ['abc'],
                            'infile      :file ': [infile1],
                            'infiles     :files': [[infile1]],
                            'emptyfile   :file ': [''],
                            'emptyfiles  :files': [['']],
                            'renamed     :file ': [infile2],
                            'nodatafiles :files': [[]],
                            'renamedfiles:files': [[infile2]],
                        })
    job = Job(0, proc)
    assert len(job.input) == 9
    assert job.input['a'] == ('var', 1)
    assert job.input['invar'] == ('var', 'abc')
    assert job.input['infile'] == ('file',
                                   str(job.dir / 'input' /
                                       'test_prepinput.txt'))
    assert job.input['infiles'] == ('files', [
        str(job.dir / 'input' / 'test_prepinput.txt')
    ])
    assert job.input['emptyfile'] == ('file', '')
    assert job.input['emptyfiles'] == ('files', [''])
    assert job.input['renamed'] == ('file',
                                    str(job.dir / 'input' /
                                        '[1]test_prepinput.txt'))
    assert job.input['nodatafiles'] == ('files', [])
    assert job.input['renamedfiles'] == ('files', [
        str(job.dir / 'input' / '[1]test_prepinput.txt')
    ])
    assert 'pInput: [1/1] Input file renamed: test_prepinput.txt -> [1]test_prepinput.txt' in caplog.text
    assert 'No data provided for [nodatafiles:files], use empty list instead.' in caplog.text


@pytest.mark.parametrize('input, error', [
    ({
        'infile:file': [[]]
    }, 'Not a string or path for input [infile:file]'),
    ({
        'nefile:file': ['__nonexist_file__']
    }, 'File not exists for input [nefile:file]'),
    ({
        'nlfile:files': [1]
    }, 'Not a list for input [nlfile:files]'),
    ({
        'npfiles:files': [[None]]
    }, 'Not a string or path as an element of input [npfiles:files]'),
    ({
        'nefiles:files': [['__nonexist_file__']]
    }, 'File not exists as an element of input [nefiles:files]'),
])
def test_input_exc(request, tmp_path, proc_factory, input, error):
    infile1 = tmp_path / 'test_prepinput_not_exists.txt'
    proc = proc_factory(request.node.name, input=input)
    with pytest.raises(JobInputParseError) as exc:
        Job(0, proc).input
    assert error in str(exc.value)


def test_output(proc_factory):
    proc = proc_factory('pOutput1', output='a:var')
    job = Job(0, proc)
    assert len(job.output) == 1

    proc = proc_factory('pOutput2',
                        output='out:var:abc, outfile:file:outfile0.txt')
    job = Job(0, proc)
    assert len(job.output) == 2
    assert job.output.out == ('var', 'abc')
    assert job.output.outfile == ('file', job.dir / 'output/outfile0.txt')

    proc.output = 'abs:file:/a/b/c'
    del job.__attrs_property_cached__['output']
    with pytest.raises(JobOutputParseError) as exc:
        job.output
    assert "Absolute path not allowed for [abs:file]: '/a/b/c'" in str(
        exc.value)


def test_output_empty(tmp_path):
    proc = Proc('pOutput3', workdir=tmp_path.joinpath('pOutput3'))
    job = Job(0, proc)
    assert job.output == {}


def test_script(tmp_path, proc_factory):
    proc = proc_factory('pScript', script="# python script")
    job = Job(0, proc)

    job.script
    assert (job.dir / 'job.script'
            ).read_text() == "#!%s# python script\n" % cmdy.which('bash')
    assert job.dir.joinpath('job.script.local').is_file()


def test_signature_input(tmp_path, proc_factory):
    proc = proc_factory('pSignature')
    job = Job(0, proc)

    # empty because of script
    fs.remove(job.dir / 'job.script')
    assert job.signature == {
        'i': {
            'a:var': '1'
        },
        'mtime': 0,
        'o': {
            'out:var': '1'
        }
    }

    (job.dir / 'job.script').write_text('')
    job.signature = ''  # clear cache
    assert job.signature.mtime == filesig(job.dir / 'job.script')[1]

    infile = tmp_path / 'test_signature_input.txt'
    infile.write_text('')
    infile1 = tmp_path / 'test_signature_input_not_exists.txt'
    # normal signature
    proc = proc_factory('pSignature2',
                        input={
                            'invar:var': ['abc'],
                            'infile:file': [infile],
                            'infiles:files': [[infile]]
                        })
    job = Job(0, proc)
    (job.dir / 'job.script').write_text('')
    assert job.signature.i == {
        'a:var': '1',
        'infile:file': str(job.dir / 'input' / infile.name),
        'infiles:files': [str(job.dir / 'input' / infile.name)],
        'invar:var': 'abc'
    }

    # empty because of input file
    proc = proc_factory('pSignature3',
                        input={
                            'invar:var': ['abc'],
                            'infile:file': [infile1],
                        })
    infile1.write_text('')
    job = Job(0, proc)
    (job.dir / 'job.script').write_text('')
    job.signature = ''
    job.input
    infile1.unlink()
    assert job.signature.i == {'a:var': '1', 'invar:var': 'abc'}
    assert job.signature.o == {'out:var': '1'}
    assert job.signature.mtime > 0

    # empty because of one of input files
    proc = proc_factory('pSignature4',
                        input={
                            'invar:var': ['abc'],
                            'infiles:files': [[infile1]],
                        })
    infile1.write_text('')
    job = Job(0, proc)
    (job.dir / 'job.script').write_text('')
    job.signature = ''
    job.input
    infile1.unlink()
    assert job.signature.i == {
        'a:var': '1',
        'infiles:files': [],
        'invar:var': 'abc'
    }
    assert job.signature.o == {'out:var': '1'}
    assert job.signature.mtime > 0


def test_signature_output(tmp_path, proc_factory):
    # normal signature with output
    outfile = tmp_path / 'test_signature_outfile.txt'
    outdir = tmp_path / 'test_signature_outdir'

    proc = proc_factory('pSignature5',
                        output=[
                            'out:var:abc',
                            'outfile:file:%s' % outfile.name,
                            'outdir:dir:%s' % outdir.name,
                        ])
    job = Job(0, proc)
    (job.dir / 'job.script').write_text('')
    outfile = job.dir / 'output' / outfile.name
    outdir = job.dir / 'output' / outdir.name
    outdir.mkdir(exist_ok=True, parents=True)
    outfile.write_text('')
    assert job.signature.o == {
        'out:var': 'abc',
        'outdir:dir': str(outdir),
        'outfile:file': str(outfile)
    }

    # Empty signature because of output file
    proc = proc_factory('pSignature6',
                        output=[
                            'out:var:abc',
                            'outfile:file:%s' % outfile.name,
                            'outdir:dir:%s' % outdir.name,
                        ])
    job = Job(0, proc)
    assert job.signature.i == {'a:var': '1'}
    assert job.signature.mtime == 0
    assert job.signature.o == {'out:var': 'abc'}

    # Empty signature because of output dir
    proc = proc_factory('pSignature7',
                        output=[
                            'out:var:abc',
                            'outdir:dir:%s' % outdir.name,
                        ])
    job = Job(0, proc)
    assert job.signature.i == {'a:var': '1'}
    assert job.signature.mtime == 0
    assert job.signature.o == {'out:var': 'abc'}


def test_rc(proc_factory):
    job = Job(0, proc_factory('pRC1'))
    job.rc = None
    assert job.rc == RC_NO_RCFILE

    del job.rc
    job.rc = ''
    assert job.rc == RC_NO_RCFILE

    del job.rc
    job.rc = 'None'
    assert job.rc == RC_NO_RCFILE

    del job.rc
    job.rc = '0'
    assert job.rc == 0


def test_data(proc_factory):
    proc = proc_factory('pData')
    job = Job(0, proc)

    assert job.data.job.index == 0
    assert job.data.job.indir == str(job.dir / 'input')
    assert job.data.job.outdir == str(job.dir / 'output')
    assert job.data.job.dir == str(job.dir)
    assert job.data.job.outfile == str(job.dir / 'job.stdout')
    assert job.data.job.errfile == str(job.dir / 'job.stderr')
    assert job.data.job.pidfile == str(job.dir / 'job.pid')
    assert job.data.job.cachedir == str(job.dir / 'output/.jobcache')
    assert job.data.i == {}
    assert job.data.o == {}
    assert job.data.proc is job.proc

    job.input
    assert job.data.i == {'a': 1}
    job.output
    assert job.data.o == {'out': str(job.dir / 'output/1')}


def test_script_parts(proc_factory):
    proc = proc_factory('pScriptParts')
    job = Job(0, proc)

    assert job.script_parts == {
        'pre': '',
        'post': '',
        'header': '',
        'saveoe': True,
        'command': [str(job.dir / 'job.script')]
    }
    assert job.dir.joinpath('job.script').is_file()
    assert not job.dir.joinpath('job.script._bak').is_file()

    job.dir.joinpath('job.script').write_text('hello world')
    job.script_parts = ''
    assert job.script_parts == {
        'pre': '',
        'post': '',
        'header': '',
        'saveoe': True,
        'command': [str(job.dir / 'job.script')]
    }
    assert job.dir.joinpath('job.script._bak').is_file()

    # try to cover when command is a string
    job.script = ''
    job.script_parts['command'] = job.script_parts['command'][0]
    job.script


def test_pid(proc_factory):
    proc = proc_factory('pPid')
    job = Job(0, proc)

    assert job.pid == ''

    del job.pid
    job.pid = 'abc'
    assert job.pid == 'abc'

    del job.pid
    job.pid = ''
    assert job.pid == ''

    job.dir.joinpath('job.pid').unlink()
    del job.pid
    job.pid = None
    assert job.pid == ''


# end of _job tests


def test_add_config(proc_factory):
    job = Job(0, proc_factory('pAddConfig'))
    job.add_config('a')
    assert job.config.a == None

    job.add_config('b', converter=str)
    assert job.config.b == 'None'


def test_is_cached(proc_factory, caplog):
    job = Job(0, proc_factory('pIsCached'))
    assert not job.is_cached()

    job.rc = 0
    job.cache()
    assert job.dir.joinpath('job.cache').is_file()
    assert job.is_cached()

    job.dir.joinpath('job.script').write_text('')
    job.signature = ''
    assert job.signature.mtime > 0
    assert not job.is_cached()
    assert 'Input or script has been modified' in caplog.text
    caplog.clear()

    job.cache()
    assert job.is_cached()

    job.__attrs_property_cached__['input'] = {'a': ('var', 2)}
    job.signature = ''
    assert not job.is_cached()
    assert "Input item 'a:var' changed: 1 -> 2" in caplog.text
    caplog.clear()

    job.cache()
    assert job.is_cached()

    job.__attrs_property_cached__['input'] = {'a': ('var', 2), 'b': ('var', 3)}
    job.signature = ''
    assert not job.is_cached()
    assert "Additional input items found: ['b:var']" in caplog.text
    caplog.clear()

    job.cache()
    assert job.is_cached()

    del job.__attrs_property_cached__['input']['b']
    job.signature = ''
    assert not job.is_cached()
    assert "Missing input items: ['b:var']" in caplog.text
    caplog.clear()

    # output
    job.cache()
    assert job.is_cached()

    del job.__attrs_property_cached__['output']['out']
    job.signature = ''
    assert not job.is_cached()
    assert "Missing output items: ['out:var']" in caplog.text
    caplog.clear()

    job.cache()
    assert job.is_cached()

    job.__attrs_property_cached__['output'] = {'out': ('var', 9)}
    job.signature = ''
    assert not job.is_cached()
    assert "Additional output items found: ['out:var']" in caplog.text

    job.cache()
    assert job.is_cached()

    # without job.cache file
    job.dir.joinpath('job.cache').unlink()
    assert job.is_cached()
    job.cache()

    caplog.clear()
    job.signature = ''
    job.__attrs_property_cached__['output'] = {'out': ('var', 10)}
    assert not job.is_cached()
    assert "Output item 'out:var' changed: 9 -> 10" in caplog.text


def test_is_cached_without_cachefile(proc_factory, tmp_path):
    infile = tmp_path / 'test_is_cached_without_cachefile.txt'
    infile.write_text('')
    outfile = tmp_path / 'test_is_cached_without_cachefile_out.txt'
    outfile.write_text('')

    proc = proc_factory(
        'pIsCachedWithoutCacheFile',
        input={'infile:file': [infile]},
        output=
        'outfile:file:{{i.infile | __import__("pathlib").Path | .stem}}.txt')
    job = Job(0, proc)
    job.rc = 0
    job.input
    Path(job.output['outfile'][1]).write_text('')
    assert job._is_cached_without_cachefile()
    print(job.signature)
    job.signature = ''
    utime(infile, (path.getmtime(infile) + 100, ) * 2)
    print(job.signature)
    assert not job._is_cached_without_cachefile()


def test_build(proc_factory):
    job = Job(0, proc_factory('pBuild', cache=True, script='# script'))
    fs.remove(job.dir)
    assert job.build()
    assert fs.isdir(job.dir)
    assert not fs.exists(job.dir / 'job.stdout.bak')
    assert not fs.exists(job.dir / 'job.stderr.bak')

    (job.dir / 'job.stdout').write_text('')
    (job.dir / 'job.stderr').write_text('')
    assert job.build()
    assert fs.exists(job.dir / 'job.stdout.bak')
    assert fs.exists(job.dir / 'job.stderr.bak')
    fs.remove(job.dir / 'job.stderr')
    fs.remove(job.dir / 'job.stdout')
    job.rc = 0
    job.cache()
    assert job.build()
    assert fs.isfile(job.dir / 'job.stderr')
    assert fs.isfile(job.dir / 'job.stdout')

    job.signature = ''
    job.rc = 0
    job.cache()
    assert job.build() == 'cached'

    # raise exception while building
    old_exists = fs.exists
    del fs.exists
    assert not job.build()
    assert 'AttributeError' in (job.dir / 'job.stderr').read_text()
    fs.exists = old_exists


def test_done(proc_factory, caplog):
    job = Job(0, proc_factory('pDone', cache=True))
    job.rc = 0
    job.done()
    assert job.is_succeeded()
    assert job.is_cached()
    assert 'Finishing up the job' in caplog.text


def test_reset(proc_factory):
    job = Job(0, proc_factory('pReset', cache=True))
    job.ntry = 0
    (job.dir / 'output').mkdir()
    (job.dir / 'output' / 'outfile.txt').write_text('')
    (job.dir / 'output' / '.jobcache').mkdir()
    (job.dir / 'job.rc').write_text('')
    (job.dir / 'job.stdout').write_text('out')
    (job.dir / 'job.stderr').write_text('err')
    (job.dir / 'job.pid').write_text('')
    (job.dir / 'retry.1').mkdir()
    job.reset()
    assert not fs.exists(job.dir / 'retry.1')
    assert not fs.exists(job.dir / 'job.rc')
    # recreated
    assert (job.dir / 'job.stdout').read_text() == ''
    assert (job.dir / 'job.stderr').read_text() == ''
    assert not fs.exists(job.dir / 'job.pid')
    assert fs.exists(job.dir / 'output')
    # recreated
    assert not fs.exists(job.dir / 'output' / 'outfile.txt')

    job.ntry = 1
    (job.dir / 'output' / 'outfile.txt').write_text('')
    (job.dir / 'output' / '.jobcache' / 'cached.txt').write_text('')
    job.reset()
    assert fs.exists(job.dir / 'retry.1')
    assert not fs.exists(job.dir / 'retry.1' / '.jobcache')
    assert fs.exists(job.dir / 'output' / '.jobcache' / 'cached.txt')

    # remove whole output directory
    job.ntry = 0
    fs.remove(job.dir / 'output' / '.jobcache')
    (job.dir / 'output' / 'outfile.txt').write_text('')
    job.reset()
    assert not fs.exists(job.dir / 'output' / 'outfile.txt')
    # move whole output directory
    job.ntry = 1
    fs.remove(job.dir / 'output' / '.jobcache')
    (job.dir / 'output' / 'outfile.txt').write_text('')
    job.reset()
    assert not fs.exists(job.dir / 'output' / 'outfile.txt')

    # restore output directory and stdout, stderr
    job.__attrs_property_cached__['output'] = OrderedDiot(
        outdir=('dir', job.dir / 'output' / 'outdir'),
        outfile=('stdout', job.dir / 'output' / 'outfile'),
        errfile=('stderr', job.dir / 'output' / 'errfile'),
    )
    job.ntry = 0
    job.reset()
    assert fs.isdir(job.dir / 'output' / 'outdir')
    assert fs.islink(job.dir / 'output' / 'outfile')
    assert fs.islink(job.dir / 'output' / 'errfile')
    assert fs.samefile(job.dir / 'job.stdout', job.dir / 'output' / 'outfile')
    assert fs.samefile(job.dir / 'job.stderr', job.dir / 'output' / 'errfile')

    # what if outdir exists
    job.reset()


def test_submit(proc_factory, caplog):
    job = Job(0, proc_factory('pSubmit'))
    assert job.submit()
    assert 'Submitting the job' in caplog.text


def test_poll(proc_factory, caplog):
    job = Job(0, proc_factory('pPoll'))
    assert job.poll() == 'running'
    assert 'Polling the job ... stderr/out file not generared.' in caplog.text
    caplog.clear()

    job.dir.joinpath('job.stdout').write_text('')
    job.dir.joinpath('job.stderr').write_text('')
    assert job.poll() == 'running'
    assert 'Polling the job ... rc file not generated.' in caplog.text
    caplog.clear()

    job.rc = 0
    assert job.poll()
    assert 'Polling the job ... done.' in caplog.text


def test_retry(proc_factory, caplog):
    job = Job(0, proc_factory('pRetry'))
    job.proc.errhow = 'ignore'
    assert job.proc.errhow == 'ignore'
    assert job.retry() == 'ignored'

    job = Job(0, proc_factory('pRetry2'))
    job.proc.errhow = 'terminate'
    assert job.retry() == False

    job = Job(0, proc_factory('pRetry3'))
    job.proc.errhow = 'retry'
    job.proc.errntry = 1
    caplog.clear()
    assert job.retry()
    assert job.ntry == 1
    assert 'Retrying 1 out of 1 time(s) ...' in caplog.text

    assert job.retry() == False


def test_kill(proc_factory):
    job = Job(0, proc_factory('pKill'))
    assert not job.kill()
