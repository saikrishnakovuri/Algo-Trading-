import os
import sys
import logging
import time

logger = logging.getLogger(__name__)

def check_pid_lock(lock_name: str):
    """
    REQ 25a-8: Ensures only one instance of a script is running using an atomic PID file.
    Includes heartbeat logic to handle stale locks.
    """
    lock_file = f"{lock_name}.pid"
    
    try:
        # Atomic O_EXCL open (REQ 25a-8)
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, 'w') as f:
            f.write(f"{os.getpid()}|{int(time.time())}")
    except FileExistsError:
        # Lock exists, check if stale or alive
        try:
            with open(lock_file, "r") as f:
                content = f.read().strip()
                old_pid, last_heartbeat = map(int, content.split('|'))
            
            # Check heartbeat (5 min stale = dead)
            if (time.time() - last_heartbeat) > 300:
                logger.warning(f"Stale lock found for {lock_name} (heartbeat > 5min). Taking over.")
                os.remove(lock_file)
                return check_pid_lock(lock_name) # Retry
                
            # Check if process is still running
            is_alive = False
            if os.name == 'nt':
                import ctypes
                handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, old_pid)
                if handle:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    is_alive = True
            else:
                try:
                    os.kill(old_pid, 0)
                    is_alive = True
                except ProcessLookupError:
                    is_alive = False

            if is_alive:
                logger.error(f"Process {lock_name} is already running (PID {old_pid})")
                sys.exit(1)
            else:
                os.remove(lock_file)
                return check_pid_lock(lock_name)
        except Exception as e:
            logger.error(f"Error checking existing lock: {e}")
            sys.exit(1)

    # Register heartbeat and cleanup
    import atexit
    def remove_lock():
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except: pass
    atexit.register(remove_lock)

def update_heartbeat(lock_name: str):
    """REQ 25a-8: Updates the heartbeat timestamp in the lock file."""
    lock_file = f"{lock_name}.pid"
    try:
        with open(lock_file, "w") as f:
            f.write(f"{os.getpid()}|{int(time.time())}")
    except: pass
