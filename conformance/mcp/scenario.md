You are connected to an MCP server named `wiki-studio` that curates a small
markdown wiki. Use only its tools, in this order, and stop after step 6.

1. Call `find` with the question "How do we retry outbound calls?".
2. Call `read_page` on `decisions/retry-policy.md`. Keep the `sha256` it returns.
3. Write a new version of that page: keep its frontmatter and every section
   heading exactly as they are, and change only the text under
   `## Decision` to "Retry outbound calls with exponential backoff, starting
   at 250 ms, at most five times."
4. Call `propose` with one edit: `path` `decisions/retry-policy.md`, `action`
   `update`, `content` the whole new page, and `base_sha256` the `sha256`
   from step 2. Use the name `host-run-update` and a one-sentence rationale.
5. Call `promote` with the name `host-run-update`.
6. Call `review_state` with `pages` `["decisions/retry-policy.md"]` and report
   the page's `state`.

Do not call any other tool, do not retry a failed step, and do not edit any
file yourself. If a step fails, report its error and stop.
