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

The labels, the protocol, the scorer, its results and the report are added
by later steps of the spec. No driver session runs these scripts. The main
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
Any difference from the pitch's page counts will be reported, and the rule
will not be tuned to remove it.

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
