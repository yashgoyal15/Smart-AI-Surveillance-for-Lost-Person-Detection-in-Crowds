"""
Database matching experiment (section 15.2 "Database matching").

Measures pgvector query time versus the number of registered face vectors (default 100 / 1,000 / 10,000;
add 100000 if you have the time), WITHOUT an index (exact search) and WITH the HNSW index, and the recall
of the approximate index compared with exact search.

It uses a scratch table `bench_vectors` (created and dropped by this script - your real tables are not touched).
Vectors are random unit vectors in 512 dimensions. Queries are noisy copies of stored vectors, like a camera
face compared with its reference photo. Random vectors are easier than real faces, so repeat the final
measurement on real embeddings if you can (use --real to take vectors from person_embeddings).

RUN   python tools/benchmark_db.py --sizes 100 1000 10000 --queries 200 --out results/db
"""
import argparse
import csv
import json
import os
import sys
import time
import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import execute_values

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

DIM = 512


def unit(x):
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def timed_queries(cur, queries, k, runs_warmup=5):
    """Returns (list of milliseconds, list of top-k id lists)."""
    sql = "SELECT id FROM bench_vectors ORDER BY embedding <=> %s LIMIT %s"
    for q in queries[:runs_warmup]:
        cur.execute(sql, (q, k))
        cur.fetchall()
    times, results = [], []
    for q in queries:
        started = time.perf_counter()
        cur.execute(sql, (q, k))
        ids = [r[0] for r in cur.fetchall()]
        times.append((time.perf_counter() - started) * 1000)
        results.append(ids)
    return times, results


def stats(times):
    a = np.array(times)
    return round(float(a.mean()), 3), round(float(np.percentile(a, 50)), 3), round(float(np.percentile(a, 95)), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[100, 1000, 10000])
    ap.add_argument("--queries", type=int, default=200)
    ap.add_argument("--noise", type=float, default=0.9, help="noise added to a stored vector to make the query")
    ap.add_argument("--ef-search", type=int, nargs="+", default=[40, 100], help="HNSW ef_search values to try")
    ap.add_argument("--maintenance-mem", default="1GB", help="memory for building the HNSW index (big N is very slow with the 64MB default)")
    ap.add_argument("--out", default="results/db")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    conn = psycopg2.connect(config.DATABASE_URL)
    conn.autocommit = True
    register_vector(conn)
    cur = conn.cursor()
    cur.execute("SELECT version()")
    print(cur.fetchone()[0])
    cur.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
    pgv = cur.fetchone()[0]

    rng = np.random.default_rng(42)
    rows = []
    for n in args.sizes:
        print(f"\n=== N = {n} ===")
        cur.execute("DROP TABLE IF EXISTS bench_vectors")
        cur.execute(f"CREATE TABLE bench_vectors (id serial PRIMARY KEY, embedding vector({DIM}))")
        data = unit(rng.standard_normal((n, DIM)).astype(np.float32))
        for start in range(0, n, 5000):
            execute_values(cur, "INSERT INTO bench_vectors (embedding) VALUES %s", [(v,) for v in data[start:start + 5000]])
        cur.execute("ANALYZE bench_vectors")

        picks = rng.integers(0, n, size=args.queries)
        queries = unit(data[picks] + args.noise * unit(rng.standard_normal((args.queries, DIM)).astype(np.float32)))

        # exact search = no index, the database compares against every row
        t_exact, truth = timed_queries(cur, queries, 10)
        m, p50, p95 = stats(t_exact)
        rows.append({"N": n, "method": "exact (no index)", "ef_search": "", "mean_ms": m, "p50_ms": p50, "p95_ms": p95,
                     "recall@1": 1.0, "recall@10": 1.0, "build_s": 0})
        print(f"exact          mean {m} ms  p95 {p95} ms")

        cur.execute(f"SET maintenance_work_mem = '{args.maintenance_mem}'")
        started = time.perf_counter()
        cur.execute("CREATE INDEX bench_hnsw ON bench_vectors USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")
        build = round(time.perf_counter() - started, 2)
        cur.execute("ANALYZE bench_vectors")

        for ef in args.ef_search:
            cur.execute(f"SET hnsw.ef_search = {ef}")
            t_idx, found = timed_queries(cur, queries, 10)
            r1 = np.mean([f[0] == t[0] for f, t in zip(found, truth)])
            r10 = np.mean([len(set(f) & set(t)) / 10 for f, t in zip(found, truth)])
            m, p50, p95 = stats(t_idx)
            rows.append({"N": n, "method": "HNSW (m16, efc64)", "ef_search": ef, "mean_ms": m, "p50_ms": p50, "p95_ms": p95,
                         "recall@1": round(float(r1), 4), "recall@10": round(float(r10), 4), "build_s": build})
            print(f"HNSW ef={ef:<4}  mean {m} ms  p95 {p95} ms  recall@1 {r1:.3f}  recall@10 {r10:.3f}  (build {build}s)")

        cur.execute("DROP INDEX IF EXISTS bench_hnsw")

    cur.execute("DROP TABLE IF EXISTS bench_vectors")

    with open(os.path.join(args.out, "db_benchmark.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(args.out, "db_benchmark.json"), "w") as f:
        json.dump({"pgvector": pgv, "dim": DIM, "maintenance_work_mem": args.maintenance_mem, "queries": args.queries, "rows": rows}, f, indent=2)
    print(f"\nwritten to {args.out}/")


if __name__ == "__main__":
    main()
