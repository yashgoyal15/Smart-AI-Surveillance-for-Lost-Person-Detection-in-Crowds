"""
One CameraWorker = one camera. v2 changes: it no longer runs its own AI thread.

  reader thread   keeps reading the newest frame and builds the live video image (smooth stream even if AI is slow)
  process()       called by the Scheduler with the newest frame and the people YOLO found in it. It
                    1. tracks people (same id while they move)
                    2. reads faces only for tracks that still need it (new / unconfirmed / every 10 s)
                    3. votes over several frames before calling someone "matched"
                    4. keeps the identity of a confirmed track even when the face turns away (method = track)
                    5. for unconfirmed people compares CLOTHES / height with the reporter's details (POSSIBLE)
"""
import os
import threading
import time
from collections import Counter
import cv2
import config
import matcher
import notifier
import attributes
from tracker import Tracker


def _jpeg(image, quality=85):
    if image is None or image.size == 0:
        return None
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else None


def _crop(frame, box, pad=0.0):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = box
    px, py = int((x2 - x1) * pad), int((y2 - y1) * pad)
    return frame[max(0, y1 - py):min(h, y2 + py), max(0, x1 - px):min(w, x2 + px)]


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
        self._frame_time = 0.0
        self._frame_lock = threading.Lock()
        self._taken_id = -1
        self.last_processed = 0.0

        self.tracker = Tracker()
        self.settings = {"threshold": config.MATCH_THRESHOLD, "calibPxPerCm": None}
        self._settings_time = 0.0
        self.detections = []      # what to draw on the video
        self.jpeg = None          # latest annotated frame, ready to stream

    # ---------------- start / stop ----------------
    def start(self):
        self.running = True
        self.status = "connecting"
        self.error = None
        threading.Thread(target=self._reader_loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.status = "stopped"
        notifier.send_status(self.cam_id, "offline")

    # ---------------- used by the Scheduler ----------------
    def has_new_frame(self):
        return self.running and self._frame is not None and self._frame_id != self._taken_id

    def take_frame(self):
        with self._frame_lock:
            self._taken_id = self._frame_id
            return self._frame.copy(), self._frame_time

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
        """Green = confirmed person, amber = possible (clothes only), grey = someone else."""
        now = time.time()
        colours = {"match": (80, 200, 60), "possible": (0, 170, 255), "other": (160, 160, 160)}
        for d in self.detections:
            if now - d["time"] > 1.5:  # box is too old, person probably moved
                continue
            x1, y1, x2, y2 = d["box"]
            color = colours[d["kind"]]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1 if d["kind"] == "other" else 3)
            if d["label"]:
                cv2.rectangle(frame, (x1, y1 - 22), (x1 + 9 * len(d["label"]) + 8, y1), color, -1)
                cv2.putText(frame, d["label"], (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
            if d.get("info"):
                cv2.putText(frame, d["info"], (x1 + 2, y2 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.rectangle(frame, (0, 0), (150, 24), (20, 20, 20), -1)
        cv2.putText(frame, f"{self.cam_id}  LIVE", (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        return frame

    # ---------------- reader thread ----------------
    def _reader_loop(self):
        last_encode = 0
        while self.running:
            cap, is_file = self._open_capture()
            if not self.running:  # Stop was pressed while we were still trying to connect
                cap.release()
                break
            if not cap.isOpened():
                self.status = "reconnecting"
                message = f"Cannot open source '{self.source}'. Check it (phone and computer on the same Wi-Fi? camera used by another app?)"
                if message != self.error:
                    print(f"[{self.cam_id}] {message}. Retrying every 3 seconds...")
                self.error = message
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
                    self._frame_time = time.time()

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

    # ---------------- AI step (called by the Scheduler) ----------------
    def _refresh_settings(self, now):
        """Per-camera threshold and calibration are read from the database every 10 s (no restart needed)."""
        if now - self._settings_time < 10:
            return
        self._settings_time = now
        found = matcher.get_camera_settings(self.cam_id)
        if found:
            self.settings = found

    def process(self, frame, boxes, captured_at):
        now = time.time()
        self._refresh_settings(now)
        self.last_processed = now
        threshold = self.settings["threshold"]
        calib = self.settings["calibPxPerCm"]

        seen = self.tracker.update(boxes, now)

        # which people still need a face check? new or unconfirmed ones, and confirmed ones every REVERIFY_SECONDS
        def needs_face(t):
            if t.identity is not None:
                return now - t.last_verified > config.REVERIFY_SECONDS
            if t.face_rejected >= 2:   # clearly a stranger: look again only now and then
                return now - t.last_face_check >= config.STRANGER_RECHECK_SECONDS
            return True

        need_face = [(t, b) for t, b in seen if needs_face(t)]
        face_now = {}   # track id -> match result when a usable face matched this frame
        for track, box in need_face:
            result = self._check_face(track, frame, box, threshold, now)
            if result:
                face_now[track.id] = result

        drawn = []
        for track, box in seen:
            attrs = attributes.body_attributes(frame, box)
            height = attributes.estimate_height_cm(box, frame.shape[0], calib)
            info = {
                "upperColor": attrs["upperColor"] if attrs else None,
                "lowerColor": attrs["lowerColor"] if attrs else None,
                "heightCm": height,
                "heightClass": attributes.height_class(height),
                "movement": attributes.movement_class(track.speed),
            }
            track.attrs = attrs
            drawn.append(self._decide(track, box, frame, attrs, info, face_now.get(track.id), height, threshold, captured_at, now))
        self.detections = drawn

    def _check_face(self, track, frame, box, threshold, now):
        """Reads the face of one track. Returns the DB match (dict) when it passed the threshold, else None."""
        track.last_face_check = now
        face = self.pipeline.find_face(frame, box)
        if face is None or face["quality"] < config.QUALITY_MIN_CAMERA:
            return None   # no usable face -> this frame says nothing (it neither votes yes nor no)

        started = time.time()
        match = matcher.match_face(face["embedding"], threshold)
        self.pipeline.metrics.add("match_ms", (time.time() - started) * 1000)

        if face["quality"] >= (track.last_quality or 0):   # keep the best face picture of this track
            track.last_face_jpeg = _jpeg(_crop(frame, face["faceBox"], 0.35))
            track.last_quality = face["quality"]

        if match is None or not match["ok"]:
            track.votes.append(None)
            if match is None or match["similarity"] < threshold - 0.10:
                track.face_rejected += 1     # a good face that is clearly nobody we look for
            return None

        track.votes.append(match["personId"])
        track.vote_sims.append(match["similarity"])
        match["quality"] = face["quality"]

        # track-level voting: enough agreeing frames -> the identity is confirmed
        person_id, count = Counter(v for v in track.votes if v is not None).most_common(1)[0]
        if count >= config.VOTES_REQUIRED and person_id == match["personId"]:
            track.identity = {"personId": person_id, "name": match["name"], "similarity": match["similarity"],
                              "quality": face["quality"]}
            track.last_verified = now
            return match
        return None

    def _decide(self, track, box, frame, attrs, info, face_match, height, threshold, captured_at, now):
        """Chooses the label and sends an alert when needed. Returns what to draw."""
        summary = " ".join(x for x in [
            f"top:{info['upperColor']}" if info["upperColor"] else "",
            f"legs:{info['lowerColor']}" if info["lowerColor"] else "",
            info["movement"] or ""] if x)

        # ---- confirmed identity (by face now, or remembered by the track) ----
        if track.identity:
            ident = track.identity
            method = "face" if face_match else "track"
            if face_match:
                ident["similarity"] = face_match["similarity"]
            if now - track.last_alert.get(("MATCH", ident["personId"]), 0) >= config.ALERT_COOLDOWN_SECONDS:
                track.last_alert[("MATCH", ident["personId"])] = now
                notifier.send_alert(
                    self.cam_id, ident["personId"], ident["similarity"], "MATCH", method, info,
                    attrs["vector"] if (attrs and method == "face") else None,
                    ident.get("quality"), threshold, captured_at,
                    track.last_face_jpeg, _jpeg(_crop(frame, box)))
                self.pipeline.metrics.count("alerts")
                self.pipeline.metrics.add("alert_dispatch_ms", (time.time() - captured_at) * 1000)
                print(f"[{self.cam_id}] MATCH person {ident['personId']} {ident['similarity']:.2f} via {method}")
            tag = "" if method == "face" else " (track)"
            return {"box": box, "kind": "match", "time": now, "label": f"{ident['name']} {ident['similarity']:.2f}{tag}", "info": summary}

        # ---- no confirmed identity: try clothes / height (POSSIBLE only) ----
        if attrs and track.hits >= config.MIN_TRACK_HITS_FOR_POSSIBLE and track.face_rejected < 2:
            cand = matcher.appearance_candidate(attrs, height)
            if cand:
                key = ("POSSIBLE", cand["personId"])
                if now - track.last_alert.get(key, 0) >= config.POSSIBLE_COOLDOWN_SECONDS:
                    track.last_alert[key] = now
                    notifier.send_alert(
                        self.cam_id, cand["personId"], cand["score"], "POSSIBLE", "appearance", info, None,
                        None, config.APPEARANCE_THRESHOLD if cand["basis"] == "learned" else config.DECLARED_COLOUR_THRESHOLD,
                        captured_at, track.last_face_jpeg, _jpeg(_crop(frame, box)))
                    self.pipeline.metrics.count("alerts")
                    print(f"[{self.cam_id}] POSSIBLE person {cand['personId']} clothes {cand['score']:.2f} ({cand['basis']})")
                return {"box": box, "kind": "possible", "time": now, "label": f"? {cand['name']} (clothes)", "info": summary}

        return {"box": box, "kind": "other", "time": now, "label": "", "info": summary}
