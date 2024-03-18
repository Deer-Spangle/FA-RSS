CREATE TABLE IF NOT EXISTS "submissions" (
  "submission_id" integer NOT NULL PRIMARY KEY,
  "username" text NOT NULL,
  "gallery" text NOT NULL,
  "title" text NOT NULL,
  "description" text NOT NULL,
  "download_url" text NOT NULL,
  "thumbnail_url" text,
  "posted_at" timestamptz NOT NULL,
  "rating" text NOT NULL,
  "keywords" text[] NOT NULL
);
CREATE INDEX "submissions_username_gallery" ON "submissions" ("username", "gallery");

CREATE TABLE IF NOT EXISTS "users" (
  "username" text NOT NULL PRIMARY KEY,
  "initialised_date" timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS "settings" (
    "key" text NOT NULL PRIMARY KEY,
    "value" text
);