"""
The Scheduler is the ONE thread that runs the AI for all cameras.

v1: every camera had its own AI thread and all of them waited for one lock -> slow cameras starved the others.
v2: this loop picks the cameras that have a new frame, serves the one that waited LONGEST first (fair),
    sends up to INFERENCE_BATCH frames to YOLO in a single batched call, then lets every camera do its
    own tracking / face / clothes step. Cameras that fall behind simply skip frames (always the newest is used).
"""
import threading
import time
import config


class Scheduler:
    def __init__(self, pipeline, workers):
        self.pipeline = pipeline
        self.workers = workers      # the same dict app.py fills: cam_id -> CameraWorker

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                now = time.time()
                ready = [w for w in list(self.workers.values())
                         if w.has_new_frame() and now - w.last_processed >= config.PROCESS_INTERVAL]
                if not ready:
                    time.sleep(0.03)
                    continue

                ready.sort(key=lambda w: w.last_processed)          # waited longest -> first (fairness)
                batch = ready[: config.INFERENCE_BATCH]
                taken = [w.take_frame() for w in batch]             # [(frame, captured_time), ...]

                started = time.time()
                boxes_per_camera = self.pipeline.detect_batch([f for f, _ in taken])
                for worker, (frame, captured_at), boxes in zip(batch, taken, boxes_per_camera):
                    try:
                        worker.process(frame, boxes, captured_at)
                    except Exception as err:   # one camera's problem must not stop the others
                        print(f"[{worker.cam_id}] frame error: {err}")
                self.pipeline.metrics.add("cycle_ms", (time.time() - started) * 1000)
            except Exception as err:
                print(f"[scheduler] error: {err}")
                time.sleep(1)
