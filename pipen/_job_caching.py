"""Provide JobCaching class that implements caching for jobs"""

from __future__ import annotations
from typing import TYPE_CHECKING

from diot import Diot
from simpleconf import Config

from .defaults import ProcInputType, ProcOutputType
from .utils import get_mtime, path_is_symlink

if TYPE_CHECKING:
    from xqute.path import SpecPath


class JobCaching:
    """Provide caching functionality of jobs"""

    @property
    def signature_file(self) -> SpecPath:
        """Get the path to the signature file

        Returns:
            The path to the signature file
        """
        return self.metadir / "job.signature.toml"

    async def cache(self) -> None:
        """write signature to signature file"""
        dirsig = (
            self.proc.pipeline.config.dirsig
            if self.proc.dirsig is None
            else self.proc.dirsig
        )
        # Check if mtimes of input is greater than those of output
        try:
            max_mtime = get_mtime(self.script_file, 0)
        except Exception:  # pragma: no cover
            max_mtime = 0

        # Make self.input serializable
        input_data = {}
        for inkey, intype in self.proc.input.type.items():
            if intype == ProcInputType.VAR:
                input_data[inkey] = self.input[inkey]
                continue

            if intype in (ProcInputType.FILE, ProcInputType.DIR):
                if self.input[inkey] is None:
                    input_data[inkey] = None
                else:
                    input_data[inkey] = str(self.input[inkey].spec)
                    max_mtime = max(
                        max_mtime,
                        get_mtime(self.input[inkey].spec, dirsig),
                    )

            if intype in (ProcInputType.FILES, ProcInputType.DIRS):
                if self.input[inkey] is None:  # pragma: no cover
                    input_data[inkey] = None
                else:
                    input_data[inkey] = []
                    for file in self.input[inkey]:
                        input_data[inkey].append(str(file.spec))
                        max_mtime = max(max_mtime, get_mtime(file.spec, dirsig))

        # Make self.output serializable
        output_data = {}
        for outkey, outval in self._output_types.items():
            if outval in (ProcOutputType.FILE, ProcInputType.DIR):
                output_data[outkey] = str(self.output[outkey].spec)
                max_mtime = max(max_mtime, get_mtime(self.output[outkey].spec, dirsig))
            else:
                output_data[outkey] = self.output[outkey]

        signature = {
            "input": {
                "type": self.proc.input.type,
                "data": input_data,
            },
            "output": {"type": self._output_types, "data": output_data},
            "ctime": float("inf") if max_mtime == 0 else max_mtime,
        }
        with self.signature_file.open("w") as f:
            f.write(Diot(signature).to_toml())

    async def _clear_output(self) -> None:
        """Clear output if not cached"""
        self.log("debug", "Clearing previous output files.")
        for outkey, outval in self._output_types.items():
            if outval not in (ProcOutputType.FILE, ProcOutputType.DIR):
                continue

            path = self.output[outkey].spec
            if not path.exists() and path_is_symlink(path):  # dead link
                path.unlink()
            elif path.exists():
                if not path.is_dir():
                    path.unlink()
                else:
                    path.rmtree(ignore_errors=True)
                    path.mkdir()

    async def _check_cached(self) -> bool:
        """Check if the job is cached based on signature

        Returns:
            True if the job is cached otherwise False
        """
        with self.signature_file.open("r") as sf:
            signature = Config.load(sf, loader="toml")

        dirsig = (
            self.proc.pipeline.config.dirsig
            if self.proc.dirsig is None
            else self.proc.dirsig
        )

        try:
            # check if inputs/outputs are still the same
            if (
                signature.input.type != self.proc.input.type
                or signature.output.type != self._output_types
            ):
                self.log("debug", "Not cached (input or output types are different)")
                return False

            # check if any script file is newer
            script_mtime = get_mtime(self.script_file, 0)
            if script_mtime > signature.ctime + 1e-3:
                self.log(
                    "debug",
                    "Not cached (script file is newer: %s > %s)",
                    script_mtime,
                    signature.ctime,
                )
                return False

            # Check if input is different
            for inkey, intype in self.proc.input.type.items():
                sig_indata = signature.input.data.get(inkey)

                if intype == ProcInputType.VAR:
                    if sig_indata != self.input[inkey]:
                        self.log(
                            "debug",
                            "Not cached (input %s:%s is different)",
                            inkey,
                            intype,
                        )
                        return False

                elif int(self.input[inkey] is None) + int(sig_indata is None) == 1:
                    # one is None, the other is not
                    self.log(
                        "debug",
                        "Not cached (input %s:%s is different; "
                        "it is <%s> in signature, but <%s> in data)",
                        inkey,
                        intype,
                        type(sig_indata).__name__,
                        type(self.input[inkey]).__name__,
                    )
                    return False

                elif self.input[inkey] is None and sig_indata is None:
                    continue

                elif intype in (ProcInputType.FILE, ProcInputType.DIR):
                    if sig_indata != str(self.input[inkey].spec):
                        self.log(
                            "debug",
                            "Not cached (input %s:%s is different)",
                            inkey,
                            intype,
                        )
                        return False

                    if (
                        get_mtime(self.input[inkey].spec, dirsig)
                        > signature.ctime + 1e-3
                    ):
                        self.log(
                            "debug",
                            "Not cached (Input file is newer: %s)",
                            inkey,
                        )
                        return False

                # FILES/DIRS

                # self.input[inkey] can't be None with intype files/dirs
                # elif sig_indata is None:  # both None
                #     continue

                elif not isinstance(sig_indata, list):  # pragma: no cover
                    self.log(
                        "debug",
                        "Not cached (input %s:%s is different, "
                        "%s detected in signature)",
                        inkey,
                        intype,
                        type(sig_indata).__name__,
                    )
                    return False

                else:  # both list
                    if len(sig_indata) != len(self.input[inkey]):  # pragma: no cover
                        self.log(
                            "debug",
                            "Not cached (input %s:%s length is different)",
                            inkey,
                            intype,
                        )
                        return False

                    for i, file in enumerate(self.input[inkey]):
                        if sig_indata[i] != str(file.spec):  # pragma: no cover
                            self.log(
                                "debug",
                                "Not cached (input %s:%s at index %s is different)",
                                inkey,
                                intype,
                                i,
                            )
                            return False

                        if get_mtime(file.spec, dirsig) > signature.ctime + 1e-3:
                            self.log(
                                "debug",
                                "Not cached (input %s:%s at index %s is newer)",
                                inkey,
                                intype,
                                i,
                            )
                            return False

            # Check if output is different
            for outkey, outtype in self._output_types.items():
                sig_outdata = signature.output.data.get(outkey)
                if outtype == ProcOutputType.VAR:
                    if sig_outdata != self.output[outkey]:  # pragma: no cover
                        self.log(
                            "debug",
                            "Not cached (output %s:%s is different)",
                            outkey,
                            outtype,
                        )
                        return False

                else:  # FILE/DIR
                    if sig_outdata != str(self.output[outkey].spec):  # pragma: no cover
                        self.log(
                            "debug",
                            "Not cached (output %s:%s is different)",
                            outkey,
                            outtype,
                        )
                        return False

                    if not self.output[outkey].spec.exists():
                        self.log(
                            "debug",
                            "Not cached (output %s:%s was removed)",
                            outkey,
                            outtype,
                        )
                        return False

        except Exception as exc:  # pragma: no cover
            # meaning signature is incomplete
            # or any file is deleted
            self.log("debug", "Not cached (%s)", exc)
            raise
            return False

        return True

    @property
    async def cached(self) -> bool:
        """Check if a job is cached

        Returns:
            True if the job is cached otherwise False
        """
        out = True
        proc_cache = (
            self.proc.pipeline.config.cache
            if self.proc.cache is None
            else self.proc.cache
        )
        if not proc_cache:
            self.log(
                "debug",
                "Not cached (proc.cache is False)",
            )
            out = False
        elif self.rc != 0:
            self.log(
                "debug",
                "Not cached (job.rc != 0)",
            )
            out = False
        elif proc_cache == "force":
            try:
                await self.cache()
            except Exception:  # pragma: no cover
                # FileNotFoundError, google.api_core.exceptions.NotFound, etc
                out = False
            else:
                out = True
        elif not self.signature_file.is_file():
            self.log(
                "debug",
                "Not cached (signature file not found)",
            )
            out = False
        else:
            out = await self._check_cached()

        if not out:
            await self._clear_output()

        return out
