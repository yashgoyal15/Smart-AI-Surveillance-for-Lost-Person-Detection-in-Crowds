"""
One CameraWorker = one camera. It runs two threads:

  reader thread    keeps reading the newest frame and builds the live video image
                   (so the stream stays smooth even when the AI is slow)
  processor thread takes the newest frame every PROCESS_INTERVAL seconds, runs YOLOv8 + ArcFace,
                   asks PostgreSQL "who is this?", and sends an alert when it is a registered person
"""
import os
import threading
import time
import cv2
import config
import matcher
import notifier


class CameraWorker:
    def __init__(self, cam_id, source, pipeline):
        self.cam_id = cam_id
        self.source = source
        self.pipeline = pipeline

        self.running = False
        self.status = "stopped"   # stopped / connecting / online / reconnecting
        self.error = None

        self._frame = None
        self._frame_id = 0
        self._frame_lock = threading.Lock()
        self.detections = []      # what to draw on the video
        self.jpeg = None          # latest annotated frame, ready to stream
        self._last_alert = {}     # person_id -> time of last alert (for the cooldown)

    # ---------------- start / stop ----------------
    def start(self):
        self.running = True
        self.status = "connecting"
        self.error = None
        threading.Thread(target=self._reader_loop, daemon=True).start()
        threading.Thread(target=self._processor_loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.status = "stopped"
        notifier.send_status(self.cam_id, "offline")

    # ---------------- helpers ----------------
    def _open_capture(self):
        src = self.source.strip()
        if src.isdigit():  # webcam number
            index = int(src)
            if os.name == "nt":
                return cv2.VideoCapture(index, cv2.CAP_DSHOW), False  # DSHOW opens Windows webcams faster
            return cv2.VideoCapture(index), False

        path = src if os.path.isabs(src) else os.path.join(config.BASE_DIR, src)
        if os.path.isfile(path):  # video file
            return cv2.VideoCapture(path), True

        return cv2.VideoCapture(src), False  # http:// or rtsp:// stream

    def _shrink(self, frame):
        h, w = frame.shape[:2]
        if w > config.MAX_FRAME_WIDTH:
            scale = config.MAX_FRAME_WIDTH / w
            frame = cv2.resize(frame, (config.MAX_FRAME_WIDTH, int(h * scale)))
        return frame

    def _draw(self, frame):
        """Draws boxes + labels. Green = registered person found, grey = someone else."""
        now = time.time()
        for d in self.detections:
            if now - d["time"] > 1.5:  # box is too old, person probably moved
                continue
            x1, y1, x2, y2 = d["box"]
            color = (80, 200, 60) if d["matched"] else (160, 160, 160)
            thickness = 3 if d["matched"] else 1
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            if d["label"]:
                cv2.rectangle(frame, (x1, y1 - 22), (x1 + 9 * len(d["label"]) + 8, y1), color, -1)
                cv2.putText(frame, d["label"], (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

        cv2.rectangle(frame, (0, 0), (150, 24), (20, 20, 20), -1)
        cv2.putText(frame, f"{self.cam_id}  LIVE", (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        return frame

    # ---------------- reader thread ----------------
    def _reader_loop(self):
        last_encode = 0
        while self.running:
            cap, is_file = self._open_capture()
            if not cap.isOpened():
                self.status = "reconnecting"
                self.error = f"Cannot open source '{self.source}'"
                cap.release()
                time.sleep(3)
                continue

            self.status = "online"
            self.error = None
            notifier.send_status(self.cam_id, "online")

            frame_delay = 1.0 / (cap.get(cv2.CAP_PROP_FPS) or 25) if is_file else 0
            failed_reads = 0

            while self.running:
                started = time.time()
                ok, frame = cap.read()

                if not ok:
                    failed_reads += 1
                    if is_file and failed_reads < 3:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # video ended -> play again from the start
                        continue
                    break  # live stream dropped -> reconnect

                failed_reads = 0
                frame = self._shrink(frame)
                with self._frame_lock:
                    self._frame = frame
                    self._frame_id += 1

                if time.time() - last_encode > 1 / 15:  # stream at most ~15 fps
                    shown = self._draw(frame.copy())
                    ok_jpg, buf = cv2.imencode(".jpg", shown, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ok_jpg:
                        self.jpeg = buf.tobytes()
                    last_encode = time.time()

                if frame_delay:
                    time.sleep(max(0, frame_delay - (time.time() - started)))

            cap.release()
            if self.running:
                self.status = "reconnecting"
                time.sleep(2)

    # ---------------- processor thread ----------------
    def _processor_loop(self):
        last_id = -1
        while self.running:
            with self._frame_lock:
                frame, frame_id = self._frame, self._frame_id
            if frame is None or frame_id == last_id:
                time.sleep(0.05)
                continue
            last_id = frame_id

            started = time.time()
            try:
                self._check_frame(frame.copy())
            except Exception as err:  # keep the camera alive even if one frame fails
                print(f"[{self.cam_id}] frame error: {err}")
                time.sleep(1)

            time.sleep(max(0, config.PROCESS_INTERVAL - (time.time() - started)))

    def _check_frame(self, frame):
        people = self.pipeline.analyse_frame(frame)
        now = time.time()
        drawn = []

        for p in people:
            label, matched = "", False

            if p["embedding"] is not None:
                found = matcher.best_match(p["embedding"])
                if found:
                    person_id, name, similarity = found
                    if similarity >= config.MATCH_THRESHOLD:
                        matched = True
                        label = f"{name} {similarity:.2f}"
                        self._maybe_alert(person_id, similarity, frame, p["box"], now)

            drawn.append({"box": p["box"], "label": label, "matched": matched, "time": now})

        self.detections = drawn

    def _maybe_alert(self, person_id, similarity, frame, box, now):
        """Cooldown: one alert per person per camera every ALERT_COOLDOWN_SECONDS."""
        if now - self._last_alert.get(person_id, 0) < config.ALERT_COOLDOWN_SECONDS:
            return
        self._last_alert[person_id] = now

        x1, y1, x2, y2 = box
        snapshot = frame[max(0, y1):y2, max(0, x1):x2]
        ok, buf = cv2.imencode(".jpg", snapshot, [cv2.IMWRITE_JPEG_QUALITY, 85])
        notifier.send_alert(self.cam_id, person_id, similarity, buf.tobytes() if ok else None)
        print(f"[{self.cam_id}] MATCH person {person_id} score {similarity:.2f}")
