-- LPDP CTRL+F — PostgreSQL schema (DigitalOcean Managed Postgres)
-- Single table backing the collective wishlist + insights features.
--
-- NOTE: `id` is uuid to match Supabase's original default (gen_random_uuid()).
-- If the source Supabase table used a bigint/identity PK instead, change the
-- `id` column to `bigint GENERATED ALWAYS AS IDENTITY` before importing data.

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

CREATE TABLE IF NOT EXISTS donations (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id                text UNIQUE NOT NULL,
    amount                  int NOT NULL CHECK (amount >= 5000),
    status                  text NOT NULL DEFAULT 'pending',
    payment_type            text,
    midtrans_transaction_id text,
    raw_notification        jsonb,
    created_at              timestamptz DEFAULT now(),
    paid_at                 timestamptz
);

CREATE INDEX IF NOT EXISTS idx_donations_order_id ON donations (order_id);
CREATE INDEX IF NOT EXISTS idx_donations_status ON donations (status);
