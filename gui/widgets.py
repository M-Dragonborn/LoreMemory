import queue
import threading

def run_in_background(root, work, done):
    q = queue.Queue()

    def worker():
        try:
            val = work()
            q.put((val, None))
        except Exception as e:
            q.put((None, str(e)))

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    def check_queue():
        try:
            val, err = q.get_nowait()
            done(val, err)
        except queue.Empty:
            root.after(50, check_queue)

    root.after(50, check_queue)
    return t
