CREATE TABLE users (
  id      SERIAL PRIMARY KEY,
  email   TEXT NOT NULL UNIQUE
);

CREATE INDEX users_email_idx ON users (email);
