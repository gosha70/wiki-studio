# The near-duplicate study (issue 121)

Issue 121 asks whether wiki-studio's `findings` can tell a curator, without a
model, that two pages record the same decision in different words. The issue 54
study measured one signal for it, signal (b): the Jaccard similarity of the
title and the first paragraph of `## Decision`, at 0.25. It found 2 of 3 true
pairs with 1 false candidate. Three labelled pairs support no estimate. This
directory holds the follow-up measurement on a larger corpus whose labels are
frozen before any candidate runs. The bet pitch
`specs/pitches/121-near-duplicate-finding/pitch.md` shapes it, and
`specs/wiki-studio-duplicates-121/` specifies it.

- **wiki-studio commit read**: the branch base,
  `421b6f680f5ec1c35f776d88324745acd5b244a9` (`main` after the spec's
  approval).
- **What is measured**: for each of the two candidates (B0, the issue 54
  signal (b) exactly, and B1, B0 with a text normalisation, both fixed when
  the labels are frozen), the true pairs found out of n and the false
  candidates over every pair of the corpus. The counts are split by
  disposition, by pair scope (within a family, across the families of one
  repository, across the two repositories) and by repository, and also given
  per 100 pages.
- **What is not measured**: a precision or recall estimate (recall is a count
  out of n); page types other than `decision`; curated pages (the pages are
  extracted from specs, not curated: pitch finding 14); agent behaviour.
- `eval/patterns/` is read and never edited. Its `_first_paragraph` and
  `_title` are imported read-only, so a page here is read exactly as the
  issue 54 scorer reads one.
- No result depends on a model. No script here calls one.

Files written by this directory's scripts:

| File | Written by | What it holds |
|---|---|---|
| `extract.py` | | the extraction rule below, as code |
| `sample.py` | | the owner's review sample rule (FR-008), as code |
| `corpus/<repository>/<family>/<slug>.md` | `extract.py`, run once by hand | one decision page per extracted item |
| `corpus.json` | `extract.py`, run once by hand | the pins, the options, the families, one entry per page, the left-out items |
| `review-sample.json` | `sample.py`, run once by hand | the seed, the split, the labels' sha256, 20 false pairs |

`labels.json` is written by hand in the labelling session, with no script
(see "The labels" below). The protocol, the scorer, its results and the
report are added by later steps of the spec. No driver session runs these
scripts. The main
session or the owner runs each one once at a milestone pause and commits its
output exactly as written.

## The corpus rule

### Sources and pins (FR-002)

| Repository | Pin | Commit date (`%cs`) | Default checkout |
|---|---|---|---|
| code-copilot-team | `fd05256b107889853068e81aca1cf7c60419e37e` | 2026-11-22 | `../code-copilot-team` |
| memkernel | `8279d7631851584a939a03d6243df57a4cc25c31` | 2026-11-23 | `../memkernel` |

The pins were resolved by hand in this phase with read-only
`git rev-parse --verify <pin>^{commit}`, and the dates come from
`git log -1 --format=%cs <pin>`. Both are written in `extract.py` as named
constants (`PINS`). `extract.py` reads each repository only through
`git -C <checkout>` with four read-only commands:
`rev-parse --verify <pin>^{commit}`, `ls-tree -r --name-only <pin> -- specs`,
`show <pin>:<path>` and `log -1 --format=%cs <pin>`. Each call is an argument
list through `subprocess.run`, never a shell. It has the prefix
`--no-pager -c core.fsmonitor=false -c core.hooksPath=<devnull> -c protocol.allow=never`
and an environment built from `os.environ` without any inherited `GIT_`
variable except `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM` and
`GIT_CONFIG_NOSYSTEM`, with `GIT_CEILING_DIRECTORIES` set to the checkout's
parent. Nothing is fetched, no working tree is read, and nothing is written to
either repository. The script writes only under `--out`. The exit codes:

- 2: a pin does not resolve to exactly that commit.
- 3: a git call fails.
- 4: `<out>/corpus/` holds a file this run would not rewrite. The script
  deletes nothing, so a narrower rerun over a wider corpus stops here.

In each of these cases nothing is written. An argument error (such as an
`--extend` out of range) also exits 2, argparse's usage-error code, before any
git call. `corpus.json` is rewritten on every successful run; only files under
`corpus/` are checked.

### Families (FR-003)

The base is code-copilot-team's `routing` and `pi` families and memkernel as
one family, `memkernel`. A code-copilot-team spec directory belongs to family
F when its name equals F or starts with `F-`. A directory is extracted only
when its `plan.md` or `spec.md` holds a decision section (FR-004).

The directory lists below were read offline with `ls-tree` and `show` at the
pins. `corpus.json` records the same lists, as `extract.py` finds them, under
`families`.

**routing**: 11 directories by the prefix rule. Ten of them hold a decision
section, the same count as the pitch's 10:

- With decision sections: `routing-calibration`, `routing-context-limit`,
  `routing-effective-endpoint` (in both `plan.md` and `spec.md`),
  `routing-eval`, `routing-profile-foundation`, `routing-recovery`,
  `routing-shadow`, `routing-tier1-failover`, `routing-tier2-delegation`,
  `routing-usage-evidence`.
- Without one: `routing-codex-backend` (a `plan.md` with no H2 naming a
  decision).

**pi**: 9 directories by the prefix rule. Five of them hold a decision
section, the same count as the pitch's 5:

