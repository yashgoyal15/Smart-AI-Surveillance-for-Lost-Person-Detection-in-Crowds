# Experiments for the results section (15.2)

Three scripts, one per measurement. Install the extra package once: `pip install -r tools/requirements-tools.txt`.
Run them from the `ai_service` folder with the virtual environment active.

| Experiment | Script | Needs |
|---|---|---|
| Recognition accuracy, threshold sweep 0.30-0.80, ROC / PR, EER, 0.5 vs 0.85, per-camera threshold advice, ablation on number of reference photos | `evaluate_recognition.py` | your dataset (below) |
| Latency and throughput: people per frame, resolution, YOLO-then-face vs whole-frame face detector, 1-4 cameras, batching | `benchmark_latency.py` | any crowd photo, AI service **stopped** |
| Database: query time vs N, with / without HNSW, index recall | `benchmark_db.py` | PostgreSQL running |

## 1. Build the recognition dataset
```
dataset/
  p01/enrol/front.jpg, left.jpg ...        1-5 reference photos (like the reporter uploads)
  p01/probe/camA/*.jpg                     frames or crops from camera A (different pose, light, distance)
  p01/probe/camB/*.jpg
  p02/...
  impostors/*.jpg                          people who are NOT registered (a false accept rate needs them)
```
* At least 10 registered people, 20+ probes each, and as many impostor images as genuine ones.
* Record each camera on purpose: near / far, bright / dim, looking at the camera / looking away.
* A public benchmark (for example LFW) can be added as extra people + impostors, but state that it is not surveillance quality.
* Get written permission from everybody who appears in the dataset (see the ethics section).

```
python tools/evaluate_recognition.py --dataset dataset --out results/recognition
python tools/evaluate_recognition.py --dataset dataset --enrol-photos 1 --out results/ablation_1photo
python tools/evaluate_recognition.py --dataset dataset --enrol-photos 3 --out results/ablation_3photo
```
Outputs: `threshold_sweep.csv` (one row per threshold), `summary.json` (AUC, EER, 0.5 vs 0.85, advice per camera), `curves.png`.
`--demo` runs on a synthetic test only to prove the script works. **Never report demo numbers.**

## 2. Latency
```
python tools/benchmark_latency.py --image my_crowd.jpg --runs 10 --out results/latency_cpu
```
Run once on a CPU machine and once on a GPU machine (the JSON records the device and library versions).
Time from "person appears" to "alert visible": read `alert_dispatch_ms` from `GET http://localhost:5001/metrics`
(header `X-Internal-Api-Key`) and add the delay until the row shows in the Live Alerts page (a stopwatch or screen recording).

## 3. Database
```
python tools/benchmark_db.py --sizes 100 1000 10000 100000 --queries 200 --out results/db
```
Uses random vectors in a scratch table (dropped afterwards). Random vectors have no cluster structure, so the
index recall on them is a pessimistic bound; repeat the biggest size with real embeddings if possible.

## 4. Robustness (manual, write down what you see)
* Camera drop and reconnect: unplug the camera or stop the phone app; the card shows "reconnecting", it must come back by itself.
* Cooldown: stand in front of one camera for 60 s; you should get one alert per 15 s (`ALERT_COOLDOWN_SECONDS`), and the same count after restarting the AI service (the cooldown now lives in the database).
* Concurrent writes: run 4 cameras on the same video and count alerts in the audit log vs the AI service counter (`counters.alerts` in /metrics). They must agree except for deduplicated ones.
* False alerts: record 10 minutes of a busy place with nobody registered; report alerts per hour with and without `VOTES_REQUIRED` (1 vs 2).

## 5. Report this next to every result
CPU / GPU model, RAM, OS, Python version, library versions (printed in `latency.json`), PostgreSQL + pgvector version
(printed by `benchmark_db.py`), camera models and resolution, and the exact settings (`.env`): thresholds, `MAX_FRAME_WIDTH`,
`MAX_PEOPLE_PER_FRAME`, `VOTES_REQUIRED`, `MARGIN`.
