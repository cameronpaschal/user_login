# user_login

Command line helpers for creating, updating, deleting, and authenticating users in a Postgres database.

## Prerequisites

- Python 3.10+
- `psycopg2` installed in your virtual environment
- A `users` table with at least the following columns:
  ```sql
  CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY,
      username TEXT NOT NULL,
      display_name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      religion TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
  ```

## Configuration

Connection details default to the environment variables below (falling back to the existing local defaults shown):

| Variable      | Default          |
| ------------- | ---------------- |
| `DB_HOST`     | `localhost`      |
| `DB_PORT`     | `5432`           |
| `DB_NAME`     | `cameronpaschal` |
| `DB_USER`     | `postgres`       |
| `DB_PASSWORD` | `bigpoppa`       |

You can override any of these when running the CLI by supplying `--db-host`, `--db-name`, etc.

## Usage

`user_cli.py` is a minimal interactive loop that prompts you for the action you want to perform (create, view, update, delete, list, or test a login). Just run:

```bash
python user_cli.py
```

and follow the on-screen prompts. Any fields you leave blank during updates stay unchanged. Password prompts use `getpass` so they are not echoed in the terminal.

Under the hood passwords are hashed with PBKDF2 (`sha256`, 310k iterations, random salt per-user). The hashes and salts are stored in the `password_hash` / `password_salt` columns whenever you create or update a user.
