# Database Schema (Part 5)

## SQL Schema (SQLite)

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  title TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS columns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  position INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
  UNIQUE (board_id, position)
);

CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  column_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  position INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (column_id) REFERENCES columns(id) ON DELETE CASCADE,
  UNIQUE (column_id, position)
);
```

## JSON View

```json
{
  "users": {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "username": "TEXT NOT NULL UNIQUE",
    "password_hash": "TEXT NOT NULL",
    "created_at": "TEXT NOT NULL DEFAULT datetime('now')"
  },
  "boards": {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "user_id": "INTEGER NOT NULL UNIQUE, FK -> users.id",
    "title": "TEXT NOT NULL",
    "created_at": "TEXT NOT NULL DEFAULT datetime('now')"
  },
  "columns": {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "board_id": "INTEGER NOT NULL, FK -> boards.id",
    "title": "TEXT NOT NULL",
    "position": "INTEGER NOT NULL, UNIQUE(board_id, position)",
    "created_at": "TEXT NOT NULL DEFAULT datetime('now')"
  },
  "cards": {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "column_id": "INTEGER NOT NULL, FK -> columns.id",
    "title": "TEXT NOT NULL",
    "description": "TEXT NOT NULL DEFAULT ''",
    "position": "INTEGER NOT NULL, UNIQUE(column_id, position)",
    "created_at": "TEXT NOT NULL DEFAULT datetime('now')",
    "updated_at": "TEXT NOT NULL DEFAULT datetime('now')"
  }
}
```

## Relationships and Constraints

- `users (1) -> boards (1)` for MVP using `boards.user_id UNIQUE`.
- `boards (1) -> columns (many)`.
- `columns (1) -> cards (many)`.
- Cascading deletes keep orphan records from remaining.
- `position` uniqueness constraints enforce ordered lanes and ordered cards.

## Migration Strategy

1. Create a `schema_migrations` table with `version` and `applied_at`.
2. Store SQL migration files in order (`001_init.sql`, `002_*.sql`, ...).
3. On app startup, execute unapplied migrations in a transaction.
4. For SQLite-incompatible ALTER operations, use create-copy-swap:
   1. Create new table.
   2. Copy data.
   3. Drop old table.
   4. Rename new table.

## Sample Queries

```sql
-- Get the signed-in user's board
SELECT b.id, b.title
FROM boards b
WHERE b.user_id = ?;

-- Get columns for a board in display order
SELECT c.id, c.title, c.position
FROM columns c
WHERE c.board_id = ?
ORDER BY c.position ASC;

-- Get cards for a board in lane and card order
SELECT ca.id, ca.column_id, ca.title, ca.description, ca.position
FROM cards ca
JOIN columns c ON c.id = ca.column_id
WHERE c.board_id = ?
ORDER BY c.position ASC, ca.position ASC;

-- Rename a column
UPDATE columns
SET title = ?
WHERE id = ?;

-- Create a card at end of a column
INSERT INTO cards (column_id, title, description, position)
VALUES (
  ?,
  ?,
  ?,
  COALESCE((SELECT MAX(position) + 1 FROM cards WHERE column_id = ?), 0)
);

-- Move a card to another column and position
UPDATE cards
SET column_id = ?, position = ?, updated_at = datetime('now')
WHERE id = ?;
```
