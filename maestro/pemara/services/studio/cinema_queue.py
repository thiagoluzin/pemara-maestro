"""Durable project conversations. The web server and the account worker share SQLite."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time

DEFAULT_DB = Path(__file__).resolve().parents[2]/"dados"/"studio"/"cinema"/"chat.sqlite3"


class Busy(ValueError):
    pass


class ChatStore:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS turns (
                    seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, project TEXT NOT NULL,
                    request TEXT NOT NULL, context TEXT NOT NULL, status TEXT NOT NULL,
                    progress TEXT NOT NULL, result TEXT NOT NULL DEFAULT '{}',
                    created REAL NOT NULL, updated REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS conversation ON turns(project,seq);
                CREATE INDEX IF NOT EXISTS waiting_turns ON turns(seq) WHERE status='queued';
                CREATE UNIQUE INDEX IF NOT EXISTS active_turn ON turns(project)
                    WHERE status IN ('queued','running');
                CREATE TABLE IF NOT EXISTS worker (id INTEGER PRIMARY KEY, heartbeat REAL);
                CREATE TABLE IF NOT EXISTS decisions (
                    turn_id TEXT, kind TEXT, state TEXT, detail TEXT,
                    PRIMARY KEY(turn_id,kind));
                CREATE TABLE IF NOT EXISTS conversation_versions (
                    project TEXT PRIMARY KEY, revision INTEGER NOT NULL);
                CREATE TRIGGER IF NOT EXISTS cinema_turn_created AFTER INSERT ON turns BEGIN
                    INSERT INTO conversation_versions VALUES(NEW.project,1)
                    ON CONFLICT(project) DO UPDATE SET revision=revision+1;
                END;
                CREATE TRIGGER IF NOT EXISTS cinema_turn_changed AFTER UPDATE ON turns BEGIN
                    INSERT INTO conversation_versions VALUES(NEW.project,1)
                    ON CONFLICT(project) DO UPDATE SET revision=revision+1;
                END;
            """)

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path,timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def submit(self, project, key, request, context):
        now = time.time()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM turns WHERE id=?",(key,)).fetchone()
            if existing:
                if existing["project"]!=project or existing["request"]!=request or json.loads(existing["context"]).get("selection")!=context["selection"]:
                    raise Busy("Identificador de envio já utilizado.")
                return key
            if db.execute("SELECT count(*) FROM turns WHERE status IN ('queued','running')").fetchone()[0]>=32:
                raise Busy("A fila de conversas está cheia.")
            try:
                db.execute("INSERT INTO turns(id,project,request,context,status,progress,created,updated) VALUES(?,?,?,?,'queued','Na fila',?,?)",
                           (key,project,request,json.dumps(context,ensure_ascii=False),now,now))
            except sqlite3.IntegrityError:
                raise Busy("Este projeto já tem uma mensagem em andamento.")
        return key

    def history(self, project, before=None, limit=30, since=None):
        with self.db() as db:
            db.execute("BEGIN")  # Keep the revision, page and actions in one read snapshot.
            row = db.execute("SELECT revision FROM conversation_versions WHERE project=?", (project,)).fetchone()
            revision = row[0] if row else 0
            worker = db.execute("SELECT heartbeat FROM worker WHERE id=1").fetchone()
            meta = {"revision":revision,"workerOnline":bool(worker and time.time()-worker[0]<20)}
            if before is None and revision == since:
                return {**meta,"unchanged":True}
            rows = db.execute("SELECT * FROM turns WHERE project=? AND seq<? ORDER BY seq DESC LIMIT ?",
                              (project,before or 2**63-1,limit+1)).fetchall()
            actions = {r["id"]:{} for r in rows[:limit]}
            if actions:
                placeholders = ",".join("?" for _ in actions)
                for action in db.execute(f"SELECT * FROM decisions WHERE turn_id IN ({placeholders})",tuple(actions)):
                    actions[action["turn_id"]][action["kind"]] = {"state":action["state"],"detail":action["detail"]}
        items = [{"seq":r["seq"],"id":r["id"],"request":r["request"],"selection":json.loads(r["context"])["selection"],
                  "status":r["status"],"progress":r["progress"],"result":json.loads(r["result"]),"updated":r["updated"],"actions":actions[r["id"]]}
                 for r in reversed(rows[:limit])]
        return {**meta,"items":items,"older":len(rows)>limit}

    def claim(self):
        with self.db() as db:
            row = db.execute("SELECT * FROM turns WHERE status='queued' ORDER BY seq LIMIT 1").fetchone()
            if row:
                claimed = db.execute("UPDATE turns SET status='running',progress='Abrindo a conversa', updated=? WHERE seq=? AND status='queued'",(time.time(),row["seq"]))
                if claimed.rowcount:
                    return dict(row)

    def update(self, key, status, progress, result=None):
        with self.db() as db:
            db.execute("UPDATE turns SET status=?,progress=?,result=?,updated=? WHERE id=? AND status='running'",
                       (status,progress,json.dumps(result or {},ensure_ascii=False),time.time(),key))

    def cancel(self, project, key):
        with self.db() as db:
            db.execute("UPDATE turns SET status='cancelled',progress='Cancelado pelo operador',updated=? WHERE id=? AND project=? AND status IN ('running','queued')",
                       (time.time(),key,project))

    def active(self,key):
        with self.db() as db:
            row=db.execute("SELECT status FROM turns WHERE id=?",(key,)).fetchone()
            return bool(row and row[0]=="running")

    def reserve_action(self,project,key,kind):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM turns WHERE project=? AND id=? AND status='done'",(project,key)).fetchone()
            if not row: raise ValueError("Proposta indisponível.")
            result = json.loads(row["result"])
            if result.get("triage",{}).get("choice") != "aligned" or not result.get(kind):
                raise ValueError("A proposta requer revisão antes da aplicação.")
            if not db.execute("INSERT OR IGNORE INTO decisions VALUES(?,?,'reserved','')",(key,kind)).rowcount:
                raise Busy("Esta ação já foi registrada. Consulte o histórico.")
            db.execute("UPDATE turns SET updated=? WHERE id=?",(time.time(),key))
            return json.loads(row["context"]),result

    def finish_action(self,key,kind,state,detail):
        with self.db() as db:
            if db.execute("UPDATE decisions SET state=?,detail=? WHERE turn_id=? AND kind=?",(state,detail,key,kind)).rowcount:
                db.execute("UPDATE turns SET updated=? WHERE id=?",(time.time(),key))

    def release_unstarted_action(self,key,kind):
        with self.db() as db:
            if db.execute("DELETE FROM decisions WHERE turn_id=? AND kind=? AND state='reserved'",(key,kind)).rowcount:
                db.execute("UPDATE turns SET updated=? WHERE id=?",(time.time(),key))

    def recover(self):
        with self.db() as db:
            db.execute("UPDATE turns SET status='interrupted',progress='O operador reiniciou durante esta mensagem.',updated=? WHERE status='running'",(time.time(),))

    def heartbeat(self):
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO worker VALUES(1,?)",(time.time(),))

