"""Actual comparison/expansion/search/backend counts on synthetic API batches."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc

from schemawitness import Limits, review
import schemawitness.engine as engine
import schemawitness.model as model
import schemawitness.review as review_module
from schemawitness.search import Search
import importlib
review_module = importlib.import_module("schemawitness.review")

def fixture(distinct=False, operations=100):
    count, operations = operations, []
    for i in range(count):
        old = {"type": "string", "minLength": 500 + (i if distinct else 0), "description": "synthetic"}
        new = {"const": "x"}
        operations.append(dict(id=f"op{i:03d}", request=dict(old=old, new=new), response=dict(old=old, new=new)))
    return dict(operations=operations)

def counted(manifest, **kwargs):
    counts = dict(core_compare_calls=0, expansion_calls=0, proof_calls=0, search_entries=0,
                  candidate_yields=0, independent_membership_calls=0, reference_preflight_calls=0, meta_schema_checks=0)
    saved = dict(compare=review_module.compare, compile=model.Compiler.compile,
        proof=model.prove_subset, engine_proof=engine.prove_subset, values=Search._values,
        candidates=Search.candidates, validate=engine.independent_validate,
        lookup=engine.check_reference_lookup, meta=engine.Draft202012Validator.check_schema)
    def wrap(name, fn):
        def call(*args, **kw):
            counts[name] += 1
            return fn(*args, **kw)
        return call
    def candidates(*args, **kw):
        for value in saved["candidates"](*args, **kw):
            counts["candidate_yields"] += 1
            yield value
    review_module.compare = wrap("core_compare_calls", saved["compare"])
    model.Compiler.compile = wrap("expansion_calls", saved["compile"])
    model.prove_subset = engine.prove_subset = wrap("proof_calls", saved["proof"])
    Search._values = wrap("search_entries", saved["values"])
    Search.candidates = candidates
    engine.independent_validate = wrap("independent_membership_calls", saved["validate"])
    engine.check_reference_lookup = wrap("reference_preflight_calls", saved["lookup"])
    engine.Draft202012Validator.check_schema = wrap("meta_schema_checks", saved["meta"])
    try:
        result = review(manifest, **kwargs)
    finally:
        review_module.compare = saved["compare"]
        model.Compiler.compile = saved["compile"]
        model.prove_subset, engine.prove_subset = saved["proof"], saved["engine_proof"]
        Search._values, Search.candidates = saved["values"], saved["candidates"]
        engine.independent_validate, engine.check_reference_lookup = saved["validate"], saved["lookup"]
        engine.Draft202012Validator.check_schema = saved["meta"]
    return result, counts

def retained_cache_size(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(retained_cache_size(k, seen) + retained_cache_size(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple, set, frozenset)):
        size += sum(retained_cache_size(v, seen) for v in value)
    return size


def rss():
    if sys.platform != "win32":
        return {"supported": False, "reason": "this probe records Windows process RSS"}
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    get_process = ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype = wintypes.HANDLE
    get_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not get_info(get_process(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return {"supported": True, "current_bytes": counters.WorkingSetSize,
            "process_lifetime_peak_bytes": counters.PeakWorkingSetSize,
            "scope": "whole process including imports, previous samples and tracemalloc; not cache-owned RSS"}


def run(distinct=False, operations=100, **kwargs):
    manifest = fixture(distinct, operations)
    before = deepcopy(manifest)
    limits = Limits(max_candidates=20, max_instance_units=16)
    result, counts = counted(manifest, limits=limits, **kwargs)
    assert manifest == before and len(result["operations"]) == operations and result["decision"] == "BLOCK"
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        review(manifest, limits=limits, **kwargs)
        samples.append((time.perf_counter() - start) * 1000)
    tracemalloc.start()
    review(manifest, limits=limits, **kwargs)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    cache_heap = 0
    def capture(frame, event, arg):
        nonlocal cache_heap
        if event == "return" and frame.f_code is review.__code__:
            cache_heap = retained_cache_size(frame.f_locals.get("cache", {}))
    if kwargs:
        sys.setprofile(capture)
        try:
            review(manifest, limits=limits, **kwargs)
        finally:
            sys.setprofile(None)
    return dict(distinct=distinct, operations=operations, actual_counts=counts, status_counts=result["counts"],
        milliseconds=samples, median_ms=statistics.median(samples), python_traced_peak_bytes=peak,
        retained_cache_reachable_peak_bytes=cache_heap,
        cache_heap_scope="retained cache object graph at return; monotonically growing entries; excludes temporary copies and allocator overhead; not a cache-only allocation peak",
        rss=rss(), batch=result.get("batch"), input_unchanged=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--batch-work", type=int)
    parser.add_argument("--operations", type=int, default=100)
    args = parser.parse_args()
    kw = {}
    if args.batch_work is not None:
        from schemawitness import BatchLimits
        kw["batch_limits"] = BatchLimits(max_work=args.batch_work)
    if not 1 <= args.operations <= 2000:
        parser.error("operations must be 1..2000")
    result = dict(scope="synthetic operations, complete review including input/cache/result handling; original per-direction limits retained; timings are local observations",
        new_bug_claim=False, cases=[run(False, args.operations, **kw), run(True, args.operations, **kw)])
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
