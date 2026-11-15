import argparse
import os
import sys
from memory import Memory
from config import CONSOLIDATE_HOURS

def build_parser():
    parser = argparse.ArgumentParser(prog="LoreMemory", description="LoreMemory LLM Memory CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_rem = sub.add_parser("remember")
    p_rem.add_argument("text", type=str)
    p_rem.add_argument("-i", "--importance", type=float, default=0.5)
    p_rem.add_argument("-s", "--session", type=str, default=None)
    p_rem.add_argument("--ttl", type=float, default=None)

    p_rec = sub.add_parser("recall")
    p_rec.add_argument("query", type=str)
    p_rec.add_argument("-k", type=int, default=5)

    p_recent = sub.add_parser("recent")
    p_recent.add_argument("-k", type=int, default=10)

    p_pend = sub.add_parser("pending")
    p_pend.add_argument("--hours", type=float, default=CONSOLIDATE_HOURS)

    p_ep = sub.add_parser("episode")
    p_ep.add_argument("--ids", type=str, required=True)
    p_ep.add_argument("--summary", type=str, required=True)
    p_ep.add_argument("-i", "--importance", type=float, default=None)

    p_cons = sub.add_parser("consolidate")
    p_cons.add_argument("--hours", type=float, default=CONSOLIDATE_HOURS)

    p_imp = sub.add_parser("importance")
    p_imp.add_argument("id", type=int)
    p_imp.add_argument("value", type=float)
    p_imp.add_argument("--episode", action="store_true")

    sub.add_parser("stats")
    return parser

def run(argv=None, mem=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    close_mem = False
    if mem is None:
        mem = Memory()
        close_mem = True

    try:
        cmd = args.command
        if cmd == "remember":
            sess = args.session or os.environ.get("LOREMEMORY_SESSION", "terminal")
            new_id = mem.remember(args.text, importance=args.importance, session=sess, ttl_hours=args.ttl)
            print(f"saved #{new_id}")
            return 0

        if cmd == "recall":
            items = mem.recall(args.query, k=args.k)
            if not items:
                print("nothing found")
            else:
                for it in items:
                    print(f"[{it['source']} #{it['id']}] imp:{it['importance']:.2f} time:{it['created']} score:{it['score']:.2f}")
                    print(it["text"])
            return 0

        if cmd == "recent":
            items = mem.recent(k=args.k)
            if not items:
                print("nothing found")
            else:
                for it in items:
                    print(f"[{it['source']} #{it['id']}] imp:{it['importance']:.2f} time:{it['created']}")
                    print(it["text"])
            return 0

        if cmd == "pending":
            items = mem.pending(hours=args.hours)
            if not items:
                print("no pending memories")
            else:
                for it in items:
                    print(f"[working #{it['wm_id']}] session:{it['session_id']} time:{it['created_at']}")
                    print(it["content"])
            return 0

        if cmd == "episode":
            try:
                ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
            except ValueError:
                print("invalid ids list", file=sys.stderr)
                return 1
            ep_id = mem.save_episode(ids, args.summary, importance=args.importance)
            if ep_id is not None:
                print(f"episode #{ep_id} saved")
                return 0
            else:
                print("failed: memories already consolidated or not found")
                return 1

        if cmd == "consolidate":
            cnt = mem.consolidate(hours=args.hours)
            print(f"consolidated {cnt} episodes")
            return 0

        if cmd == "importance":
            src = "episodic" if args.episode else "working"
            mem.set_importance(args.id, args.value, source=src)
            print("importance updated")
            return 0

        if cmd == "stats":
            st = mem.stats()
            print(f"working: {st['working']}")
            print(f"unconsolidated: {st['unconsolidated']}")
            print(f"episodes: {st['episodes']}")
            print(f"embeddings: {st['embeddings']}")
            return 0

        return 0
    finally:
        if close_mem:
            mem.close()

if __name__ == "__main__":
    sys.exit(run())