- With decision sections: `pi-harness-adoption`, `pi-project-config`,
  `pi-sandbox-hardening`, `pi-team-controller` (two decision sections),
  `pi-worktree-lifecycle`.
- Without one: `pi-extension-templates`, `pi-team-plane-b1`,
  `pi-team-plane-b2c`, `pi-team-plane-d`. Their decisions sit under H3
  headings of `## Design`, not under an H2 that names a decision.

**memkernel**: every spec directory at the pin with a decision section,
except the exclusions. Twenty hold one; two are excluded, which leaves the
pitch's 18: `copilot-memory-mvp`, `memkernel-0-3`, `memkernel-0-4`,
`memkernel-0-7`, `memkernel-0-7-governed`, `memkernel-0-7-hooks`,
`memkernel-0-7-release-b-exit`, `memkernel-0-7-store-locks`,
`memkernel-0-7-wiki-scope`, `memkernel-0-7-wiring-spool`,
`memkernel-0-8-untrusted-memory`, `memkernel-0-9-mcp2`,
`memkernel-0-10-recall-log`, `memkernel-0-12-capture-core`,
`memkernel-0-13-one-store-across-tools`, `memkernel-0-14-capture-signals`,
`memkernel-0-15-harness-foundations`, `memkernel-0-16-lifecycle-corrections`.

These are directory counts; the page counts come from the extraction run.
Their differences from the pitch's page counts are reported under "The
extracted corpus" below, and the rule is not tuned to remove them.

### Exclusions (FR-003; pitch finding 11)

An excluded spec is never extracted, by any option. The list is fixed in
`extract.py` (`EXCLUDED_FAMILIES`, `EXCLUDED_SPECS`):

| Repository | Excluded | Reason | The check that found it |
|---|---|---|---|
| code-copilot-team | the `session-analytics` family | the issue 54 records were drawn from it | the 12 records of `eval/patterns/corpus/decisions-57.md` cite `specs/session-analytics-trace-archive`, `-similarity-ui`, `-benchmark-step` and `-benchmark-ui` (a grep for `specs/` paths in that file, re-run in this phase) |
| code-copilot-team | the `benchmark` family | the issue 54 records were drawn from it | the same grep: `specs/benchmark-adapters-backends`, `specs/benchmark-llm-judge` |
| code-copilot-team | the `auto-build` family | the issue 54 records were drawn from it | the same grep: `specs/auto-build-loop-merge-profile` |
| code-copilot-team | `init-permission-profiles` | cited by an issue 54 record | the same grep: `specs/init-permission-profiles` |
| code-copilot-team | `redaction-canaries` | the same topic as two issue 54 records (redaction of configuration and of archived traces) | the pitch's reading of the records against code-copilot-team's spec list |
| memkernel | `memkernel-0-10-decision-revalidation` | evaluates on the issue 54 corpus | a scan of memkernel's spec files at the pin for `decisions-57` (re-run in this phase) finds exactly these two |
| memkernel | `memkernel-0-11-anti-rot-injection` | evaluates on the issue 54 corpus | the same scan |

The issue 54 fixture's background pages cite four more code-copilot-team
specs: `infra-verification-gate`, `origin-confirmation-circuit-breaker`,
`prefill-decode-telemetry` and `wiki-ingest-pipeline`. None of them is in a
base family or in the extension order, so none can enter the corpus. The
pitch also scanned memkernel's specs for the records' distinctive terms and
found no further overlap.

### The extension order (FR-003)

If the labelled base holds fewer than 8 true pairs, `--extend N` adds the
first N steps below, each step its own family, before the freeze. The
excluded families are never added. Each step's directories, all with a
decision section at the pin, are:

1. `api`: `api-host-origin-guard`, `api-probe-dsn-constraints`,
   `api-probe-error-hardening` (each `plan.md`).
2. `llm-catalog`: `llm-catalog` (`plan.md` and `spec.md`).
3. `wiki-studio-adoption`: `wiki-studio-adoption` (`plan.md`).
4. `wiki-audit`: `wiki-audit-flush` and `wiki-audit-trail` (each `spec.md`).
5. `memkernel-integration`: `memkernel-integration` (`plan.md`).
6. `one-harness-home`: `one-harness-home` (`spec.md`).
7. `plugin-generate-from-sources`: `plugin-generate-from-sources`
   (`plan.md`).
8. `simplest-complete-change`: `simplest-complete-change` (`plan.md`).

### Cut 1 (FR-003)

`--cut-1` is used only if the owner invokes the circuit breaker's first cut.
It narrows code-copilot-team to `routing` and leaves out memkernel's
`copilot-memory-mvp`, `memkernel-0-3` and `memkernel-0-4` (the three pre-0.7
plans whose decisions are H3 ADRs). The extension order still applies.

### Items left out for closing-keyword text (FR-007)

An item whose text matches the pattern below is not written as a page:

```
(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b:?\s+(?:[\w.-]+/[\w.-]+)?#\d+
```

The pattern means a closing verb (close, fix or resolve, in any of their
forms) followed by an issue reference. Such an item is listed in
`corpus.json` under `left_out` by repository, spec path, line span and slug
only, with the reason `closing-keyword text`. Its text is never copied
anywhere. The pitch knows of one, in memkernel's
`memkernel-0-16-lifecycle-corrections`. The item is found by the pattern at
extraction, so a second one could not slip in. A left-out item still takes
its ordinal, so the slugs of the other items do not depend on it.

## The extraction rule, step by step (FR-004 to FR-007)

