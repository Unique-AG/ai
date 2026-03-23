"""Benchmark script for KnowledgeBaseService file-tree resolution."""

from unique_toolkit import KnowledgeBaseService
from unique_toolkit.content.schemas import ContentInfo


if __name__ == "__main__":
    import asyncio
    import time
    from pathlib import Path

    import matplotlib.pyplot as plt
    from dotenv import load_dotenv

    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / "unique.env"
    if not env_file.exists():
        env_file = project_root / ".env"
    load_dotenv(env_file)

    CONCURRENCY_LEVELS = [1, 3, 9, 27, 81]

    async def main():
        kb = KnowledgeBaseService.from_settings()

        # --- Benchmark get_content_infos_async ---
        print("=" * 70)
        print("BENCHMARK: get_content_infos_async")
        print("=" * 70)

        content_infos: list[ContentInfo] = []
        content_results: dict[int, tuple[float, int]] = {}
        for level in CONCURRENCY_LEVELS:
            print(f"  max_concurrent_requests={level} ...", end=" ", flush=True)
            start = time.perf_counter()
            content_infos = await kb.get_content_infos_async(
                max_concurrent_requests=level
            )
            elapsed = time.perf_counter() - start
            content_results[level] = (elapsed, len(content_infos))
            print(f"{elapsed:.3f}s  ({len(content_infos)} items)")

        # --- Extract scope IDs (once, from last run) ---
        scope_ids = kb.extract_scope_ids(content_infos)
        print(f"\nExtracted {len(scope_ids)} unique scope IDs\n")

        # --- Benchmark _translate_scope_ids_async ---
        print("=" * 70)
        print("BENCHMARK: _translate_scope_ids_async")
        print("=" * 70)

        translate_results: dict[int, tuple[float, int]] = {}
        for level in CONCURRENCY_LEVELS:
            print(f"  max_concurrent_requests={level} ...", end=" ", flush=True)
            start = time.perf_counter()
            mapping = await kb._translate_scope_ids_async(
                scope_ids, max_concurrent_requests=level
            )
            elapsed = time.perf_counter() - start
            translate_results[level] = (elapsed, len(mapping))
            print(f"{elapsed:.3f}s  ({len(mapping)} resolved)")

        # --- Combined table ---
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        hdr = (
            f"{'Concurrency':>12} │"
            f" {'content_infos':>14} {'speedup':>8} │"
            f" {'translate_ids':>14} {'speedup':>8}"
        )
        print(hdr)
        print("─" * len(hdr))
        ci_baseline = content_results[CONCURRENCY_LEVELS[0]][0]
        tr_baseline = translate_results[CONCURRENCY_LEVELS[0]][0]
        for level in CONCURRENCY_LEVELS:
            ci_t, _ = content_results[level]
            tr_t, _ = translate_results[level]
            print(
                f"{level:>12} │"
                f" {ci_t:>13.3f}s {ci_baseline / ci_t:>7.2f}x │"
                f" {tr_t:>13.3f}s {tr_baseline / tr_t:>7.2f}x"
            )

        # --- Plots (2x2: log-log and linear for each function) ---
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        benchmarks = [
            ("get_content_infos_async", content_results, "tab:blue"),
            (
                "_translate_scope_ids_async",
                translate_results,
                "tab:orange",
            ),
        ]

        for row, (name, res, color) in enumerate(benchmarks):
            levels = CONCURRENCY_LEVELS
            times = [res[l][0] for l in levels]
            baseline = times[0]
            ideal = [baseline / l for l in levels]

            # log-log
            ax = axes[row][0]
            ax.plot(levels, times, "o-", linewidth=2, markersize=8, color=color)
            ax.plot(levels, ideal, "k--", alpha=0.3, label="ideal 1/x")
            ax.set_xscale("log", base=3)
            ax.set_yscale("log")
            ax.set_xlabel("max_concurrent_requests")
            ax.set_ylabel("Time (s)")
            ax.set_title(f"{name} (log-log)")
            ax.set_xticks(levels)
            ax.set_xticklabels([str(l) for l in levels])
            ax.grid(True, which="both", ls="--", alpha=0.5)
            ax.legend()

            # linear
            ax = axes[row][1]
            ax.plot(levels, times, "o-", linewidth=2, markersize=8, color=color)
            ax.plot(levels, ideal, "k--", alpha=0.3, label="ideal 1/x")
            ax.set_xlabel("max_concurrent_requests")
            ax.set_ylabel("Time (s)")
            ax.set_title(f"{name} (linear)")
            ax.set_xticks(levels)
            ax.grid(True, which="both", ls="--", alpha=0.5)
            ax.legend()

        fig.tight_layout()
        out_path = project_root / "concurrency_benchmark.png"
        fig.savefig(out_path, dpi=150)
        print(f"\nPlot saved to {out_path}")
        plt.show()

    asyncio.run(main())
