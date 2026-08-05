# AGENTS.md - GitHub Infrastructure Unit Tests

7 files, ~2.7K lines.

## STRUCTURE
```
tests/unit/infrastructure/github/
├── test_api_client.py                     # 130
├── test_api_client_comprehensive.py       # 506
├── test_file_processor.py                 # 208
├── test_file_processor_comprehensive.py   # 556
├── test_diff_generator.py                 # 101
├── test_diff_generator_comprehensive.py   # 743
└── test_github_mappers.py                 # 417
```

## CONVENTIONS
- Basic vs comprehensive split: happy path vs edge/error branches.
- Mock `github.Github` hierarchy; assert our wrapper behavior.

## ANTI-PATTERNS
- NO real GitHub network.
