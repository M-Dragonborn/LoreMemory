import math, os, re, sqlite3, struct, threading
from datetime import datetime, timezone, timedelta
from config import (
    MEMORY_DB, VEC_W, KW_W, IMP_W, RECENCY_W,
    HALF_LIFE_HOURS, CONSOLIDATE_HOURS, MIN_SIM
)

class Memory:
    def __init__(self, db_path=None, enable_embeddings=False):
        self.db_path = str(db_path or MEMORY_DB)
        self.enable_embeddings, self.lock, self._model = enable_embeddings, threading.RLock(), None
        parent = os.path.dirname(self.db_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        self.con = sqlite3.connect(self.db_path, isolation_level=None, check_same_thread=False, timeout=5.0)
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.execute("PRAGMA journal_mode = WAL")
        self._init_db()

    def _init_db(self):
        with self.lock:
            self.con.execute("""CREATE TABLE IF NOT EXISTS episodic_memory (
                episode_id INTEGER PRIMARY KEY AUTOINCREMENT, summary TEXT NOT NULL,
                importance REAL NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
                scope TEXT NOT NULL DEFAULT 'global' CHECK (scope IN ('global','session')),
                source TEXT, embedding BLOB, period_start TEXT, period_end TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, last_accessed TEXT,
                access_count INTEGER DEFAULT 0, valid_until TEXT)""")
            self.con.execute("""CREATE TABLE IF NOT EXISTS working_memory (
                wm_id INTEGER PRIMARY KEY AUTOINCREMENT, episode_id INTEGER, session_id TEXT,
                content TEXT NOT NULL, importance REAL NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
                embedding BLOB, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TEXT,
                FOREIGN KEY (episode_id) REFERENCES episodic_memory(episode_id) ON DELETE SET NULL)""")

    def _get_embedding(self, text):
        if not self.enable_embeddings:
            return None
        try:
            if self._model is None:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            vec = self._model.encode(text).tolist()
            return struct.pack(f"{len(vec)}f", *vec)
        except (ImportError, OSError, RuntimeError, ValueError):
            return None

    def _cosine_sim(self, b1, b2):
        if not b1 or not b2 or len(b1) != len(b2):
            return 0.0
        n = len(b1) // 4
        v1, v2 = struct.unpack(f"{n}f", b1), struct.unpack(f"{n}f", b2)
        dot = sum(x * y for x, y in zip(v1, v2))
        m1, m2 = math.sqrt(sum(x * x for x in v1)), math.sqrt(sum(y * y for y in v2))
        return (dot / (m1 * m2)) if m1 and m2 else 0.0

    def remember(self, text, importance=0.5, session=None, ttl_hours=None):
        with self.lock:
            imp = max(0.0, min(1.0, float(importance)))
            expires_at = None
            if ttl_hours is not None:
                exp_dt = datetime.now(timezone.utc) + timedelta(hours=float(ttl_hours))
                expires_at = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
            emb = self._get_embedding(text)
            sql = "INSERT INTO working_memory (session_id, content, importance, embedding, expires_at) VALUES (?, ?, ?, ?, ?)"
            cur = self.con.execute(sql, (session, text, imp, emb, expires_at))
            return cur.lastrowid

    def recall(self, query, k=5):
        with self.lock:
            q_words = set(re.findall(r"\w+", query.lower()))
            q_emb, now_dt = self._get_embedding(query), datetime.now(timezone.utc)
            cur_w = self.con.execute("""SELECT wm_id, content, importance, embedding, created_at, session_id
                FROM working_memory WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP""")
            candidates = [("working", r[0], r[1], r[2], r[3], r[4], r[5] or "") for r in cur_w.fetchall()]

            cur_e = self.con.execute("""SELECT episode_id, summary, importance, embedding, created_at
                FROM episodic_memory WHERE valid_until IS NULL OR valid_until > CURRENT_TIMESTAMP""")
            candidates += [("episodic", r[0], r[1], r[2], r[3], r[4], "") for r in cur_e.fetchall()]

            scored = []
            for src, item_id, text, imp, emb, created_str, session in candidates:
                words = set(re.findall(r"\w+", text.lower()))
                common = q_words.intersection(words)
                kw = len(common) / len(q_words) if q_words else 0.0
                sim = self._cosine_sim(q_emb, emb) if q_emb and emb else 0.0
                if len(common) == 0 and sim < MIN_SIM:
                    continue
                try:
                    c_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    age_h = max(0.0, (now_dt - c_dt).total_seconds() / 3600.0)
                except Exception:
                    age_h = 0.0
                rec = 0.5 ** (age_h / HALF_LIFE_HOURS)
                score = (VEC_W * sim) + (KW_W * kw) + (IMP_W * imp) + (RECENCY_W * rec)
                scored.append({
                    "source": src, "id": item_id, "text": text,
                    "importance": imp, "created": created_str, "session": session,
                    "score": round(score, 4)
                })

            scored.sort(key=lambda x: x["score"], reverse=True)
            results = scored[:k]
            for it in results:
                if it["source"] == "episodic":
                    self.con.execute("UPDATE episodic_memory SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1 WHERE episode_id = ?", (it["id"],))
            return results

    def recent(self, k=10, offset=0):
        with self.lock:
            sql = """SELECT 'working' AS source, wm_id AS id, content AS text, importance, created_at, COALESCE(session_id, '') AS session
                FROM working_memory UNION ALL
                SELECT 'episodic' AS source, episode_id AS id, summary AS text, importance, created_at, '' AS session
                FROM episodic_memory ORDER BY created_at DESC LIMIT ? OFFSET ?"""
            cur = self.con.execute(sql, (k, offset))
            return [{"source": r[0], "id": r[1], "text": r[2], "importance": r[3],
                     "created": r[4], "session": r[5], "score": 0.0} for r in cur.fetchall()]

    def pending(self, hours=None):
        with self.lock:
            h = CONSOLIDATE_HOURS if hours is None else float(hours)
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S")
            sql = "SELECT wm_id, content, importance, session_id, created_at FROM working_memory WHERE episode_id IS NULL AND created_at <= ? ORDER BY created_at ASC"
            return [{"wm_id": r[0], "content": r[1], "importance": r[2],
                     "session_id": r[3] or "", "created_at": r[4]} for r in self.con.execute(sql, (cutoff,)).fetchall()]

    def save_episode(self, ids, summary, importance=None):
        with self.lock:
            if not ids: return None
            placeholders = ", ".join(["?"] * len(ids))
            cur = self.con.execute(f"SELECT wm_id, importance, created_at FROM working_memory WHERE wm_id IN ({placeholders}) AND episode_id IS NULL", tuple(ids))
            rows = cur.fetchall()
            if not rows: return None
            max_imp = max(r[1] for r in rows) if importance is None else float(importance)
            p_start, p_end = min(r[2] for r in rows), max(r[2] for r in rows)
            emb = self._get_embedding(summary)
            sql = "INSERT INTO episodic_memory (summary, importance, scope, source, embedding, period_start, period_end) VALUES (?, ?, 'global', 'manual', ?, ?, ?)"
            cur_ep = self.con.execute(sql, (summary, max_imp, emb, p_start, p_end))
            ep_id = cur_ep.lastrowid
            self.con.execute(f"UPDATE working_memory SET episode_id = ? WHERE wm_id IN ({placeholders}) AND episode_id IS NULL", (ep_id,) + tuple(ids))
            return ep_id

    def consolidate(self, hours=None):
        with self.lock:
            items = self.pending(hours)
            if not items: return 0
            groups = {}
            for it in items:
                groups.setdefault(it["session_id"], []).append(it)
            count = 0
            for sess, mems in groups.items():
                m_ids = [m["wm_id"] for m in mems]
                joined = " | ".join(m["content"] for m in mems)[:1000]
                max_imp = max(m["importance"] for m in mems)
                p_start, p_end = min(m["created_at"] for m in mems), max(m["created_at"] for m in mems)
                emb = self._get_embedding(joined)
                sql = "INSERT INTO episodic_memory (summary, importance, scope, source, embedding, period_start, period_end) VALUES (?, ?, 'global', 'consolidation', ?, ?, ?)"
                cur_ep = self.con.execute(sql, (joined, max_imp, emb, p_start, p_end))
                ep_id = cur_ep.lastrowid
                p_holders = ", ".join(["?"] * len(m_ids))
                self.con.execute(f"UPDATE working_memory SET episode_id = ? WHERE wm_id IN ({p_holders})", (ep_id,) + tuple(m_ids))
                count += 1
            return count

    def set_importance(self, item_id, value, source="working"):
        with self.lock:
            val = max(0.0, min(1.0, float(value)))
            table, col = ("episodic_memory", "episode_id") if source == "episodic" else ("working_memory", "wm_id")
            self.con.execute(f"UPDATE {table} SET importance = ? WHERE {col} = ?", (val, item_id))

    def stats(self):
        with self.lock:
            w_cnt = self.con.execute("SELECT COUNT(*) FROM working_memory").fetchone()[0]
            u_cnt = self.con.execute("SELECT COUNT(*) FROM working_memory WHERE episode_id IS NULL").fetchone()[0]
            e_cnt = self.con.execute("SELECT COUNT(*) FROM episodic_memory").fetchone()[0]
            emb_w = self.con.execute("SELECT COUNT(*) FROM working_memory WHERE embedding IS NOT NULL").fetchone()[0]
            emb_e = self.con.execute("SELECT COUNT(*) FROM episodic_memory WHERE embedding IS NOT NULL").fetchone()[0]
            return {"working": w_cnt, "unconsolidated": u_cnt, "episodes": e_cnt, "embeddings": emb_w + emb_e}

    def close(self):
        with self.lock:
            if self.con:
                try: self.con.close()
                except Exception: pass
                self.con = None
