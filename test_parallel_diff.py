#!/usr/bin/env python3
"""Simple test to validate parallel diff generation implementation."""

import sys
from ccpragents.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from ccpragents.infrastructure.github.diff_generator import get_diff_generator
from ccpragents.infrastructure.github.parallel_executor import get_parallel_executor
from ccpragents.infrastructure.utils.diff_utils import get_diff_utils


def create_test_file(index: int) -> FilePatchInfo:
    """Create a test FilePatchInfo object."""
    base_content = f"line 1\nline 2\nline 3 original {index}\nline 4\n"
    head_content = f"line 1\nline 2\nline 3 modified {index}\nline 4\nline 5 added\n"
    patch = f"""@@ -1,4 +1,5 @@
 line 1
 line 2
-line 3 original {index}
+line 3 modified {index}
 line 4
+line 5 added
"""

    return FilePatchInfo(
        base_file=base_content,
        head_file=head_content,
        patch=patch,
        filename=f"test_file_{index}.py",
        edit_type=EDIT_TYPE.MODIFIED,
        num_plus_lines=2,
        num_minus_lines=1,
    )


def test_sequential_processing():
    """Test sequential diff generation."""
    print("🔍 Testing sequential diff generation...")

    diff_utils = get_diff_utils()
    diff_generator = get_diff_generator(
        diff_utils=diff_utils,
        parallel_executor=None,  # No parallel executor
        parallel_enabled=False,
    )

    # Create 2 test files (below threshold)
    test_files = [create_test_file(i) for i in range(2)]

    result = diff_generator.generate_extended_diff(test_files)

    assert len(result) == 2, f"Expected 2 results, got {len(result)}"
    assert all(isinstance(r, str) for r in result), "All results should be strings"
    assert all("test_file_" in r for r in result), "Results should contain filenames"

    print("✅ Sequential processing test passed")
    return True


def test_parallel_processing():
    """Test parallel diff generation."""
    print("🔍 Testing parallel diff generation...")

    diff_utils = get_diff_utils()
    parallel_executor = get_parallel_executor(max_workers=4, timeout=30.0)
    diff_generator = get_diff_generator(
        diff_utils=diff_utils,
        parallel_executor=parallel_executor,
        parallel_enabled=True,
        parallel_threshold=3,  # Use parallel for 3+ files
    )

    # Create 5 test files (above threshold)
    test_files = [create_test_file(i) for i in range(5)]

    result = diff_generator.generate_extended_diff(test_files)

    assert len(result) == 5, f"Expected 5 results, got {len(result)}"
    assert all(isinstance(r, str) for r in result), "All results should be strings"
    assert all("test_file_" in r for r in result), "Results should contain filenames"

    # Verify order is preserved
    for i, r in enumerate(result):
        assert f"test_file_{i}.py" in r, f"File order not preserved at index {i}"

    print("✅ Parallel processing test passed")
    return True


def test_adaptive_strategy():
    """Test adaptive strategy (switching between sequential and parallel)."""
    print("🔍 Testing adaptive strategy...")

    diff_utils = get_diff_utils()
    parallel_executor = get_parallel_executor(max_workers=4, timeout=30.0)
    diff_generator = get_diff_generator(
        diff_utils=diff_utils,
        parallel_executor=parallel_executor,
        parallel_enabled=True,
        parallel_threshold=3,
    )

    # Test with 2 files (below threshold - should use sequential)
    test_files_small = [create_test_file(i) for i in range(2)]
    result_small = diff_generator.generate_extended_diff(test_files_small)
    assert len(result_small) == 2, "Small set should process all files"

    # Test with 5 files (above threshold - should use parallel)
    test_files_large = [create_test_file(i) for i in range(5)]
    result_large = diff_generator.generate_extended_diff(test_files_large)
    assert len(result_large) == 5, "Large set should process all files"

    print("✅ Adaptive strategy test passed")
    return True


def test_output_consistency():
    """Test that sequential and parallel produce consistent results."""
    print("🔍 Testing output consistency between sequential and parallel...")

    diff_utils = get_diff_utils()

    # Create test files
    test_files = [create_test_file(i) for i in range(5)]

    # Sequential processing
    diff_generator_seq = get_diff_generator(
        diff_utils=diff_utils,
        parallel_executor=None,
        parallel_enabled=False,
    )
    result_seq = diff_generator_seq.generate_extended_diff(test_files)

    # Parallel processing
    parallel_executor = get_parallel_executor(max_workers=4, timeout=30.0)
    diff_generator_par = get_diff_generator(
        diff_utils=diff_utils,
        parallel_executor=parallel_executor,
        parallel_enabled=True,
        parallel_threshold=1,  # Always use parallel
    )
    result_par = diff_generator_par.generate_extended_diff(test_files)

    # Compare results
    assert len(result_seq) == len(result_par), "Result counts should match"

    for i, (seq, par) in enumerate(zip(result_seq, result_par)):
        # Results should be identical
        assert seq == par, f"Results differ at index {i}"

    print("✅ Output consistency test passed")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 Parallel Diff Generation Validation Tests")
    print("="*60 + "\n")

    tests = [
        ("Sequential Processing", test_sequential_processing),
        ("Parallel Processing", test_parallel_processing),
        ("Adaptive Strategy", test_adaptive_strategy),
        ("Output Consistency", test_output_consistency),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n📋 Running: {test_name}")
            print("-" * 60)
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} failed")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} failed with error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    if failed > 0:
        print("❌ Some tests failed")
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
