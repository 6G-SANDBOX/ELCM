import subprocess
import psutil
import re
from Helper import Level
from Settings import Config, TapConfig
from typing import Dict, Optional, Callable
from time import sleep


class Tap:
    initialized = False
    tapConfig: TapConfig = None
    closingRegex = None

    @classmethod
    def Initialize(cls):
        cls.tapConfig = Config().Tap
        cls.closingRegex = re.compile(r'.*Resource ".*" closed.*')
        cls.initialized = True

    def __init__(self, tapPlan: str, externals: Dict[str, str], logger: Callable):
        if not self.initialized:
            self.Initialize()

        self.tapPlan = tapPlan
        self.externals = externals
        self.args = self.getArgs(tapPlan, externals)
        self.logger = logger
        self.closedInstruments = 0
        self.closeStarted = False
        self.process: Optional[psutil.Process] = None

    @staticmethod
    def getArgs(tapPlan: str, externals: Dict[str, str]):
        if Tap.tapConfig.OpenTap:
            args = [Tap.tapConfig.Path, 'run', '-v']
        else:
            args = [Tap.tapConfig.Path, '-v']

        for key, value in externals.items():
            args.extend(['-e', f'{key}={value}'])

        args.append(tapPlan)

        return args

    def notify(self):
        self.logger(Level.INFO, f'Executing TapPlan: {self.tapPlan}')
        if len(self.externals) != 0:
            for key, value in self.externals.items():
                self.logger(Level.INFO, f'    {key}={value}')

    def Execute(self) -> int:
        self.closedInstruments = 0
        self.closeStarted = False

        self.notify()
        process = subprocess.Popen(self.args, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, cwd=Tap.tapConfig.Folder)
        sleep(0.5)  # Give some time to ensure that psutil finds the process
        self.process = psutil.Process(process.pid)
        self.tap_stdout(process)

        exitCode = process.wait()

        return exitCode

    def tap_stdout(self, process: subprocess.Popen):
        _levels = [('Debug', Level.DEBUG), ('Information', Level.INFO),
                   ('Warning', Level.WARNING), ('Error', Level.ERROR)]

        def _inferLevel(l: str) -> Level:
            for level in _levels:
                string, res = level
                if re.match(rf'.*:\s*{string}\s*:.*', l): return res
            return Level.INFO

        pipe = process.stdout

        for line in iter(pipe.readline, b''):
            try: line = line.decode('utf-8').rstrip()
            except Exception as e: line = f"DECODING EXCEPTION: {e}"

            level = _inferLevel(line)
            self.logger(level, f"[TAP]{line}")

            if self.tapConfig.EnsureClosed:
                if 'Unable to continue. Now exiting TAP CLI' in line:
                    self.closeStarted = True
                    Tap.ensureTapClosed(self.process, self.logger, self.tapConfig.EnsureAdbClosed)

                if Tap.closingRegex.match(line):
                    self.closedInstruments += 1
                    if self.closedInstruments >= 3 and not self.closeStarted:
                        self.closeStarted = True
                        Tap.ensureTapClosed(self.process, self.logger, self.tapConfig.EnsureAdbClosed)

    @staticmethod
    def ensureTapClosed(tapProcess: psutil.Process, logger, closeAdb):
        logger(Level.INFO, 'Ensuring that TAP is correctly closed (in 15 seconds).')
        sleep(15)

        if tapProcess.is_running():
            logger(Level.WARNING, f'TAP still running, stopping child processes '
                  f'({len(tapProcess.children(recursive=True))})...')
            Tap.endProcessTree(tapProcess)
            logger(Level.INFO, 'Process tree closed')
        else:
            logger(Level.INFO, 'TAP closed correctly')

        if closeAdb:
            for p in psutil.process_iter():
                if p.name() == 'adb.exe':
                    logger(Level.WARNING, f"Closing rogue adb process with PID: {p.pid}")
                    p.kill()

    @classmethod
    def endProcessTree(cls, process: psutil.Process):
        def safeTerminate(p: psutil.Process):
            try: p.terminate()
            except psutil.NoSuchProcess: pass

        for child in process.children(recursive=True):  # type: psutil.Process
            safeTerminate(child)
        safeTerminate(process)
