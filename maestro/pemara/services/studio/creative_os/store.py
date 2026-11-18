"""Transactional metadata and append-only revisions, separate from legacy state."""
from __future__ import annotations

import copy
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .ir import CreativeError, identifier


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def transaction(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA busy_timeout=15000")
            con.execute("CREATE TABLE IF NOT EXISTS entities (kind TEXT, id TEXT, revision INTEGER, data TEXT, PRIMARY KEY(kind,id))")
            con.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, kind TEXT, id TEXT, revision INTEGER, at REAL, data TEXT)")
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def read(con, kind, entity_id):
        row = con.execute("SELECT data FROM entities WHERE kind=? AND id=?", (kind, entity_id)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def write(con, kind, entity_id, data, *, expected=None, create=False):
        identifier(kind); identifier(entity_id)
        old = Store.read(con, kind, entity_id)
        if create and old is not None:
            raise CreativeError("ALREADY_EXISTS", "Registro já existe.", 409)
        if expected is not None and (old or {}).get("revision", 0) != expected:
            raise CreativeError("REVISION_CONFLICT", "Registro mudou; releia antes de alterar.", 409)
        result = copy.deepcopy(data)
        result.update(id=entity_id, revision=(old or {}).get("revision", 0) + 1, updated_at=time.time())
        result.setdefault("created_at", (old or {}).get("created_at", result["updated_at"]))
        raw = json.dumps(result, ensure_ascii=False, allow_nan=False)
        con.execute("INSERT INTO entities VALUES(?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET revision=excluded.revision,data=excluded.data", (kind, entity_id, result["revision"], raw))
        con.execute("INSERT INTO events(kind,id,revision,at,data) VALUES(?,?,?,?,?)", (kind, entity_id, result["revision"], time.time(), raw))
        return result

    def get(self, kind, entity_id):
        identifier(entity_id)
        with self.transaction() as con:
            value = self.read(con, kind, entity_id)
        if value is None:
            raise CreativeError("NOT_FOUND", "Registro não encontrado.", 404)
        return value

    def put(self, kind, data, *, entity_id=None, expected=None, create=True):
        with self.transaction() as con:
            return self.write(con, kind, entity_id or uuid.uuid4().hex, data, expected=expected, create=create)

    def list(self, kind, limit=100):
        with self.transaction() as con:
            rows = con.execute("SELECT data FROM entities WHERE kind=? ORDER BY rowid DESC LIMIT ?", (kind, max(1, min(500, int(limit))))).fetchall()
        return [json.loads(row[0]) for row in rows]

    def history(self, kind, entity_id):
        identifier(entity_id)
        with self.transaction() as con:
            rows = con.execute("SELECT data FROM events WHERE kind=? AND id=? ORDER BY seq", (kind, entity_id)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def where(self, kind, field, value):
        """Internal exact-scope query; pagination must not hide an active generation."""
        identifier(field)
        with self.transaction() as con:
            rows=con.execute("SELECT data FROM entities WHERE kind=? AND json_extract(data,?)=? ORDER BY rowid DESC",
                             (kind,"$."+field,value)).fetchall()
        return [json.loads(row[0]) for row in rows]