The rule was fixed in this phase, before any page was extracted, and is not
tuned after any page is read. An item the rule extracts badly is still
extracted as written.

1. **Files.** `specs/<name>/plan.md`, then `specs/<name>/spec.md`, as they
   are at the pin.
2. **Fenced code.** A line whose text, after leading whitespace, starts with
   three backticks or three tildes opens a fenced block. The next line that
   starts, after leading whitespace, with the same three characters closes
   it. Headings and item starts inside a fenced block do not count.
3. **Decision sections.** A decision section is a line outside fenced code
   that starts with `## ` and whose text contains `decision` (any case). It
   runs up to the next `## ` line outside fenced code, or to the end of the
   file. All decision sections of both files are read, plan before spec.
4. **Items, by precedence within one section.**
   - If the section has H3 lines (`### ` outside fenced code), each H3 line
     with the lines up to the next H3 or the section's end is one item.
   - Otherwise, if it has bold paragraphs, each one is an item with
     everything up to the next one or the section's end, its column-0
     bullets included. A bold paragraph is a line at column 0 starting with
     `**` that is the section's first non-blank line or follows a blank line.
   - Otherwise, each column-0 list line whose text after one marker (`- `,
     `* `, `+ `, or digits followed by `.` or `)` and a space) starts with
     `**` is one item. The item runs up to the next column-0 non-blank line
     or the section's end.

   Text before the first item of a section is not an item. Trailing blank
   lines are not part of an item. An item's form is `h3`, `bold-paragraph`
   or `list-item`. An `h3` item that holds a line starting `**Decision**:`
   or `**Decision:**` (any case, after leading whitespace) has the form
   `h3-adr`. A definition or scope note extracted this way (`**Terms.**`) is
   kept and labelled by content.
5. **The label.** For an H3 form the label is the H3 line's text. For the
   other forms it is the text inside the item's first `**…**` span, with
   whitespace collapsed, since a label can wrap over two lines.
6. **The title (FR-005).** Four removals, once each and in this order:
   1. A leading identifier, matching
      `^(?:ADR-\d+|D-[a-z0-9]+(?:-[a-z0-9]+)*|[A-Z]{1,3}-?\d+(?:\.\d+)*[a-z]?)(?:[.:)])?(?:\s+[—–-])?\s*`.
      This covers `D5`, `D-upsert-key`, `S1.`, `A1`, `R2`, `ADR-1:` and
      `FR-012`.
   2. A trailing parenthetical, `\s*\([^()]*\)\s*$`. A trailing `.` or `:`
      is set aside while it is matched and put back afterwards.
   3. One trailing `.` or `:`.
   4. Surrounding whitespace.

   When nothing is left, the title is the first sentence of the item's body
   after step 7: the shortest prefix of its first non-empty paragraph
   (whitespace collapsed) that ends in `.`, `?` or `!` followed by
   whitespace or the end, or the whole paragraph when there is none. The
   title is written to the frontmatter only.
7. **The body (FR-006).** Four steps, the same for every form. No word is
   changed, added or reordered.
   1. **The label is removed.** For an H3 form this is the H3 line. For the
      other forms it is the opening bold span, with the whitespace and one
      separator character (`:`, `—`, `–` or `-`) directly after it, and the
      whitespace after that separator, all on the same line.
   2. **Indentation and one list marker are removed.** Each line outside
      fenced code loses its leading whitespace and then one leading list
      marker (`- `, `* `, `+ `, or digits followed by `.` or `)` and a
      space). Blank lines stay where they were. So a list item, its
      continuation lines and any nested items written without a blank line
      become one prose paragraph, and a bold paragraph's bullets become
      prose. Lines inside a fenced block (opened by a line that starts with
      three backticks or three tildes after this step) are copied unchanged.
      The closing fence line loses its leading whitespace, as the opening one
      did.
   3. **ADR items are split into sections.** In an `h3-adr` item, the
      `**Context**:`, `**Decision**:` and `**Consequences**:` lines (each
      also matched with the colon inside the bold, any case) lose only that
      label and the space after it. Each label's line, and the lines after it
      up to the next of the three labels, go under `## Context`,
      `## Decision` or `## Consequences`, in the order the labels appear in
      the item. Lines before the first label stay above the first section.
   4. **Everything else stays as written after step 2**: headings, tables,
      code fences and blockquotes inside an item. The scorer skips them, as
      it would on a curated page. Inline cross-references (`(D6)`, `FR-012`)
      are words of the item and stay.

   Leading and trailing blank lines of each block are dropped.
8. **The page.** The frontmatter holds these keys, then a blank line, then
   the body, then one final newline:

   ```
   ---
   page_type: decision
   slug: <slug>
   title: '<title, each single quote doubled>'
   status: stable
   last_reviewed: <the pin's commit date>
   sources:
     - path: specs/<name>/<plan.md|spec.md>
       sha: <the pin's full hash>
   ---
   ```

   For every form but `h3-adr` the body is `## Decision`, a blank line and
   the item's text after step 7. For `h3-adr` it is the sections of step 7.3,
   separated by blank lines. The title is single-quoted because
   `yaml_lite.unquote` unescapes a doubled `'` there and does not unescape a
   double-quoted scalar.
9. **The slug and the path.** The slug is `<cct|mk>-<spec name>-<plan|spec>-<nn>`,
   where `nn` is the item's 1-based ordinal among its file's items in
   document order, two digits. The page is
   `corpus/<repository>/<family>/<slug>.md`, where `<repository>` is
   `code-copilot-team` or `memkernel`.
