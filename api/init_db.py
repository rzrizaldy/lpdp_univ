"""
Idempotent schema bootstrap, run as an App Platform PRE_DEPLOY job.

Uses the DATABASE_URL bound by App Platform (the managed lpdpfind DB on the
colorize-db cluster). Safe to run on every deploy — all DDL is IF NOT EXISTS.
"""

import os
import sys
import psycopg

SCHEMA = """
CREATE TABLE IF NOT EXISTS wishlists (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_fingerprint text NOT NULL,
    university_name  text NOT NULL DEFAULT '',
    program_name     text NOT NULL DEFAULT '',
    location         text DEFAULT '',
    jenjang          text DEFAULT '',
    beasiswa         text DEFAULT '',
    created_at       timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wishlists_fingerprint ON wishlists (user_fingerprint);
"""


def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set; skipping schema bootstrap", file=sys.stderr)
        return 0
    with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='wishlists'"
        )
        ok = cur.fetchone()[0] == 1
    print("schema bootstrap complete; wishlists table present:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
