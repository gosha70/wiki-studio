# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.7.x | yes |
| 0.6.x, 0.5.x, 0.4.x, 0.3.x, 0.2.x, 0.1.x | no (upgrade to 0.7; the library API is a superset, see the upgrade notes in `CHANGELOG.md`) |

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
  descriptor on POSIX. The wiki directory's configured spelling may itself
  be a symlink alias (two spellings share one lock); it is resolved once,
  and on POSIX the manifest, schema overrides and approval records are
  reached from the real directory component by component with
  `O_NOFOLLOW`, so a component swapped for a symlink later is refused.
  Where the platform has no descriptor-relative opens (`dir_fd`, as on
  Windows, which the package does not claim to support), the approval-record
  scan falls back to checking each component with `lstat` before reading it
  by path: a weaker binding, since a swap between the check and the read is
  not caught, as for the ingest-log append.
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
- `--by NAME` and `WIKI_STUDIO_ACTOR` are attribution, not authentication.
  The name recorded as `plan.json`'s `proposer` and the receipt's `actor`
  is whatever the caller supplied; nothing verifies it, and the OS user
  name is never captured. The host that runs wiki-studio supplies
  authority. Receipts, archived proposals and the ingest log give
  traceability, not tamper-proof evidence: anyone who can write the wiki or
  the proposals directory can change them. A way to forge or alter these
  records is not a vulnerability; a way to make wiki-studio record a name
  the caller did not supply is.

Anything that lets a source file, a backend response or a proposal
directory write outside the wiki and proposals directories, run a command,
or bypass the confinement is in scope.
