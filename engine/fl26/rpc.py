"""Newline-delimited JSON over stdin/stdout: the Electron shell's only door into the engine.

    -> {"id": 1, "method": "open_save", "params": {"path": "..."}}
    <- {"id": 1, "ok": true, "result": {...}}
    <- {"id": 2, "ok": false, "error": "message"}
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

from . import config, i18n, safewrite
from .i18n import tr
from .database import DEFAULT_DUMP, Database
from .session import Session


class Server:
    def __init__(self):
        self.db = None
        self.s = None

    def _db(self, save_dir):
        if self.db is None:
            self.db = Database(DEFAULT_DUMP, Path(save_dir) / "EDIT00000000")
        return self.db

    def _session(self):
        if self.s is None:
            raise RuntimeError(tr("err.noCareer"))
        return self.s

    # ------------------------------------------------------------------ methods

    def ping(self):
        return {"pong": True}

    # first-run setup: where the game is, and the database dump CareerLab reads

    def set_language(self, lang):
        return {"lang": i18n.set_lang(lang)}

    def setup_status(self):
        return config.status()

    def set_game_dir(self, path):
        config.set_game_dir(path)
        self.db = None
        return config.status()

    def set_save_dir(self, path):
        if not Path(path).is_dir():
            raise RuntimeError(tr("err.noFolder"))
        cfg = config.load()
        cfg["saveDir"] = str(Path(path))
        config.save(cfg)
        return config.status()

    def install_dump_module(self):
        config.install_module()
        return config.status()

    def game_state(self):
        return {"running": safewrite.game_running()}

    def list_saves(self, save_dir=None):
        d = Path(save_dir or config.save_dir())
        out = []
        for p in sorted(d.glob("BL*")):
            if p.is_file():
                out.append({"path": str(p), "slot": p.name, "size": p.stat().st_size,
                            "modified": int(p.stat().st_mtime)})
        return {"dir": str(d), "saves": out}

    def open_save(self, path):
        self.s = Session(path, self._db(Path(path).parent))
        return self.s.summary()

    def summary(self):
        return self._session().summary()

    def clubs(self):
        return self._session().clubs()

    def squad(self, block):
        return self._session().squad(int(block))

    def player(self, pid):
        return self._session().player(int(pid))

    def search(self, query):
        return self._session().search(query)

    def sync_plan(self, block, refresh=False):
        return self._session().sync_plan(int(block), refresh)

    def leagues(self):
        return self._session().leagues()

    def league_plan(self, comp_id, refresh=False):
        return self._session().league_plan(comp_id, refresh)

    def stage_many(self, ops):
        return self._session().stage_many(ops)

    def efdb_player(self, pid):
        from . import efdb
        p = efdb.player(int(pid))
        return {"pid": p["pes_id"], "name": p.get("player_name"), "position": p.get("main_position_text"),
                "age": p.get("age"), "status": self._session().status(int(pid))}

    def stage(self, op):
        return self._session().stage(op)

    def unstage(self, index):
        return self._session().unstage(int(index))

    def unstage_all(self):
        return self._session().unstage_all()

    def staged(self):
        return self._session().staged

    def preview(self):
        return self._session().preview()

    def apply(self):
        return self._session().apply()

    def backups(self):
        return self._session().backups()

    def restore(self, file):
        return self._session().restore(file)


def main():
    srv = Server()
    # Windows pipes default to the ANSI code page; the protocol is UTF-8 both ways.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    out = sys.stdout
    sys.stdout = sys.stderr                      # stray prints must never corrupt the pipe
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            fn = getattr(srv, req["method"], None)
            if fn is None or req["method"].startswith("_"):
                raise RuntimeError(f"unknown method {req['method']}")
            res = {"id": rid, "ok": True, "result": fn(**(req.get("params") or {}))}
        except Exception as e:                   # report, never die
            traceback.print_exc(file=sys.stderr)
            res = {"id": rid, "ok": False, "error": str(e)}
        out.write(json.dumps(res, ensure_ascii=False) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
