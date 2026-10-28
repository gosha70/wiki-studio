#!/bin/sh
# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
#
# The conformance suite's stub backend (FR-043 case 11). The suite installs this
# script as the CLI named by WIKI_STUDIO_BACKEND, first on PATH, so any model
# call a tool makes runs it instead of a real model. Every invocation appends
# one line to $CONFORMANCE_STUB_LOG; the suite asserts that file never appears.
printf '%s\n' "$*" >> "${CONFORMANCE_STUB_LOG:?CONFORMANCE_STUB_LOG is not set}"
echo "conformance stub backend: no model is available here" >&2
exit 1
