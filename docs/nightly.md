# Nightly: the propose-only curation pass

`wiki-studio nightly` runs the wiki's routine checks unattended and writes
one report. It prepares work for a curator and stops: it never promotes or
approves a proposal, never commits, pushes or checks out, and writes
nothing in the wiki directory; its findings step reads repositories
read-only.

One run does four things:

- structural lint, with the audit-format errors reported beside it;
- the model-free findings, with their counts by kind;
- a list of the proposal directories still pending, each with its edit
  count;
- with an explicit backend, drafts of the findings whose fix adds a link.

## What it drafts, and what it refuses

Drafting happens only when `--backend` names one. `WIKI_STUDIO_BACKEND`
and PATH auto-detect are not consulted, so a run without `--backend`
calls no model.

Two findings are draftable: a `missing-cross-link`, whose canonical page
other pages mention without linking, and a weak orphan that `index.md`
does not link. Every other finding is reported for a curator.

A draft may only turn words already on the page into links. It may not
add a word, a line or a section, and it may not change another byte. The
pass refuses any draft that breaks that rule and writes nothing, so a
proposal holds only added links and one log line. Each draft is bound to
the sha256 of the page bytes the model was shown, so a draft made from an
old revision fails `promote` with exit 9 instead of replacing newer text.

Under the default `--max-proposals 5` one run creates at most five
proposal directories and makes at most ten backend calls;
`--max-proposals N` sets both. A proposal directory's name is derived
from the finding, so a rerun on an unchanged wiki drafts nothing and
reports the proposal as already proposed.

## Where the report goes

Without `--report` the markdown report goes to stdout. `--report PATH`
writes it to PATH atomically and prints no markdown; missing parents are
created. PATH must lie outside the wiki directory, and a path inside it is
refused before anything runs. `--json` prints the result as one JSON
object; with `--report` the file is written before the JSON is printed.

A run that could not write its report exits 6 and names the reason on
stderr. A wiki whose structural lint fails exits 1 after the report is
written, and no draft is attempted. A completed run exits 0 whatever it
found. The verb's `--help` lists every exit code.

## Install

```bash
pip install wiki-studio
```

## Run it from cron

A cron job starts in the home directory with a minimal environment. A
wrapper script changes to the project checkout and writes the report under
`reports/`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# cron starts in the home directory with a minimal PATH; run from the project checkout.
cd "<project-dir>"

wiki-studio nightly --report "reports/nightly-$(date +%F).md" --by "<agent-name>"
```

Replace `<project-dir>` with the checkout's path and `<agent-name>` with the
name the run records as the proposer.

A `%` in a crontab entry is special: cron ends the command at the first
unescaped `%` and feeds the rest to the command as standard input, so a
`date +%F` written directly in an entry must escape the `%` as `\%`. The
wrapper keeps the date inside the script, so the crontab entry holds no
`%` and needs no escaping. Save the block as
`scripts/nightly-report.sh`, make it executable, and add one line to the
crontab with `crontab -e`:

```crontab
0 3 * * * /path/to/project/scripts/nightly-report.sh
```

To draft as well, add `--backend claude` to the same command:

```bash
wiki-studio nightly --report "reports/nightly-$(date +%F).md" --backend claude --by "<agent-name>"
```

The `claude` CLI must be installed on the machine that runs the job: a
`--backend` whose CLI is not on PATH exits 2 before lint runs. The CLI
must also be authenticated for the user cron runs as. An unauthenticated
CLI makes each draft's backend call fail, and the run exits 3.

## Run it from GitHub Actions

The same pass runs as a scheduled workflow. This form installs with the
line above, runs without a backend, and uploads the report and the
proposals directory after every run. The checkout asks for the full
history (`fetch-depth: 0`), because the revision check skips a shallow
clone, so with the default shallow checkout no cited `sha:` is checked:

```yaml
name: wiki-nightly
on:
  schedule:
    - cron: "0 3 * * *"
  workflow_dispatch:
jobs:
  nightly:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install wiki-studio
      - run: wiki-studio nightly --report reports/nightly.md --by "<agent-name>"
      - if: always()
        uses: actions/upload-artifact@v4
        with:
          name: nightly-report
          path: |
            reports/
            doc_internal/proposals/
```

The drafting variant is the same workflow with `--backend claude` added
to the run step. The `claude` CLI must be installed and authenticated on
the runner before that step; how the runner is provisioned is up to the
project, so no install step for the CLI is shown:

```yaml
name: wiki-nightly
on:
  schedule:
    - cron: "0 3 * * *"
  workflow_dispatch:
jobs:
  nightly:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install wiki-studio
      - run: wiki-studio nightly --report reports/nightly.md --backend claude --by "<agent-name>"
      - if: always()
        uses: actions/upload-artifact@v4
        with:
          name: nightly-report
          path: |
            reports/
            doc_internal/proposals/
```

## After the run

The verb never commits, pushes or checks out; its findings step reads
repositories read-only. A curator promotes a draft from a checkout of the repository that holds the
wiki: `wiki-studio promote <proposal-dir>`. A promotion applies the draft
only while every page still carries the revision the draft was built from.

A person approves a `nightly-*` draft. Review the proposal with the
[curator persona](https://github.com/gosha70/wiki-studio/blob/main/src/wiki_studio/schema/WIKI_MAINTAINER.md)
at hand: an agent may review and promote the proposal, and approving it is
a person's step, following the persona's "Who approves" step.
