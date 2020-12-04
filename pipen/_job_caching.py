"""Provide JobCaching class"""
from pathlib import Path

import toml
from diot import Diot
from xqute.utils import a_read_text, a_write_text

from .defaults import ProcInputType, ProcOutputType
from .utils import get_mtime

class JobCaching:
    """Provide caching functionality of jobs"""

    @property
    def signature_file(self) -> Path:
        """Get the path to the signature file"""
        return self.metadir / 'job.signature.toml'

    async def cache(self) -> None:
        """write signature to signature file"""
        max_mtime = 0
        for inkey, intype in self.proc.input.type.items():
            if intype == ProcInputType.VAR:
                continue
            if intype == ProcInputType.FILE and self.input[inkey] is not None:
                max_mtime = max(
                    max_mtime,
                    get_mtime(self.input[inkey], self.proc.dirsig)
                )
            if intype == ProcInputType.FILES:
                for file in (self.input[inkey] or ()):
                    max_mtime = max(
                        max_mtime,
                        get_mtime(file, self.proc.dirsig)
                    )

        for outkey, outval in self._output_types.items():
            if outval == ProcOutputType.FILE:
                max_mtime = max(
                    max_mtime,
                    get_mtime(self.output[outkey], self.proc.dirsig)
                )

        signature = {
            'input': {
                'type': self.proc.input.type,
                'data': self.input,
            },
            'output': {
                'type': self._output_types,
                'data': self.output
            },
            'ctime': float('inf') if max_mtime == 0 else max_mtime
        }
        sign_str = toml.dumps(signature)
        await a_write_text(self.signature_file, sign_str)

    @property
    async def cached(self) -> bool:
        """check if a job is cached"""
        if (not self.proc.cache or
                await self.rc != 0 or
                not self.signature_file.is_file()):
            self.log('debug',
                     'Not cached (proc.cache=False or job.rc!=0 or '
                     'signature file not found)')
            return False

        if self.proc.cache == 'force':
            await self.cache()
            return True

        sign_str = await a_read_text(self.signature_file)
        signature = Diot(toml.loads(sign_str))

        try:
            # check if inputs/outputs are still the same
            if (signature.input.type != self.proc.input.type or
                    signature.input.data != self.input or
                    signature.output.type != self._output_types or
                    signature.output.data != self.output):
                self.log('debug',
                         'Not cached (input or output is different)')
                return False

            # check if any script file is newer
            if self.script_file.stat().st_mtime > signature.ctime:
                self.log('debug',
                         'Not cached (script file is newer)')
                return False

            for inkey, intype in self.proc.input.type.items():
                if intype == ProcInputType.VAR:
                    continue
                if intype == ProcInputType.FILE:
                    if get_mtime(self.input[inkey],
                                 self.proc.dirsig) > signature.ctime + 1e-3:
                        self.log('debug',
                                 'Not cached (Input file is newer: %s)',
                                 inkey)
                        return False
                if intype == ProcInputType.FILES:
                    for file in self.input[inkey]:
                        if get_mtime(file,
                                     self.proc.dirsig) > signature.ctime + 1e-3:
                            self.log(
                                'debug',
                                'Not cached (One of the input files is newer: '
                                '%s)',
                                inkey
                            )
                            return False

            for outkey, outval in self._output_types.items():
                if outval != ProcOutputType.FILE:
                    continue
                if get_mtime(self.output[outkey],
                             self.proc.dirsig) > signature.ctime + 1e-3:
                    self.log('debug',
                             'Not cached (Output file is newer: %s)',
                             outkey)
                    return False

        except (AttributeError, FileNotFoundError): # pragma: no cover
            # meaning signature is incomplete
            # or any file is deleted
            return False

        return True
