"""
A very small IoU tracker. It keeps the same id for the same person while they move through one camera view,
so we can (1) vote over several frames, (2) remember "this track is Rahul" even when his face turns away,
and (3) measure how fast he moves.

IoU = overlap area / combined area of two boxes. A new box that overlaps an old track a lot is the same person.
Greedy matching is enough for 4 cameras with a handful of people; it can swap ids in a dense crowd
(a real Re-ID model or DeepSORT would be the next step).
"""
from collections import deque
import config


def iou(a, b):
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union


class Track:
    def __init__(self, track_id, box, now):
        self.id = track_id
        self.box = box
        self.first_seen = now
        self.last_seen = now
        self.hits = 1
        self.votes = deque(maxlen=5)   # recent face results: person id or None
        self.vote_sims = deque(maxlen=5)
        self.identity = None           # {"personId","name","similarity"} once confirmed
        self.last_verified = 0.0       # last time a face confirmed the identity
        self.face_rejected = 0         # good-quality faces that matched nobody
        self.last_face_check = 0.0     # last time we ran the face model on this track
        self.last_face_jpeg = None     # newest good face picture (used for alerts when the face turns away)
        self.last_quality = None
        self.positions = deque(maxlen=8)   # (time, centre x, centre y, height)
        self.last_alert = {}           # key -> time, so one track does not spam alerts
        self.attrs = None              # latest clothes information
        self.speed = None

    def update(self, box, now):
        self.box = box
        self.last_seen = now
        self.hits += 1
        x1, y1, x2, y2 = box
        self.positions.append((now, (x1 + x2) / 2, (y1 + y2) / 2, max(y2 - y1, 1)))
        if len(self.positions) >= 3:
            t0, x0, y0, h0 = self.positions[0]
            t1, x1_, y1_, h1 = self.positions[-1]
            if t1 > t0:
                dist = ((x1_ - x0) ** 2 + (y1_ - y0) ** 2) ** 0.5
                self.speed = dist / ((h0 + h1) / 2) / (t1 - t0)   # body-heights per second


class Tracker:
    def __init__(self):
        self.tracks = {}
        self._next_id = 1

    def update(self, boxes, now):
        """boxes: list of (x1,y1,x2,y2). Returns [(track, box)] for the boxes seen in this frame."""
        pairs = sorted(
            ((iou(t.box, b), tid, bi) for tid, t in self.tracks.items() for bi, b in enumerate(boxes)),
            reverse=True,
        )
        used_tracks, used_boxes, seen = set(), set(), []
        for score, tid, bi in pairs:
            if score < 0.3:
                break
            if tid in used_tracks or bi in used_boxes:
                continue
            used_tracks.add(tid)
            used_boxes.add(bi)
            self.tracks[tid].update(boxes[bi], now)
            seen.append((self.tracks[tid], boxes[bi]))

        for bi, box in enumerate(boxes):
            if bi in used_boxes:
                continue
            track = Track(self._next_id, box, now)
            track.update(box, now)
            track.hits = 1
            self.tracks[self._next_id] = track
            self._next_id += 1
            seen.append((track, box))

        for tid in [t for t, tr in self.tracks.items() if now - tr.last_seen > config.TRACK_TTL]:
            del self.tracks[tid]
        return seen
