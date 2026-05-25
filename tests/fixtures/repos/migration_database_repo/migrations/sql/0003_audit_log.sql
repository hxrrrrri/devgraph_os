CREATE TABLE audit_log (
  id        BIGSERIAL PRIMARY KEY,
  user_id   INTEGER REFERENCES users(id),
  action    TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE posts ADD COLUMN published BOOLEAN NOT NULL;