10. **`corpus.json` (FR-007).** It holds:
    - the two repositories, with their full pins and commit dates;
    - the options the run used (`extend`, `cut_1`);
    - each family, with its directories as listed and those holding a
      decision section;
    - per page, in path order: `page` (the path under `corpus/`),
      `repository`, `family`, `spec_path`, `line_start` and `line_end` (the
      item's 1-based line span in the file at the pin), `form`, `title` and
      `sha256` (of the page's bytes), and three input counts:
      - `title_tokens` and `paragraph_tokens`: the size of
        `wiki_state._tokenise` of the title and of the paragraph that
        `eval/patterns/duplicates.py`'s `_first_paragraph` reads from the
        page;
      - `paragraph_empty`: true when that paragraph is empty;
    - `left_out`, as above.

    The counts read each page alone and compare no two pages. Nothing in
    `extract.py` computes a similarity or a candidate.

## The six fixed items (FR-009; O12)

One item per form in each repository. None of them quotes closing-keyword
text. Each one is written out in `tests/test_duplicates_extract.py` as it
reads with `git show <pin>:<path>`, with its title and the paragraph the
scorer reads written out by hand. The test builds each page with
`extract.py`'s page builder and checks the title, that the label is absent
from the body, and that `_first_paragraph` equals the first paragraph of the
item's text after its label.

code-copilot-team's base holds H3 items only in `pi-harness-adoption`'s ADR
section, so its H3 item has the form `h3-adr`, with a `**Decision**:` line
alone. Every memkernel `h3-adr` item is in a plan that cut 1 leaves out, so
under cut 1 the last item below is outside the corpus.

| Page (slug) | Repository | Form | Spec path and line span | Title |
|---|---|---|---|---|
| `cct-routing-calibration-plan-03` | code-copilot-team | list item | `specs/routing-calibration/plan.md` lines 86-96 | Reports bind to corpus AND policy |
| `cct-routing-context-limit-plan-03` | code-copilot-team | bold paragraph | `specs/routing-context-limit/plan.md` lines 97-101 | fail-closed only where a requirement exists |
| `cct-pi-harness-adoption-plan-04` | code-copilot-team | H3 (`h3-adr`) | `specs/pi-harness-adoption/plan.md` lines 115-118 | Launcher symmetry with `claude-code` |
| `mk-memkernel-0-12-capture-core-spec-01` | memkernel | list item | `specs/memkernel-0-12-capture-core/spec.md` lines 306-308 | Key |
| `mk-memkernel-0-7-wiring-spool-spec-02` | memkernel | bold paragraph | `specs/memkernel-0-7-wiring-spool/spec.md` lines 32-39 | Spool pruning |
| `mk-memkernel-0-3-plan-03` | memkernel | `h3-adr` | `specs/memkernel-0-3/plan.md` lines 72-76 | `forget_expired` leaves the MCP surface |

## The extracted corpus (FR-011)

The main session ran `python -m eval.duplicates.extract` once, with no option,
at the pause after the extraction code, and committed `corpus/` and
`corpus.json` as written: 218 pages. At the pause after the labels, with 7 true
pairs against the minimum of 8, it ran the extension rule's first step
(FR-016(a)), `python -m eval.duplicates.extract --extend 1`, which adds the
`api` family, and committed the added pages and `corpus.json` with these
counts updated. The `api` family added no true pair, so it ran the second
step, `python -m eval.duplicates.extract --extend 2`, which adds the
`llm-catalog` family, committed the same way. That family added no true pair
either, so it ran the third step, `--extend 3`, which adds the
`wiki-studio-adoption` family, committed the same way. It added no true pair
either, so it ran the fourth step, `--extend 4`, which adds the `wiki-audit`
family, committed the same way. It added no true pair either, so it ran the
fifth step, `--extend 5`, which adds the `memkernel-integration` family
committed the same way. It added no true pair either, so it ran the sixth
step, `--extend 6`, which adds the `one-harness-home` family (`extend` 6,
committed the same way. It added no true pair either, so it ran the seventh
step, `--extend 7`, which adds the `plugin-generate-from-sources` family
committed the same way. It added no true pair either, so it ran the eighth and
last step, `--extend 8`, which adds the `simplest-complete-change` family
(`extend` 8, `cut_1` false, as `corpus.json` now records), committed the same
way. The extension order is then used up. Every
number below is read from `corpus.json`, and
`tests/test_duplicates_corpus.py` recomputes each one from it.

The pages are extracted from specs, not curated (pitch finding 14). Each one
is a decision item copied by the rule above, not a page a curator wrote from
the wiki's templates. B1's drop of the template words (FR-018) is meant for
curated template pages, and this corpus holds none, so that part of B1 cannot
be measured on this corpus.

### Pages per repository, family and form

The corpus holds **299 pages**: 198 from code-copilot-team and 101 from
memkernel.

| Repository | Family | Form | Pages |
|---|---|---|---|
| code-copilot-team | api | list-item | 15 |
| code-copilot-team | llm-catalog | list-item | 15 |
| code-copilot-team | memkernel-integration | list-item | 7 |
| code-copilot-team | one-harness-home | list-item | 6 |
| code-copilot-team | plugin-generate-from-sources | bold-paragraph | 5 |
| code-copilot-team | pi | h3-adr | 6 |
| code-copilot-team | pi | list-item | 23 |
| code-copilot-team | routing | bold-paragraph | 21 |
| code-copilot-team | routing | list-item | 67 |
| code-copilot-team | simplest-complete-change | h3 | 3 |
| code-copilot-team | wiki-audit | bold-paragraph | 16 |
| code-copilot-team | wiki-studio-adoption | h3 | 14 |
| memkernel | memkernel | bold-paragraph | 37 |
| memkernel | memkernel | h3-adr | 14 |
| memkernel | memkernel | list-item | 50 |

The plain `h3` form appears only in the `wiki-studio-adoption` (14 pages) and
`simplest-complete-change` (3 pages) extension families; every H3 item of the base families holds a `**Decision**:`
line and is written in the `h3-adr` form.

### Against the pitch's counts

The pitch counted about 215 items: code-copilot-team 113 (routing 84, pi 29)
and memkernel 102. The differences are reported here, and the rule was not
tuned to remove them.

| Repository | Family | Pages | The pitch's count |
|---|---|---|---|
| code-copilot-team | api | 15 | (extension family, not in the base count) |
| code-copilot-team | llm-catalog | 15 | (extension family, not in the base count) |
| code-copilot-team | wiki-studio-adoption | 14 | (extension family, not in the base count) |
| code-copilot-team | wiki-audit | 16 | (extension family, not in the base count) |
| code-copilot-team | memkernel-integration | 7 | (extension family, not in the base count) |
| code-copilot-team | one-harness-home | 6 | (extension family, not in the base count) |
| code-copilot-team | plugin-generate-from-sources | 5 | (extension family, not in the base count) |
| code-copilot-team | simplest-complete-change | 3 | (extension family, not in the base count) |
| code-copilot-team | pi | 29 | 29 |
| code-copilot-team | routing | 88 | 84 |
| memkernel | memkernel | 101 | 102 |

| Repository | Form | Pages | The pitch's count |
|---|---|---|---|
| code-copilot-team | bold-paragraph | 42 | 17 (base families; `wiki-audit` adds 16, `plugin-generate-from-sources` 5) |
| code-copilot-team | h3 | 17 | 0 (only the `wiki-studio-adoption` and `simplest-complete-change` extension families) |
| code-copilot-team | h3-adr | 6 | 6 (H3) |
| code-copilot-team | list-item | 133 | 90 (base families; `api` and `llm-catalog` add 15 each, `memkernel-integration` 7, `one-harness-home` 6) |
| memkernel | bold-paragraph | 37 | 37 |
| memkernel | h3-adr | 14 | 14 (H3) |
| memkernel | list-item | 50 | 51 |

- **routing: 88 pages against 84**, four more bold-paragraph items. The
  pitch's per-family counts by form are not given, so the four cannot be
  named against it. The routing bold-paragraph pages come from
  `routing-context-limit` (8), `routing-effective-endpoint` (4 from
  `plan.md`, 3 from `spec.md`) and `routing-usage-evidence` (6).
- **memkernel: 101 pages against 102 items.** The one item left out for
  closing-keyword text (below) is a memkernel item, so the rule finds 102
  memkernel items and writes 101 of them as pages. The list-item count is the
  one that differs (50 against 51). The left-out item's form is not recorded,
  since its text is copied nowhere.
- **In all: 218 base pages against about 215**, plus 15 from the `api`
  extension family (`api-host-origin-guard`, `api-probe-dsn-constraints`,
  `api-probe-error-hardening`, all list items from `plan.md`) and 15 from the
  `llm-catalog` extension family (`specs/llm-catalog/spec.md`, all list
  items) and 14 from the `wiki-studio-adoption` extension family
  (`specs/wiki-studio-adoption/plan.md`, all plain H3 items) and 16 from the
  `wiki-audit` extension family (`specs/wiki-audit-trail/spec.md` and
  `specs/wiki-audit-flush/spec.md`, all bold paragraphs) and 7 from the
  `memkernel-integration` extension family
  (`specs/memkernel-integration/plan.md`, all list items) and 6 from the
  `one-harness-home` extension family (`specs/one-harness-home/spec.md`, all
  list items) and 5 from the `plugin-generate-from-sources` extension family
  (`specs/plugin-generate-from-sources/plan.md`, all bold paragraphs) and 3
  from the `simplest-complete-change` extension family
  (`specs/simplest-complete-change/plan.md`, all plain H3 items): 299 pages.

### Items left out

| Repository | Spec path | Lines | Slug | Reason |
|---|---|---|---|---|
| memkernel | `specs/memkernel-0-16-lifecycle-corrections/spec.md` | 109-110 | `mk-memkernel-0-16-lifecycle-corrections-spec-06` | closing-keyword text |

This is the one the pitch knew of. It is listed by id only (FR-007).

### Pages with an empty first paragraph

These pages stay in the corpus. `_first_paragraph` reads an empty string from
them, so B0 scores them on their title alone, as the issue 54 study did.

| Repository | Form | Pages with an empty first paragraph |
|---|---|---|
| code-copilot-team | bold-paragraph | 2 |
| code-copilot-team | h3 | 0 |
| code-copilot-team | h3-adr | 0 |
| code-copilot-team | list-item | 0 |
| memkernel | bold-paragraph | 0 |
| memkernel | h3-adr | 0 |
| memkernel | list-item | 0 |

- `code-copilot-team/routing/cct-routing-effective-endpoint-plan-01.md`
- `code-copilot-team/routing/cct-routing-effective-endpoint-spec-01.md`

Both are items the rule extracts badly, kept as written (FR-004). In each
one, the whole item is its bold label, so its `## Decision` section is
empty. Each label starts with an option name (`O1`, `O4`) that the identifier
pattern of the title rule (FR-005) removes. The titles therefore start in
mid-sentence: `+ O4. O4 governs; O1 is telemetry completion` and
`governs; O1 is telemetry completion, not the thing that makes C30
effective`.

### Input counts per repository and form

The minimum, median and maximum of `title_tokens` and `paragraph_tokens`
(the size of `wiki_state._tokenise` of the title and of the paragraph the
scorer reads). Each count reads one page and compares none. A median of an
even number of pages is the mean of the two middle values.

| Repository | Form | Pages | `title_tokens` min | `title_tokens` median | `title_tokens` max | `paragraph_tokens` min | `paragraph_tokens` median | `paragraph_tokens` max |
|---|---|---|---|---|---|---|---|---|
| code-copilot-team | bold-paragraph | 42 | 2 | 4.5 | 9 | 0 | 35 | 185 |
| code-copilot-team | h3 | 17 | 3 | 6 | 8 | 14 | 35 | 81 |
| code-copilot-team | h3-adr | 6 | 3 | 6 | 7 | 19 | 29 | 37 |
| code-copilot-team | list-item | 133 | 1 | 4 | 18 | 5 | 34 | 285 |
| memkernel | bold-paragraph | 37 | 1 | 3 | 10 | 6 | 69 | 221 |
| memkernel | h3-adr | 14 | 2 | 5 | 10 | 10 | 24.5 | 64 |
| memkernel | list-item | 50 | 1 | 2.5 | 19 | 3 | 22.5 | 98 |

### The six fixed items in the corpus

The six items of the table above are these pages. Each one is byte-equal to
the page `extract.py` builds from the raw text written out in
`tests/test_duplicates_extract.py`, and its first paragraph is the one written
out there.

- `code-copilot-team/pi/cct-pi-harness-adoption-plan-04.md`
- `code-copilot-team/routing/cct-routing-calibration-plan-03.md`
- `code-copilot-team/routing/cct-routing-context-limit-plan-03.md`
- `memkernel/memkernel/mk-memkernel-0-12-capture-core-spec-01.md`
- `memkernel/memkernel/mk-memkernel-0-3-plan-03.md`
- `memkernel/memkernel/mk-memkernel-0-7-wiring-spool-spec-02.md`

### Structural-lint violations from an item's own text

The test copies every page to `decisions/<slug>.md` in a temporary wiki,
with an `index.md` that links every page and a `log.md`, and runs
`wiki_studio.lint`'s structural checks on it. A violation that comes from an
item's own text, such as a relative link that does not resolve in the
temporary wiki, is listed below by page and never fixed (plan, O2). The test
allows exactly the violations listed.

The list is empty: no page holds a Markdown link, so no link target is
checked, and every page passes the other checks.

## The review sample (FR-008)

`sample.py` draws the owner's review sample from `labels.json` and
`corpus.json`. The population is every within-family pair of the three base
families (`routing`, `pi`, `memkernel`) whose label is false: an in-group
`companion` or `distinct-by-precondition` disposition, or `unrelated`, stated
or by default. Extension families are not sampled.

The 20 pairs are split across the families in proportion to their
within-family pair counts by the largest-remainder method, with ties going to
the family order routing, pi, memkernel. On the pitch's base counts this
gives routing 8, pi 1 and memkernel 11; under cut 1 it gives routing 10 and
memkernel 10. Within each family the draw is
`random.Random(SAMPLE_SEED).sample(sorted(population), k)`, with
`SAMPLE_SEED = 121`.

The script writes `review-sample.json` with the seed, the split, the sha256
of the `labels.json` it was drawn from, and the 20 pairs with their family and
label. It is run once, from the labelling commit's labels, before the owner
changes any label, and it is never re-drawn.

## The labels (FR-013 to FR-016)

`labels.json` was written in one labelling session, with no candidate code in
the tree: `candidates.py` did not exist, no script was run, and no token set,
overlap or score was computed. The session did not open
`eval/patterns/duplicates.py`, `eval/patterns/results/` or `eval/revisions/`.
It read every page of each family (one read of the family's directory) and
labelled from the pages' content only. The owner reviews the labels at the
pause after this step, before the freeze.

The `api` family, added by the extension rule's first step (FR-016(a)), was
labelled by a second session started by hand under the same rules and with no
candidate code: it read the family's 15 pages, grouped them by question
(`api-01` to `api-06`), and redid the summary pass over all four families. It
changed no label of the base families.

The `llm-catalog` family, added by the second step, was labelled the same way
by a third session: it read the family's 15 pages, grouped them by question
(`llm-catalog-01` to `llm-catalog-03`), and redid the summary pass over all
five families. It changed no existing label, the `api` family's included.

The `wiki-studio-adoption` family, added by the third step, was labelled the
same way by a fourth session: it read the family's 14 pages, grouped them by
question (`wiki-studio-adoption-01` to `wiki-studio-adoption-11`), and redid
the summary pass over all six families, reading memkernel's wiki-bridge pages
beside it. It changed no existing label of any family.

The `wiki-audit` family, added by the fourth step, was labelled the same way
by a fifth session: it read the family's 16 pages (the audit-trail and
audit-flush specs' decisions), grouped them by question (`wiki-audit-01` to
`wiki-audit-11`), looked across the two specs for a decision one restates,
reverses or replaces, and redid the summary pass over all seven families,
reading the routing, wiki-studio-adoption and memkernel pages it found
beside it. It changed no existing label of any family.

The `memkernel-integration` family, added by the fifth step, was labelled the
same way by a sixth session: it read the family's 7 pages (code-copilot-team's
plan for integrating memkernel), grouped them by question
(`memkernel-integration-01` to `memkernel-integration-03`), and redid the
summary pass over all eight families, reading memkernel's hook, session-start,
MCP-server and per-tool pages beside it for a decision the two repositories
state from both sides, and the wiki-studio-adoption pages for CCT's other
package adoption. It changed no existing label of any family.

The `one-harness-home` family, added by the sixth step, was labelled the same
way by a seventh session: it read the family's 6 pages (code-copilot-team's
spec for one harness home), grouped them by question (`one-harness-home-01`
and `one-harness-home-02`), and redid the summary pass over all nine
families, reading beside it the pi project-configuration and harness pages,
the llm-catalog user-home and file pages, the routing pages that name a path
in the user home, and memkernel's state-directory and harness pages. It
changed no existing label of any family.

The `plugin-generate-from-sources` family, added by the seventh step, was
labelled the same way by an eighth session: it read the family's 5 pages
(code-copilot-team's plan for generating the plugin from its sources),
grouped them by question (`plugin-generate-from-sources-01`), and redid the
summary pass over all ten families, reading beside it the
wiki-studio-adoption pages on plugin-only installations and setup, the
memkernel-integration pages on hooks, setup and on-demand rules, pi's
harness and worktree pages, and memkernel's session-start, hook and release
pages. It changed no existing label of any family.

The `simplest-complete-change` family, added by the eighth and last step,
was labelled the same way by a ninth session: it read the family's 3 pages
(code-copilot-team's plan for the simplest complete change), found that each
answers its own question and formed no group, and redid the summary pass over
all eleven families, reading beside it the wiki-studio-adoption pages on the
pin and the pin bump, the plugin-generate-from-sources page on the always-on
skills, the memkernel-integration page on the on-demand memory rule, pi's
harness pages, and memkernel's capture pages on record types. It changed no
existing label of any family.

### Grouping by question

Per family, pages that answer **the same question** form a group, and the
group is named by that question, not by a decision. Two pages in a group may
decide the same thing, decide opposite things, or decide for different cases;
the disposition of the pair says which. A page may sit in more than one group.
Grouping by question, not by how alike two pages read, keeps the labels
independent of the words the candidates compare: a pair is true because of
what the two decisions settle, never because they share a title.

Every pair inside a group gets one disposition and a one-line reason that
names the question. A pair that shares two groups is labelled once.
**A within-family pair outside every group is `unrelated`.**

### The six dispositions

True (a curator should act on the pair):

- `redundant`: the same decision on the same question, in other words.
  Either page could go without losing the decision.
- `conflicting`: the same question, opposite choices, and neither page says
  it replaces the other.
- `supersedes`: a later decision replaces an earlier one on the same
  question, which a wiki would mark with `superseded_by`.

False (the pair should stay as it is):

- `companion`: two pages about the same event or rule kept apart on purpose,
  because one builds on the other: a decision and the incident behind it, a
  rule and its application to one case, a decision and the later refinement
  that names it. Merging them would lose why they are apart.
- `distinct-by-precondition`: two decisions on the same question, each made
  for its own case (its own increment, component, record kind or setting),
  neither taking the other as its basis. They may agree or differ.
- `unrelated`: no shared question; the default for every pair outside a
  group.

### A decision and its incident record

A decision and the incident record behind it are labelled `companion`, which
is false. Two examples, named by path only; neither pair is in this corpus:

- the issue 54 pair `decisions/never-bypass-a-git-lock-with-an-alternate-index.md`
  and `incidents/git-safety-bypasses.md`. It is labelled `redundant` in the
  issue 54 labels, and that label stays frozen there;
- code-copilot-team's `infra-verification-as-gate` and
  `executable-artifacts-shipped-unexecuted`.

### The summary pass and the pairs across families

`labels.json` carries a summary of all families: one line per group (its
question) and one line per page in no group (its title). The session made one
pass over it and listed the pairs it found across families and across the two
repositories under `cross_pairs`, reading both pages before labelling each.
**An unlisted cross pair is `unrelated`.** Every pair of the corpus is scored
and counted later, whatever its label.

### The count

**True pairs: 7**, against the minimum of 8 (D4). The count is `true_pairs`
in `labels.json`: the pairs labelled `redundant`, `conflicting` or
`supersedes` in `pairs` and `cross_pairs`. Every commit that changes a label
updates `true_pairs` and this count together.

The `api` family added no true pair: its six groups hold seven
`distinct-by-precondition` pairs and two `companion` pairs, and the redone
summary pass added one cross pair (`api` and `routing`), labelled
`distinct-by-precondition`.

The `llm-catalog` family added no true pair either: its three groups hold five
`distinct-by-precondition` pairs, and the redone summary pass added four cross
pairs (`llm-catalog` and `routing`): two `companion` and two
`distinct-by-precondition`.

The `wiki-studio-adoption` family added no true pair: the plan's fourteen
decisions build on one another, so its eleven groups hold fourteen `companion`
pairs (a decision and the later one that names or applies it) and five
`distinct-by-precondition` pairs, and none restates, reverses or replaces
another. The redone summary pass added four cross-repository pairs, between
this family and memkernel's wiki-bridge, MCP-range and release-exit pages, all
`distinct-by-precondition`.

The `wiki-audit` family added no true pair either: the audit-flush spec builds
on the audit-trail spec's log format, and within each spec the decisions build
on one another, so its eleven groups hold seventeen `companion` pairs (a
decision and the later one that applies or refines it) and four
`distinct-by-precondition` pairs; no decision restates, reverses or replaces
another. The redone summary pass added five cross pairs: two
`distinct-by-precondition` with `routing` (write-time scrubbing, a second
immediate run as a no-op), two `companion` with `wiki-studio-adoption` (CCT's
contract test proving the flush's commit and its no-op), and one
cross-repository `distinct-by-precondition` with memkernel (who consumes the
ingest log's hash recipe).

The `memkernel-integration` family added no true pair either: its three
groups hold two `companion` pairs (the GCC sections' replacement and the
cleanup of every remnant; the per-project MCP registration and the sync step
that applies it to existing projects) and one `distinct-by-precondition` pair
(the sync paths for an existing install and an existing project), and no
decision restates, reverses or replaces another. memkernel's own specs state
none of the plan's seven decisions from their side: the closest, its per-tool
choice of a hook or an always-applied rule, is a different set of tools. The
redone summary pass added four cross pairs, all `distinct-by-precondition`:
one cross-repository with that memkernel page (where an agent tool's memory
instructions live), and three with `wiki-studio-adoption` (how CCT checks a
sibling package is usable, which artifact its setup installs, and whether the
replaced in-repo system is removed in the same change).

The `one-harness-home` family added no true pair either: its two groups hold
two `companion` pairs (the user home's `~/.cct/` and the ruling that renames
the project side too; the delivery rule that makes the project half its own
issue if D5 says yes and D5's yes), and no decision restates, reverses or
replaces another. The redone summary pass added eleven cross pairs, all
false: three `companion` with `llm-catalog`, whose user-home decision was
amended on record to `${CCT_HOME:-~/.cct}` after the user-home change landed
first; and eight with `pi`'s project-configuration spec and harness plan,
six `companion` (the project-side issue that the one-harness-home ruling
deferred, supplying its location, gitignore guidance, fallback and manifest
rule; the project fallback set with the user-home fallback; the ruling's
renaming of the harness plan's `.code-copilot-team/` project files) and two
`distinct-by-precondition` (an explicit migrate command, for the user home
and for the project). The user home's new name was not labelled against the
pages that name a file under `~/.code-copilot-team/` (pi's harness plan, the
routing registry and its state store): the rename moves the directory
through one resolver and replaces none of those pages' decisions, so those
pairs stay `unrelated`; the owner reviews this reading with the labels.

The `plugin-generate-from-sources` family added no true pair either: its one
group holds one `distinct-by-precondition` pair (the six always-on skills
shipped as ordinary plugin skills, and the templates and helper script
shipped inside the plugin with rewritten paths, each rather than leaving
out what the agents and commands refer to), and no decision restates,
reverses or replaces another. The owner's ruling page ("D1–D4 approved as
recommended") was not grouped with the four decision pages: none of them
carries its D number, so their text does not tie the ruling to any one of
them, and those pairs stay `unrelated`; the owner reviews this reading with
the labels. The redone summary pass added one cross pair, labelled
`distinct-by-precondition`: the templates decision with the
wiki-studio-adoption page that claims no automatic installation parity for
plugin-only installs (whether a plugin-only installation works as far as a
`setup.sh` install, each for its own components).

The `simplest-complete-change` family added no true pair either: its three
decisions answer three questions (whether CCT depends on Ponytail, which
always-loaded rule holds the reuse ladder, and which decisions are recorded
in memory through memkernel's existing interfaces), so it has no group and
its three pairs are `unrelated`. The redone summary pass added two cross
pairs, both `distinct-by-precondition`: the Ponytail decision with the
wiki-studio-adoption pin and pin-bump pages (how an upstream project's
changes may reach what CCT runs: Ponytail's never do, since CCT takes no
dependency on it; wiki-studio's only by a CCT commit). The decision-memory
page was not labelled against memkernel's capture page that keeps captured
owner answers out of the `decision` type: that page settles a record type
for captured text, not which decisions an agent records, so the pair stays
`unrelated`; the owner reviews this reading with the labels.

**Status: below the minimum, with the extension order used up; the verdict
will be "not testable".** The count is still below the minimum after the
extension order's eighth and last step, so the extension rule (FR-016) has
no step left and the verdict will be "not testable" (D4), never a pass. No
label is changed to reach the minimum. The next steps are the main
session's review sample (`python -m eval.duplicates.sample`, committed as
its own commit) and then the owner's review of every true and `companion`
label, every listed cross pair and the 20 sampled false pairs, before the
freeze.

`tests/test_duplicates_labels.py` checks the labels' structure: the keys, the
groups, every in-group pair labelled once, the dispositions and reasons, the
cross pairs' scopes, the summary, the true-pair count here and in the file,
and `corpus_sha256`.

## Commands

Run from the repository root with the package importable (the main session's
`PYTHONPATH=src`):

```
python -m eval.duplicates.extract
python -m eval.duplicates.extract --cut-1
python -m eval.duplicates.extract --extend 1
python -m eval.duplicates.sample
```

The first line is the extraction run. The second replaces it only if the
owner invokes cut 1. The third is the extension rule's form, with N the
number of steps. The last is the review sample.
