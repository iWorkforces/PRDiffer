---
name: review_pr
description: Review PR with given pr_url
argument-hint: "<pr_url>"
---

Review the pull request identified by `$1`. `$1` is the sole argument and is
`pr_url`. No other argument is accepted.

1. Validate that `pr_url` is an absolute review URL matching either accepted
   pattern: GitHub: `https://github.com/<owner>/<repository>/pull/<number>`;
   GitLab: `https://<gitlab-host>/<namespace>/<project>/-/merge_requests/<number>`.
   For a GitHub URL, extract `pr_number` from the decimal path segment after
   `/pull/`. For a GitLab URL, extract `pr_number` from the decimal path segment
   after `/-/merge_requests/`. Ignore query strings, fragments, trailing slashes,
   and any further path segments after that number for either pattern. Stop with
   a clear error before fetching or writing a report if neither valid numeric
   pattern is present. The report path is exactly
   `pr-{pr_number}-review-report.yml` in the current working directory.
2. Call `prdiffer_get_pr_diff` with `pr_url` set to `$1`. If the fetch fails,
   is incomplete, or does not expose `result.files`, stop immediately without
   creating or changing the report.
3. Review every entry in `result.files`. For each one, inspect its `path`,
   `previous_path` when present, `status`, `stats`, and complete full-context
   `diff`. Review the entire changed-file content represented by that complete
   full-context diff from its first line through its last line, not merely its
   hunks or changed lines. Do not skip any file type or status.
4. For each changed file, use LSP diagnostics, definitions, references, and
   symbols as relevant and where supported to inspect the local code context.
   For every definition, reference, or symbol consulted, read the relevant
   source content at that location in the related local source file; an LSP
   result location alone is not sufficient context to decide whether an issue
   exists. If LSP is unavailable, unsupported, or the file was deleted,
   continue the manual full-file review of the complete full-context diff from
   first line through last line. Finish reviewing every changed file before any
   report write.
5. Record only confirmed, concrete, actionable defects. Do not record
   placeholders, speculation, style-only feedback, or informational notes.
   Every finding must identify a precise inclusive line range. Use lines from
   the new side for added, modified, and renamed files, and lines from the old
   side for deleted files.
6. Only after all files have been reviewed, read the existing
   `pr-{pr_number}-review-report.yml` if it exists. Preserve its prior
   findings. It must be valid YAML whose only top-level key is a `findings`
   sequence. If the existing report is malformed or incompatible with this
   structure, stop with a clear error and do not overwrite it.
7. Append only non-duplicate confirmed findings to that sole `findings`
   sequence. For every finding, set `relevant_file` to the `path` of the
   currently examined `result.files` entry; never use another file's path or
   its `previous_path`. Each finding must use exactly these keys:

   ```yaml
   - relevant_file: |
       path/to/file
     issue_header: |
       Short actionable title
     issue_content: |
       Explain the defect, impact, and correction needed.
     start_line: 1
     end_line: 1
   ```

   `issue_content` must always be a YAML literal block. Do not add required
   finding keys beyond `relevant_file`, `issue_header`, `issue_content`,
   `start_line`, and `end_line`.
8. If there are no new findings, leave an existing report unchanged. If there
   is no existing report, create it with exactly:

   ```yaml
   findings: []
   ```

9. Re-read the final report file and run LSP diagnostics on it. Report the
   review result, including any findings written or the clean-review outcome.
