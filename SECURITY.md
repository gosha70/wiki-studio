# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.6.x | yes |
| 0.5.x, 0.4.x, 0.3.x, 0.2.x, 0.1.x | no (upgrade to 0.6; the library API is a superset, see the upgrade notes in `CHANGELOG.md`) |

Fixes are released as patch versions of the latest minor line.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's
private reporting on this repository: **Security → Report a vulnerability**
(https://github.com/gosha70/wiki-studio/security/advisories/new). Include the
version, a reproduction, and what an attacker would gain.

You will get an acknowledgement within seven days and a fix or a
mitigation plan within thirty days of confirmation. Credit is given in the
advisory unless you ask otherwise.

## What to look at

- `wiki-studio` has no runtime dependencies; the LLM backends are copilot CLIs
  the tool starts as subprocesses with the rendered prompt as an argument.
  Prompts contain the source being ingested and wiki pages, so backend
  stderr may echo them; error messages therefore carry only a redacted
  fingerprint of stderr unless `--debug-unsafe-output` is given.
- Sources and proposal directories are confined to the project root by
  default (`--allow-out-of-repo` lifts that deliberately); every read and
  write of a wiki page, a proposal file or a local link target passes one
  containment check that resolves the path and refuses an escape or a
  symlink (`wiki_studio.paths.contain`). The same check covers the archive
  root `proposals/.applied`, the paths a receipt names for recovery, the
  legacy proposal file, the pages ingest reads into its prompt, and the
  ingest-log append, which is bound to the verified `.audit/` directory
  descriptor on POSIX.
- A promotion is validated (a staged copy of the wiki is linted in a
  private temporary directory before anything is written), serialised
  against other wiki-studio writers on the same machine by an OS advisory
  lock, and rolled back on failure. It is not crash-safe across files: a
  process killed inside the commit can leave some files written and
  others not, and uncoordinated readers may observe intermediate state. A
  receipt or archive that could not be synced to disk (a real `fsync`
  error) stops the promotion rather than continuing.
  The lock covers one machine and one filesystem; it is not distributed,
  does not protect against direct edits of wiki files, and network
  filesystems are out of scope.
- `promote` is the only code path that writes into the wiki, and
  `audit-flush` is the only one that runs `git commit`.

Anything that lets a source file, a backend response or a proposal
directory write outside the wiki and proposals directories, run a command,
or bypass the confinement is in scope.
