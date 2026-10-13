# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | yes |
| earlier | no (nothing earlier was released) |

Fixes are released as patch versions of the latest minor line.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's
private reporting on this repository: **Security → Report a vulnerability**
(https://github.com/gosha70/wikiforge/security/advisories/new). Include the
version, a reproduction, and what an attacker would gain.

You will get an acknowledgement within seven days and a fix or a
mitigation plan within thirty days of confirmation. Credit is given in the
advisory unless you ask otherwise.

## What to look at

- `wikiforge` has no runtime dependencies; the LLM backends are copilot CLIs
  the tool starts as subprocesses with the rendered prompt as an argument.
  Prompts contain the source being ingested and wiki pages, so backend
  stderr may echo them; error messages therefore carry only a redacted
  fingerprint of stderr unless `--debug-unsafe-output` is given.
- Sources and proposal directories are confined to the project root by
  default (`--allow-out-of-repo` lifts that deliberately); `promote`
  validates and lints a staged copy of the wiki in a private temporary
  directory before writing anything.
- `promote` is the only code path that writes into the wiki, and
  `audit-flush` is the only one that runs `git commit`.

Anything that lets a source file, a backend response or a proposal
directory write outside the wiki and proposals directories, run a command,
or bypass the confinement is in scope.
