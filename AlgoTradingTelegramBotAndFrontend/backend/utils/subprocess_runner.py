import subprocess
import os
import signal
import psutil

class SubprocessManager:
    _processes = {}

    @classmethod
    def start_process(cls, name, command, cwd=None):
        if name in cls._processes and cls.is_running(name):
            return False, "Process already running"
        
        try:
            # On Windows, we need to handle process groups carefully
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            cls._processes[name] = proc
            return True, f"Started {name} with PID {proc.pid}"
        except Exception as e:
            return False, str(e)

    @classmethod
    def stop_process(cls, name):
        if name not in cls._processes:
            return False, "Process not found"
        
        proc = cls._processes[name]
        try:
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            return True, f"Stopped {name}"
        except Exception as e:
            return False, str(e)

    @classmethod
    def is_running(cls, name):
        if name not in cls._processes:
            return False
        proc = cls._processes[name]
        return proc.poll() is None

    @classmethod
    def get_status(cls, name):
        return "running" if cls.is_running(name) else "stopped"
