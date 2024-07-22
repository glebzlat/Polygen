from __future__ import annotations

# import sys
import shutil
import logging
import subprocess as sp

from abc import abstractmethod
from contextlib import AbstractContextManager
from pathlib import Path
from io import StringIO
from typing import Optional

logger = logging.getLogger("polygen.runner")


class RunnerError(Exception):
    """Runner error"""


class Executable():
    def __init__(self, command: str, output_stream=None):
        self.command = command
        self.output_stream = output_stream

        path = shutil.which(command)
        if not path:
            raise RunnerError(f"command {command} not found")

        logger.info("%s found: %s", command, path)
        self.path = Path(path)

    def run(self,
            *args,
            capture_output=True,
            timeout: Optional[float] = None) -> tuple[int, Optional[str]]:
        """Run a command with arguments

        Return process exit code and output as string.

        Kwargs:
            capture_output: Capture process' output
            timeout: Halt the process if timeout expired
        """
        process = sp.Popen(
            [self.path, *args],
            stdout=sp.PIPE,
            stderr=sp.STDOUT,
            encoding="UTF-8"
        )

        output = StringIO() if capture_output else None
        with process.stdout:
            if self.output_stream or capture_output:
                self._log_subprocess_output(process.stdout, output)
        exitcode = process.wait(timeout)

        return exitcode, output.getvalue() if capture_output else None

    def _log_subprocess_output(self, pipe, output):
        for line in iter(pipe.readline, ""):
            if self.output_stream:
                self.output_stream.write(line)
            if output:
                output.write(line)


class RunnerBase(AbstractContextManager):
    """Runner interface

    Runner manages parser source code and binary file. Depending on the
    language, runner may need to manage build system, compile source code,
    etc. Thus, the method of running the parser may be different too.

    Runner implementation must define its dependencies list as a class
    variable `DEPENDENCIES`. These programs are guaranteed to be found
    before any implementation's code is called. Found dependencies are
    accessible through the Runner instance `__getitem__`:

    ```python
    python_exe = self["python3"]
    ```

    Parser source code is guaranteed to placed in `parser_directory`.
    Filenames can be retrieved from CodeGenerator, placed in the same module
    as Runner.
    """

    DEPENDENCIES: list[str]

    def __init__(self):
        self.output_files: Optional[list[Path]] = None
        self.logger = logger
        self._deps: dict[str, Executable] = {}

    def find_deps(self) -> bool:
        for dep in self.DEPENDENCIES:
            path = shutil.which(dep)

            if not path:
                self.logger.error("%s not found", dep)
                return False

            self.logger.info("%s found: %s", dep, path)
            # print the program output to stdout for now
            # self._deps[dep] = Executable(Path(path), output_stream=sys.stdout)
            self._deps[dep] = Executable(Path(path))
        return True

    @abstractmethod
    def setup(self):
        """Prepare parser executable

        Preparation process may involve build system configuration,
        dependency installation and compilation.
        """
        raise NotImplementedError

    @abstractmethod
    def run(self, file: Path) -> tuple[int, str]:
        """Run parser executable with an input file

        Return error code and program output.

        Return:
            error code, output
        """
        raise NotImplementedError

    @abstractmethod
    def setdown(self):
        """Cleanup

        Remove directories, created by the build system, cache, compilation
        artifacts, parser dependencies, etc.
        """
        raise NotImplementedError

    def __enter__(self) -> RunnerBase:
        self.setup()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.setdown()

    def __getitem__(self, key: str) -> Executable:
        return self._deps[key]
