#!/usr/bin/env python3
"""Simple local benchmarks for diff generation and file processing."""

import argparse
import time
from dataclasses import dataclass
from typing import cast

from prdiffer.domain.entities.file_patch import FilePatchInfo, EDIT_TYPE
from prdiffer.domain.entities import (
    Repository as DomainRepository,
    PullRequest as DomainPullRequest,
)
from prdiffer.domain.services.github_api import GitHubAPIServiceInterface
from prdiffer.domain.services.pattern_matching import PatternMatchingServiceInterface
from prdiffer.infrastructure.github.diff_generator import DiffGenerator
from prdiffer.infrastructure.github.file_processor import FileProcessor
from prdiffer.infrastructure.utils.diff_utils import DiffUtils
from github.File import File
from github.Repository import Repository as PyGithubRepository


@dataclass
class FakeFile:
    filename: str
    status: str
    patch: str | None
    additions: int
    deletions: int


class DummyPatternMatcher(PatternMatchingServiceInterface):
    def is_valid_file(self, filename: str) -> bool:
        return True

    def filter_files(self, filenames: list[str]) -> list[str]:
        return list(filenames)


class DummyAPIService(GitHubAPIServiceInterface):
    def __init__(self, content_map: dict[tuple[str, str], str]):
        self._content_map = content_map

    def initialize_client(self, github_token: str | None = None, timeout: int = 30):
        return None

    def get_repository(self, repo_full_name: str) -> DomainRepository | None:
        return None

    def get_pull_request(self, repo_full_name: str, pr_number: int) -> DomainPullRequest | None:
        return None

    def get_file_content(self, repo_full_name: str, file_path: str, branch: str) -> str:
        return self._content_map.get((file_path, branch), '')

    def get_files_content_batch(self, repo_full_name: str, file_paths: list[str], branch: str):
        return {path: self.get_file_content(repo_full_name, path, branch) for path in file_paths}

    def get_files_content_batch_parallel(
        self,
        repo_full_name: str,
        file_paths: list[str],
        branch: str,
        max_workers: int = 4,
    ):
        return self.get_files_content_batch(repo_full_name, file_paths, branch)


def build_fake_files(diff_utils: DiffUtils, count: int, lines: int) -> tuple[list[FakeFile], list[FilePatchInfo], dict]:
    base_content = '\n'.join(['line'] * lines) + '\n'
    head_content = base_content + 'extra\n'
    patch = diff_utils.build_full_file_patch(base_content, head_content)

    files = []
    patch_infos = []
    content_map = {}
    for i in range(count):
        filename = f'file_{i}.py'
        files.append(
            FakeFile(
                filename=filename,
                status='modified',
                patch=None,
                additions=1,
                deletions=0,
            )
        )
        patch_infos.append(
            FilePatchInfo(
                filename=filename,
                base_file=base_content,
                head_file=head_content,
                patch=patch,
                edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=1,
                num_minus_lines=0,
            )
        )
        content_map[(filename, 'base')] = base_content
        content_map[(filename, 'head')] = head_content

    return files, patch_infos, content_map


def benchmark_diff_generation(diff_utils: DiffUtils, patch_infos: list[FilePatchInfo]) -> float:
    generator = DiffGenerator(diff_utils=diff_utils, parallel_executor=None, parallel_enabled=False)
    start = time.perf_counter()
    generator.generate_extended_diff(patch_infos)
    return time.perf_counter() - start


def benchmark_file_processing(
    diff_utils: DiffUtils,
    files: list[FakeFile],
    content_map: dict,
    parallel_threshold: int,
    max_workers: int,
) -> float:
    processor = FileProcessor(
        github_api_service=DummyAPIService(content_map),
        pattern_matcher=DummyPatternMatcher(),
        diff_utils=diff_utils,
        parallel_fetch_threshold=parallel_threshold,
        max_parallel_workers=max_workers,
    )
    start = time.perf_counter()
    processor.process_files_to_patches(
        cast(list[File], files),
        repository=cast(PyGithubRepository, object()),
        head_sha='head',
        base_sha='base',
    )
    return time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', type=int, default=25)
    parser.add_argument('--lines', type=int, default=200)
    parser.add_argument('--parallel-threshold', type=int, default=10)
    parser.add_argument('--parallel-workers', type=int, default=4)
    args = parser.parse_args()

    diff_utils = DiffUtils()
    files, patch_infos, content_map = build_fake_files(diff_utils, args.files, args.lines)

    diff_time = benchmark_diff_generation(diff_utils, patch_infos)
    seq_time = benchmark_file_processing(diff_utils, files, content_map, parallel_threshold=0, max_workers=1)
    par_time = benchmark_file_processing(
        diff_utils,
        files,
        content_map,
        parallel_threshold=args.parallel_threshold,
        max_workers=args.parallel_workers,
    )

    print(f'Diff generation: {diff_time:.3f}s for {args.files} files')
    print(f'File processing (sequential): {seq_time:.3f}s')
    print(f'File processing (parallel): {par_time:.3f}s')


if __name__ == '__main__':
    main()
