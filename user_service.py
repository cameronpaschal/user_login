import os
import hashlib
import hmac
import binascii
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Some constants for password hashing
PBKDF2_ITERATIONS = 310000
PBKDF2_ALGORITHM = "sha256"
DEFAULT_SALT_BYTES = 16
HASH_DELIMITER = "$"


class UserServiceError(Exception):
    pass


class DatabaseConfig:
    def __init__(self, host, port, database, user, password):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password


def get_database_config_from_env():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if port is None or db_name is None or user is None or password is None:
        raise ValueError("One or more required DB_* env vars are missing")

    return DatabaseConfig(host, port, db_name, user, password)


def get_connection(config):
    # just open a new connection each time
    conn = psycopg2.connect(
        host=config.host,
        port=config.port,
        database=config.database,
        user=config.user,
        password=config.password,
    )
    return conn


def hash_password(password, salt_hex=None):
    # if we don't have a salt yet, make one
    if salt_hex is None:
        salt = os.urandom(DEFAULT_SALT_BYTES)
    else:
        salt = binascii.unhexlify(salt_hex)

    pwd_hash = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )

    hash_hex = binascii.hexlify(pwd_hash).decode("ascii")
    salt_hex = binascii.hexlify(salt).decode("ascii")

    return {
        "hash": hash_hex,
        "salt": salt_hex,
    }


def encode_password(hash_info):
    # store salt and hash together in one string
    return hash_info["salt"] + HASH_DELIMITER + hash_info["hash"]


def decode_password(stored_value):
    parts = stored_value.split(HASH_DELIMITER)
    if len(parts) != 2:
        raise UserServiceError("Stored password hash is malformed.")
    salt_hex = parts[0]
    hash_hex = parts[1]
    return {"salt": salt_hex, "hash": hash_hex}


def verify_password(password, stored_value):
    decoded = decode_password(stored_value)
    recomputed_hash_info = hash_password(password, decoded["salt"])
    computed_hash = recomputed_hash_info["hash"]
    # use compare_digest so timing is safer
    return hmac.compare_digest(computed_hash, decoded["hash"])


def create_user(config, username, display_name, email, religion, password):
    # hash the password first
    hashed = hash_password(password)
    password_to_store = encode_password(hashed)

    query = """
        INSERT INTO users (username, display_name, email, religion, password_hash)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
    """

    conn = get_connection(config)
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                query,
                (username, display_name, email, religion, password_to_store),
            )
            row = cur.fetchone()
            user_id = row[0]
            conn.commit()
            return user_id
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            raise UserServiceError("Username already exists.")
        finally:
            cur.close()
    finally:
        conn.close()


def list_users(config):
    query = "SELECT id, username, display_name, email, religion, created_at, updated_at FROM users ORDER BY id;"

    conn = get_connection(config)
    try:
        cur = conn.cursor()
        try:
            cur.execute(query)
            rows = cur.fetchall()
            users = []
            for row in rows:
                user = {
                    "id": row[0],
                    "username": row[1],
                    "display_name": row[2],
                    "email": row[3],
                    "religion": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                }
                users.append(user)
            return users
        finally:
            cur.close()
    finally:
        conn.close()


def get_user(config, username=None, user_id=None):
    if username is None and user_id is None:
        raise ValueError("Either username or user_id must be provided.")

    base_query = """
        SELECT id, username, display_name, email, religion, password_hash, created_at, updated_at
        FROM users
        WHERE {clause}
        LIMIT 1;
    """

    if username is not None:
        clause = "username = %s"
        param = username
    else:
        clause = "id = %s"
        param = user_id

    query = base_query.format(clause=clause)

    conn = get_connection(config)
    try:
        cur = conn.cursor()
        try:
            cur.execute(query, (param,))
            row = cur.fetchone()
            if row is None:
                raise UserServiceError("User not found.")
            user = {
                "id": row[0],
                "username": row[1],
                "display_name": row[2],
                "email": row[3],
                "religion": row[4],
                "password_hash": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            }
            return user
        finally:
            cur.close()
    finally:
        conn.close()


def update_user(config, username,
                new_username=None,
                new_display_name=None,
                new_email=None,
                new_religion=None,
                new_password=None):
    # build up the update parts
    updates = []
    params = []

    if new_username is not None:
        updates.append("username = %s")
        params.append(new_username)
    if new_display_name is not None:
        updates.append("display_name = %s")
        params.append(new_display_name)
    if new_email is not None:
        updates.append("email = %s")
        params.append(new_email)
    if new_religion is not None:
        updates.append("religion = %s")
        params.append(new_religion)
    if new_password is not None:
        hashed = hash_password(new_password)
        password_to_store = encode_password(hashed)
        updates.append("password_hash = %s")
        params.append(password_to_store)

    if len(updates) == 0:
        raise ValueError("No updates requested.")

    # always update timestamp
    updates.append("updated_at = CURRENT_TIMESTAMP")

    query = "UPDATE users SET " + ", ".join(updates) + " WHERE username = %s;"

    params.append(username)

    conn = get_connection(config)
    try:
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if cur.rowcount == 0:
                conn.rollback()
                raise UserServiceError("Username not found.")
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()


def delete_user(config, username):
    query = "DELETE FROM users WHERE username = %s;"

    conn = get_connection(config)
    try:
        cur = conn.cursor()
        try:
            cur.execute(query, (username,))
            if cur.rowcount == 0:
                conn.rollback()
                raise UserServiceError("Username not found.")
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()


def login(config, username, password):
    user = get_user(config, username=username)
    if verify_password(password, user["password_hash"]):
        # just return basic info, not the password hash
        return {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "email": user["email"],
            "religion": user["religion"],
        }
    else:
        raise UserServiceError("Invalid username or password.")