import threading
import time
import sys
import traceback
import os

# Mocking the Watchdog class from gui.py for isolation test
class Watchdog:
    """
    Background thread that monitors the application's liveness.
    If the worker thread doesn't 'kick' the dog for 5 seconds (SHORTENED FOR TEST), 
    it assumes a hang and dumps a crash log.
    """
    def __init__(self, timeout=5.0):
        self.timeout = timeout
        self._last_kick = time.time()
        self._running = False
        self._monitor_thread = None
        self._triggered = False

    def start(self):
        self._running = True
        self._triggered = False
        self._last_kick = time.time()
        self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._running = False

    def kick(self):
        """Update the last activity timestamp."""
        self._last_kick = time.time()

    def _monitor(self):
        print("WATCHDOG: Started monitoring...")
        while self._running:
            time.sleep(1.0)
            if not self._running: break
            
            delta = time.time() - self._last_kick
            # print(f"DEBUG: Delta {delta:.1f}s")
            
            if delta > self.timeout and not self._triggered:
                self._triggered = True
                self.dump_state()
                print("WATCHDOG: Hang detected! Dumped state.")
                self.stop() # Stop test
                
    def dump_state(self):
        filename = f"test_crash_dump_{int(time.time())}.txt"
        with open(filename, "w") as f:
            f.write(f"TEST Crash Dump - {time.ctime()}\n")
            f.write("="*40 + "\n")
            f.write("Stack Traces:\n")
            for thread_id, frame in sys._current_frames().items():
                f.write(f"\nThread ID: {thread_id}\n")
                traceback.print_stack(frame, file=f)
                f.write("-" * 20 + "\n")
        print(f"WATCHDOG: Created dump file: {filename}")

def worker_thread(watchdog):
    print("WORKER: Starting normal work...")
    # Normal work
    for i in range(3):
        time.sleep(1)
        watchdog.kick()
        print(f"WORKER: Kick {i+1}")
        
    print("WORKER: Simulating HANG (sleeping 10s)...")
    time.sleep(10)
    print("WORKER: Woke up (too late!)")

if __name__ == "__main__":
    print("TEST: Starting Watchdog Isolation Test")
    wd = Watchdog(timeout=3.0) # 3 second timeout
    wd.start()
    
    t = threading.Thread(target=worker_thread, args=(wd,))
    t.start()
    t.join()
    
    print("TEST: Finished.")
