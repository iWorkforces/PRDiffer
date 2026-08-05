"""Tests for the strict-v1 full-diff benchmark harness.

Validates fixture determinism, mode selection markers, overwrite refusal,
and preflight failure before any timing runs.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BENCH_PATH = ROOT / "scripts" / "bench_diff_generation.py"


def _load_bench():
    """Load the benchmark script as a module without requiring scripts package."""
    name = "bench_diff_generation_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, BENCH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bench = _load_bench()


@pytest.fixture
def medium_fixture():
    return bench.build_fixture(bench.STRICT_V1_WORKLOADS["medium"], seed=bench.DEFAULT_SEED)


class TestStrictV1MatrixDefinition:
    def test_matrix_workloads_match_plan(self) -> None:
        assert set(bench.STRICT_V1_WORKLOADS) == {"medium", "large", "pathological"}
        medium = bench.STRICT_V1_WORKLOADS["medium"]
        assert (medium.files, medium.lines, medium.samples) == (25, 200, 5)
        large = bench.STRICT_V1_WORKLOADS["large"]
        assert (large.files, large.lines, large.samples) == (250, 1000, 5)
        pathological = bench.STRICT_V1_WORKLOADS["pathological"]
        assert (pathological.files, pathological.lines, pathological.samples) == (10, 5000, 3)
        assert pathological.style == "pathological"
        assert bench.DEFAULT_SEED == 5020
        assert bench.WARMUPS == 1

    def test_baseline_and_post_modes_are_disjoint_labels(self) -> None:
        assert bench.BASELINE_MODES.isdisjoint(bench.POST_CHANGE_MODES)
        assert "sync-current" in bench.BASELINE_MODES
        assert "async-current-negative-control" in bench.BASELINE_MODES
        assert "serialized-worker-1" in bench.POST_CHANGE_MODES
        assert "bounded-worker-2" in bench.POST_CHANGE_MODES
        assert "bounded-worker-4" in bench.POST_CHANGE_MODES


class TestFixtureValidity:
    def test_fixture_has_full_name_and_pages(self, medium_fixture) -> None:
        assert medium_fixture.repository.full_name == "bench-owner/bench-repo"
        assert len(medium_fixture.files) == 25
        assert len(medium_fixture.pages) >= 1
        assert medium_fixture.manifest["ordered_paths"][0].startswith("src/module_")
        bench.validate_fixture(medium_fixture)

    def test_fixture_digest_is_stable_across_builds(self) -> None:
        a = bench.build_fixture(bench.STRICT_V1_WORKLOADS["medium"], seed=5020)
        b = bench.build_fixture(bench.STRICT_V1_WORKLOADS["medium"], seed=5020)
        assert a.fixture_digest == b.fixture_digest
        assert a.manifest["ordered_paths"] == b.manifest["ordered_paths"]

    def test_invalid_workload_fails_before_timing(self) -> None:
        bad = bench.WorkloadSpec(name="medium", files=0, lines=200, samples=5)
        with pytest.raises(ValueError, match="positive"):
            bench.build_fixture(bad, seed=5020)

    def test_validate_fixture_rejects_digest_tamper(self, medium_fixture) -> None:
        tampered = bench.FixtureBundle(
            workload=medium_fixture.workload,
            seed=medium_fixture.seed,
            repository=medium_fixture.repository,
            base_sha=medium_fixture.base_sha,
            head_sha=medium_fixture.head_sha,
            files=medium_fixture.files,
            content_map=medium_fixture.content_map,
            pages=medium_fixture.pages,
            manifest=dict(medium_fixture.manifest),
            fixture_digest="0" * 64,
        )
        with pytest.raises(ValueError, match="digest"):
            bench.validate_fixture(tampered)


class TestModeSelectionMarkers:
    def test_post_modes_unsupported_during_baseline(self, medium_fixture) -> None:
        result = bench.run_mode("serialized-worker-1", medium_fixture, phase="baseline")
        assert result.supported is False
        assert result.validity["status"] == "unsupported"
        assert result.samples == []

    def test_sync_current_supported_and_emits_samples(self) -> None:
        tiny = bench.WorkloadSpec(name="medium", files=2, lines=20, samples=2)
        bundle = bench.build_fixture(tiny, seed=5020)
        result = bench.run_mode("sync-current", bundle, phase="baseline")
        assert result.supported is True
        assert len(result.samples) == 2  # warmups excluded
        assert result.validity["status"] == "ok"
        assert result.validity["stable_output_digest"] is True
        assert all(s.api_calls >= 1 for s in result.samples)
        assert all(s.page_fetches >= 1 for s in result.samples)
        assert all(s.output_digest for s in result.samples)

    def test_negative_control_marks_blocking_not_safety(self) -> None:
        tiny = bench.WorkloadSpec(name="medium", files=1, lines=10, samples=1)
        bundle = bench.build_fixture(tiny, seed=5020)
        result = bench.run_mode("async-current-negative-control", bundle, phase="baseline")
        assert result.supported is True
        assert result.validity["status"] == "negative-control"
        assert result.validity["claims_event_loop_safety"] is False
        assert "event_loop_blocking_observed" in result.validity


class TestArtifactIO:
    def test_write_json_refuses_overwrite(self, tmp_path: Path) -> None:
        path = tmp_path / "baseline.json"
        payload = {"hello": "world"}
        digest1 = bench.write_json_atomic(path, payload, allow_overwrite=False)
        assert path.exists()
        assert len(digest1) == 64
        with pytest.raises(FileExistsError, match="Refusing to overwrite"):
            bench.write_json_atomic(path, {"hello": "again"}, allow_overwrite=False)

    def test_write_json_allow_overwrite(self, tmp_path: Path) -> None:
        path = tmp_path / "report.json"
        bench.write_json_atomic(path, {"v": 1}, allow_overwrite=False)
        digest = bench.write_json_atomic(path, {"v": 2}, allow_overwrite=True)
        assert json.loads(path.read_text(encoding="utf-8"))["v"] == 2
        assert len(digest) == 64

    def test_main_overwrite_refusal_exit_code(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "task-1.baseline.json"
        path.write_text("{}", encoding="utf-8")

        # Avoid heavy real runs — stub run_matrix so we only exercise overwrite policy.
        monkeypatch.setattr(
            bench,
            "run_matrix",
            lambda **kwargs: {
                "schema_version": 1,
                "matrix": "strict-v1",
                "phase": "baseline",
                "seed": 5020,
                "workloads": {},
                "network_calls": 0,
            },
        )
        code = bench.main(
            [
                "--matrix",
                "strict-v1",
                "--phase",
                "baseline",
                "--modes",
                "sync-current",
                "--json",
                str(path),
            ]
        )
        assert code == 1


class TestRunMatrixSchema:
    def test_run_matrix_tiny_subset_schema(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(
            bench.STRICT_V1_WORKLOADS,
            "medium",
            bench.WorkloadSpec(name="medium", files=2, lines=15, samples=2),
        )
        # Keep only medium in this test.
        for name in list(bench.STRICT_V1_WORKLOADS):
            if name != "medium":
                monkeypatch.delitem(bench.STRICT_V1_WORKLOADS, name)

        report = bench.run_matrix(
            matrix="strict-v1",
            phase="baseline",
            modes=["sync-current", "async-current-negative-control"],
            seed=5020,
            workloads=["medium"],
        )

        assert report["schema_version"] == 1
        assert report["matrix"] == "strict-v1"
        assert report["phase"] == "baseline"
        assert report["seed"] == 5020
        assert report["warmups"] == 1
        assert report["network_calls"] == 0
        assert "medium" in report["workloads"]
        medium = report["workloads"]["medium"]
        assert "fixture_digest" in medium
        assert "fixture_manifest" in medium
        assert set(medium["modes"]) == {"sync-current", "async-current-negative-control"}
        sync = medium["modes"]["sync-current"]
        assert sync["supported"] is True
        assert len(sync["samples"]) == 2
        sample = sync["samples"][0]
        for key in (
            "wall_seconds",
            "cpu_seconds",
            "tracemalloc_peak_bytes",
            "rss_delta_bytes",
            "api_calls",
            "page_fetches",
            "bytes_read",
            "max_in_flight",
            "output_digest",
            "output_manifest",
        ):
            assert key in sample
        neg = medium["modes"]["async-current-negative-control"]
        assert neg["validity"]["claims_event_loop_safety"] is False
