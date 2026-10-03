import argparse
import sys
from pathlib import Path
from . import Limits, compare, dumps, loads, review
from .wire import WireError


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "review":
        return review_main(argv[1:])
    parser = argparse.ArgumentParser(description="Directional JSON Schema inclusion evidence")
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--direction", choices=("request", "response"), default="request")
    parser.add_argument("--max-candidates", type=int, default=2000)
    parser.add_argument("--max-instance-units", type=int, default=128)
    parser.add_argument("--no-proof", action="store_true", help="ablation: never prove compatibility")
    parser.add_argument("--no-search", action="store_true", help="ablation: return proof or UNKNOWN")
    args = parser.parse_args(argv)
    try:
        limits = Limits(max_candidates=args.max_candidates, max_instance_units=args.max_instance_units)
        schemas = []
        for path in (args.old, args.new):
            with path.open("rb") as stream:
                data = stream.read(limits.max_document_bytes + 1)
            schemas.append(loads(data.decode("utf-8"), max_bytes=limits.max_document_bytes))
        result = compare(*schemas, direction=args.direction, limits=limits,
                         prove=not args.no_proof, search=not args.no_search)
        print(dumps(result.to_dict()))
        return {"COMPATIBLE": 0, "BREAKING": 1, "UNKNOWN": 2, "INVALID": 3}[result.status]
    except (OSError, UnicodeError, WireError, ValueError) as exc:
        print(dumps({"status": "INVALID", "diagnostics": [{"code": "input_error", "message": str(exc)}]}))
        return 3


def review_main(argv):
    parser = argparse.ArgumentParser(description="Fail-closed API release review")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        limits = Limits()
        with args.manifest.open("rb") as stream:
            data = stream.read(limits.max_document_bytes + 1)
        result = review(loads(data.decode("utf-8"), max_bytes=limits.max_document_bytes), limits=limits)
        print(dumps(result))
        return {"COMPATIBLE": 0, "BREAKING": 1, "UNKNOWN": 2, "INVALID": 3}[result["status"]]
    except (OSError, UnicodeError, ValueError) as exc:
        print(dumps({"status": "INVALID", "decision": "BLOCK", "diagnostics": [{"code": "input_error", "message": str(exc)}]}))
        return 3
