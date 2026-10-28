You are connected to an MCP server named `wiki-studio` that curates a small
markdown wiki. Use only its tools, in this order, and stop after step 10.

1. Call `find` with the question "How do we retry outbound calls?".
2. Call `read_page` on `decisions/retry-policy.md`. Keep the `sha256` it returns.
3. Call `read_page` on `../outside.md`. The server must refuse this call with
   an error whose `exit_code` is 7. Report the refusal and continue with
   step 4.
4. Write a new version of the page from step 2: keep its frontmatter and
   every section heading exactly as they are, and change only the text under
   `## Decision` to "Retry outbound calls with exponential backoff, starting
   at 250 ms, at most five times."
5. Call `propose` with one edit: `path` `decisions/retry-policy.md`, `action`
   `update`, `content` the whole new page, and `base_sha256` the `sha256`
   from step 2. Use the name `host-run-update` and a one-sentence rationale.
6. Call `promote` with the name `host-run-update`.
7. Call `review_state` with `pages` `["decisions/retry-policy.md"]` and report
   the page's `state`.
8. Call `propose` again with one edit: `path` `decisions/retry-policy.md`,
   `action` `update`, `content` the whole new page from step 4, and
   `base_sha256` the `sha256` from step 2 again (the page has changed since
   step 6, so that hash is stale). Use the name `host-run-stale` and a
   one-sentence rationale. This call succeeds.
9. Call `promote` with the name `host-run-stale`. The server must refuse this
   call with an error whose `exit_code` is 9. Report the refusal and continue
   with step 10.
10. Call `promote` with the name `../x`. The server must refuse this call
    with an error whose `exit_code` is 1 (a `ValueError`). Report the
    refusal and stop.

Do not call any other tool, do not retry a failed step, and do not edit any
file yourself. Steps 3, 9 and 10 are the only steps that are expected to
fail. If any other step fails, report its error and stop.
