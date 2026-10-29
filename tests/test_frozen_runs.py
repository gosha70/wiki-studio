# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The frozen evaluation runs are never edited (0.8.0 FR-019, FR-026).

Runs 1 and 2 call the live selector, so their numbers are only evidence while
their inputs stay byte for byte what was published. Every frozen file is pinned
here by sha256; the list was taken from ``git ls-files`` at pin time, so an
untracked file beside them is never pinned. The discovery runner keeps its
search cache in a temporary directory; a runner pass must leave run 2's tree
unchanged. The held-out set pins its frozen inputs the same way and never the
files its one run writes.
"""

from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from eval.navigation import discovery
from eval.navigation.run2_protocol import _tree_hash

NAVIGATION = Path(__file__).resolve().parents[1] / "eval" / "navigation"
REPO_ROOT = NAVIGATION.parents[1]
RUN2 = NAVIGATION / "run2"
HELDOUT = NAVIGATION / "heldout"
UNTUNED_CONFIG = NAVIGATION / "run3" / "ranker-config-untuned.json"

# The files FR-019 names; the pins below cover them and every tracked file under these directories.
NAMED_FILES = (
    "run.py",
    "run2_protocol.py",
    "questions.json",
    "gold.json",
    "results.json",
    "manifest.json",
    "stopwords.txt",
    "ingest-notes.md",
)
FROZEN_DIRS = ("run2", "wiki", "proposals", "corpus")
# The derived search cache beside a fixture's wiki (FR-012): it must never appear in a frozen directory.
CACHE_GLOB = ".*.wiki-studio.*"

# ``<path under eval/navigation>=<sha256>``, one token per line, pinned from ``git ls-files`` on 2026-10-27.
FROZEN_PINS = """
run.py=e441ac532dcf6b906128d04fa6efe30c34b36560bf985eaf5480250cd29c5190
run2_protocol.py=3fe6cad41d28109561d6e0404840bcf7b3540f523d661a394c2bbb96b28476b5
questions.json=30390468555e11ce9fbeb2e259997e266979d502dd6c3833373620f468ee760d
gold.json=74a9db0df77ba550a9e5f6e3b7c9b6879f660c6c6407769229bda9aa7bc8ef86
results.json=ed4550260cf34b4fb618ff4839576dfa9cd52fb39e2528c7184b6301c011bd58
manifest.json=de4c3e60ec2851f15078a8347e65ebafb7f5774afcb685b91d7d7460b38fa191
stopwords.txt=e55cb41493293a01c3408d29b5eb70408f189b5dc7aac50a486412ac4b449851
ingest-notes.md=adf2c1f0565dcdd3d23c728dd213e0e0fbd4beca4c25bb8de513b0bef0afe22c
corpus/README.md=819e2638daf9b91efb97c4e5b3d777a3117d660cada232514200bd6ab69524fa
corpus/docs/adr/ADR-007-tiered-memory.md=ad9b472e06c7c3889e020073d51d375ff8a334b02b4a5f6a5c8fd27cb82f76e0
corpus/docs/adr/ADR-008-llm-wiki-as-semantic-layer.md=84d93d69820f924a54f5b8285d5cf6f3c67d895a44a5e699963f7e2f1fc81f5e
corpus/docs/adr/ADR-009-rlm-studio-for-documents.md=c5192106f0da21a959c6ac04e154195e31eb86e1fa9d82f97eb616a2cd9d5c5c
corpus/docs/architecture/memory-tiers.md=a73e489fa442895f0ab3cc1c4787a6eb71296eb6f284c8e7801fb3de5b1a1cff
corpus/docs/integration/harness-integration.md=018269343518cd794d0e1897e2aee582db2320d3d5ee040465f5dd4e3df04d29
corpus/docs/licensing.md=9617df2ddce8aa5219d30599da58179f717ad428ebe1af47b26051fcae802b88
corpus/docs/research/memory-literature-review.md=225b93aafe3477be3fe5fd29505cde6548c5ea0f49a1c39c034ee6557e9902b3
corpus/docs/research/sibling-projects.md=acd7668d466d5da9b8476c5ec18cdd9daf33897eb4bbfc1bc56c0d3d750105f2
corpus/docs/roadmap.md=50c35dd125b95485d66884421fcd65b018ee2bbf2bd1a2317588e7bfdb2aa697
proposals/.applied/2026-10-15-ADR-009-rlm-studio-for-documents/.ingest-snapshot/plan.json=ed640a73f605954437e1d9511a403e8d0e3908f565161d6f1744b6079c0bb109
proposals/.applied/2026-10-15-ADR-009-rlm-studio-for-documents/.ingest-snapshot/preview/decisions/rlm-studio-document-layer.md=4dadf0ae6bebad9a25523d9a0ab22263aadc6ce98234ed59b95ed85a926f54e9
proposals/.applied/2026-10-15-ADR-009-rlm-studio-for-documents/.ingest-snapshot/preview/index.md=a6b8139c0ac86ffe2b9c659358941a686a1e2b954866c31f678b7be98de6b1d9
proposals/.applied/2026-10-15-ADR-009-rlm-studio-for-documents/.ingest-snapshot/preview/log.md=c8b2f5ad7e4b635ea0a458a3a3fc93be4abe80ac136bf4442108ccb9cf54112b
proposals/.applied/2026-10-15-ADR-009-rlm-studio-for-documents/plan.json=ed640a73f605954437e1d9511a403e8d0e3908f565161d6f1744b6079c0bb109
proposals/.applied/2026-10-15-ADR-009-rlm-studio-for-documents/preview/decisions/rlm-studio-document-layer.md=4dadf0ae6bebad9a25523d9a0ab22263aadc6ce98234ed59b95ed85a926f54e9
proposals/.applied/2026-10-15-ADR-009-rlm-studio-for-documents/preview/index.md=a6b8139c0ac86ffe2b9c659358941a686a1e2b954866c31f678b7be98de6b1d9
proposals/.applied/2026-10-15-ADR-009-rlm-studio-for-documents/preview/log.md=c8b2f5ad7e4b635ea0a458a3a3fc93be4abe80ac136bf4442108ccb9cf54112b
run2/gold.json=5a8c43df1093e8ff906581e88b9034129067080dd7af5a849be75b185922e88b
run2/ingest-logs/01-ingest.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/01-ingest.stdout.txt=1adc7151f8ca432e7841cd25d94efa05f3d5501c3fbdca9fd2c7c4e57e1a547c
run2/ingest-logs/01-promote.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/01-promote.stdout.txt=3dd8b6612ee8d9f4b0fc7d652fb9c2e9a8b604079ec2f82a0cd88936f9f033e4
run2/ingest-logs/02-ingest.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/02-ingest.stdout.txt=f1fc9b187ed2e35bb25364f81fe6d8bef9ec75b9bd4bf4c41896fcdfb64003c4
run2/ingest-logs/02-promote.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/02-promote.stdout.txt=72d69d2863325d8e9a6db2021c060dc8766a9c57a1d152b55cd5076dc70b8b60
run2/ingest-logs/03-ingest.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/03-ingest.stdout.txt=e0ff5cf1b3cdde52e9e3cb353a74f620001050d88da78443be8fd633547a8693
run2/ingest-logs/03-promote.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/03-promote.stdout.txt=c84e06ca0208bb5fea6995f8b77040cc87c817d0928df646be5c968bf8602fdd
run2/ingest-logs/04-ingest.stderr.txt=f7308c2be4713d841e7560bd439e8c5a231c2b07027fa1a56812ba55e618abc0
run2/ingest-logs/04-ingest.stdout.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/05-ingest.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/05-ingest.stdout.txt=61558873f1cf309ecf1e6c11dcc3a868640369d52f8ab57e3e1489ad424d7664
run2/ingest-logs/05-promote.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/05-promote.stdout.txt=62b0c8dbba9e119606fbe39010cb4142d6134b8bd1fd9baa0b2f8421c31b1ef3
run2/ingest-logs/06-ingest.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/06-ingest.stdout.txt=8f261479ebb8b95e91737eeeb016f7693fcd486290f17fdb15bdf81d3c4579a1
run2/ingest-logs/06-promote.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/06-promote.stdout.txt=75df0fd3a4dd3f8f3235e7ab2482fe857a323c8448b3161351fa04867325ad29
run2/ingest-logs/07-ingest.stderr.txt=f7308c2be4713d841e7560bd439e8c5a231c2b07027fa1a56812ba55e618abc0
run2/ingest-logs/07-ingest.stdout.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/08-ingest.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/08-ingest.stdout.txt=86c90a38661a46769656a14c13d1a681959aaab3a5257183e31de3f5cc8c9243
run2/ingest-logs/08-promote.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/08-promote.stdout.txt=0da3925a4dafb3a83094241cda4a6bf043ff8690403ba5754c15312337572bdf
run2/ingest-logs/09-ingest.stderr.txt=f7308c2be4713d841e7560bd439e8c5a231c2b07027fa1a56812ba55e618abc0
run2/ingest-logs/09-ingest.stdout.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/10-ingest.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/10-ingest.stdout.txt=79d0dd18b2a4540da1bb6516b759cffe26d4cdee7801c45a499de9142c7595ab
run2/ingest-logs/10-promote.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/10-promote.stdout.txt=ae495421b89c71d3faf28d2606b110040be8e576f53081da3dee9a8c49b8d95a
run2/ingest-logs/lint.stderr.txt=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
run2/ingest-logs/lint.stdout.txt=588279e8567640565754e15889a6a3545817cbb616932d4801f9f0b8033e46db
run2/ingest-notes.md=e05d9541c5d02a86bce60d9224e46d9ad70a25d6439b7196659d81ff6990b26a
run2/manifest.json=a2bd433823f84d245c419e9df7d32f10f91d2a4e52541465f61f0242e25cd291
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/.ingest-snapshot/plan.json=b9f39d6c8ef27a2c2bb8caae027440b86802820af9c5293764b4d22a7c6cd149
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/.ingest-snapshot/preview/concepts/memkernel-tiered-memory.md=dfa1270d571ec51b4fd8b0e76d54c2ec55eb3aa6529620b4d784db9cfda5f9ff
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/.ingest-snapshot/preview/decisions/memkernel-tiered-memory-decision.md=2198581162751d32102f8bea6baffacc92fdaed69c41b522cf8c9917cf9e29be
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/.ingest-snapshot/preview/index.md=dd7e3f02673cc8708ff120b68df7db00fcb1a92078dd17272146f6f8666bd187
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/.ingest-snapshot/preview/log.md=23f681887cba11ddd2f6bbf1b872d973b61011fa01119825c0840ae33fe17315
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/plan.json=b9f39d6c8ef27a2c2bb8caae027440b86802820af9c5293764b4d22a7c6cd149
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/preview/concepts/memkernel-tiered-memory.md=dfa1270d571ec51b4fd8b0e76d54c2ec55eb3aa6529620b4d784db9cfda5f9ff
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/preview/decisions/memkernel-tiered-memory-decision.md=2198581162751d32102f8bea6baffacc92fdaed69c41b522cf8c9917cf9e29be
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/preview/index.md=dd7e3f02673cc8708ff120b68df7db00fcb1a92078dd17272146f6f8666bd187
run2/proposals/.applied/2026-10-16-ADR-007-tiered-memory/preview/log.md=23f681887cba11ddd2f6bbf1b872d973b61011fa01119825c0840ae33fe17315
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/.ingest-snapshot/plan.json=8429737362a19898bc64264d2398d49cf05c76c31ce0462e5fbc9eb6a21f2834
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/.ingest-snapshot/preview/concepts/memkernel-wiki-bridge-and-health.md=dd73ce6b5663940855df3ae1fe6e1ae68bba7969cd99cb5902176d264b34cce3
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/.ingest-snapshot/preview/decisions/memkernel-wiki-semantic-layer-decision.md=3ec7146e315031ce27c20be1f93542ab141011f481e8fd251db71fc61f782c0d
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/.ingest-snapshot/preview/index.md=158bae95b3a43f289b06e611f50a192adbecfd541112d6f66a27d85f94b7b6a2
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/.ingest-snapshot/preview/log.md=acab9835a83ae8dae5325935f31d2e2c81c352f8956e0f91e1d24088dfadf734
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/plan.json=8429737362a19898bc64264d2398d49cf05c76c31ce0462e5fbc9eb6a21f2834
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/preview/concepts/memkernel-wiki-bridge-and-health.md=dd73ce6b5663940855df3ae1fe6e1ae68bba7969cd99cb5902176d264b34cce3
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/preview/decisions/memkernel-wiki-semantic-layer-decision.md=3ec7146e315031ce27c20be1f93542ab141011f481e8fd251db71fc61f782c0d
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/preview/index.md=158bae95b3a43f289b06e611f50a192adbecfd541112d6f66a27d85f94b7b6a2
run2/proposals/.applied/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/preview/log.md=acab9835a83ae8dae5325935f31d2e2c81c352f8956e0f91e1d24088dfadf734
run2/proposals/.applied/2026-10-16-README/.ingest-snapshot/plan.json=349254c25b6090b2a902e35463feaf94dc317dd3df01a0c263bfb076caccaa46
run2/proposals/.applied/2026-10-16-README/.ingest-snapshot/preview/concepts/memkernel-tiered-memory.md=1eb7ee97ec35c467a5c41d7d7bf5325f6f0df14394fe2647d20ae594653838ec
run2/proposals/.applied/2026-10-16-README/.ingest-snapshot/preview/concepts/memkernel-wiki-bridge-and-health.md=c1e4197c40a19dc8fa37cb216735901102551704e4b5b8692e416fb3d34694f8
run2/proposals/.applied/2026-10-16-README/.ingest-snapshot/preview/index.md=ae9e9da9b63a5a5851c7eb086228713dfc5bf70935fd4331533c93c047cd0e09
run2/proposals/.applied/2026-10-16-README/.ingest-snapshot/preview/log.md=4d9df80a59dd091697c633e0fffd71f9e073550e5a9fa875fc43ab193cba9846
run2/proposals/.applied/2026-10-16-README/.ingest-snapshot/preview/playbooks/memkernel-install-troubleshooting.md=7be63d03d24d29e57d0fb909daa6cb121de058f96598653d2ccf287855072fc3
run2/proposals/.applied/2026-10-16-README/.ingest-snapshot/preview/workflows/memkernel-claude-code-setup.md=c7c556ccc2cafb308900b69bd9af9badeb01d56b66671a8eba28b4570ff62bfd
run2/proposals/.applied/2026-10-16-README/plan.json=349254c25b6090b2a902e35463feaf94dc317dd3df01a0c263bfb076caccaa46
run2/proposals/.applied/2026-10-16-README/preview/concepts/memkernel-tiered-memory.md=1eb7ee97ec35c467a5c41d7d7bf5325f6f0df14394fe2647d20ae594653838ec
run2/proposals/.applied/2026-10-16-README/preview/concepts/memkernel-wiki-bridge-and-health.md=c1e4197c40a19dc8fa37cb216735901102551704e4b5b8692e416fb3d34694f8
run2/proposals/.applied/2026-10-16-README/preview/index.md=ae9e9da9b63a5a5851c7eb086228713dfc5bf70935fd4331533c93c047cd0e09
run2/proposals/.applied/2026-10-16-README/preview/log.md=4d9df80a59dd091697c633e0fffd71f9e073550e5a9fa875fc43ab193cba9846
run2/proposals/.applied/2026-10-16-README/preview/playbooks/memkernel-install-troubleshooting.md=7be63d03d24d29e57d0fb909daa6cb121de058f96598653d2ccf287855072fc3
run2/proposals/.applied/2026-10-16-README/preview/workflows/memkernel-claude-code-setup.md=c7c556ccc2cafb308900b69bd9af9badeb01d56b66671a8eba28b4570ff62bfd
run2/proposals/.applied/2026-10-16-harness-integration/.ingest-snapshot/plan.json=77fd9e71092fbcb9b9b25174ea7e69857cdc19ad513304f4dd033e92b8b9af2f
run2/proposals/.applied/2026-10-16-harness-integration/.ingest-snapshot/preview/concepts/memkernel-harness-integration.md=d09077537f0a885560c19373d61e77a6de9d0892e155206daa3fe5e44cec893c
run2/proposals/.applied/2026-10-16-harness-integration/.ingest-snapshot/preview/index.md=c42d941d82a4db515567ff71e3e10a680569a3dcf0c0b6879408c52a42a3f95b
run2/proposals/.applied/2026-10-16-harness-integration/.ingest-snapshot/preview/log.md=8240a60d80cd31c919b32cfc57870e133b35ff242aa2b17c8a4aaa259f852f93
run2/proposals/.applied/2026-10-16-harness-integration/.ingest-snapshot/preview/workflows/memkernel-claude-code-setup.md=c302df8675f0afa2bdcc080d8e3c4afacd618383db2dab825268b6fc6e97d145
run2/proposals/.applied/2026-10-16-harness-integration/plan.json=77fd9e71092fbcb9b9b25174ea7e69857cdc19ad513304f4dd033e92b8b9af2f
run2/proposals/.applied/2026-10-16-harness-integration/preview/concepts/memkernel-harness-integration.md=d09077537f0a885560c19373d61e77a6de9d0892e155206daa3fe5e44cec893c
run2/proposals/.applied/2026-10-16-harness-integration/preview/index.md=c42d941d82a4db515567ff71e3e10a680569a3dcf0c0b6879408c52a42a3f95b
run2/proposals/.applied/2026-10-16-harness-integration/preview/log.md=8240a60d80cd31c919b32cfc57870e133b35ff242aa2b17c8a4aaa259f852f93
run2/proposals/.applied/2026-10-16-harness-integration/preview/workflows/memkernel-claude-code-setup.md=c302df8675f0afa2bdcc080d8e3c4afacd618383db2dab825268b6fc6e97d145
run2/proposals/.applied/2026-10-16-memory-literature-review/.ingest-snapshot/plan.json=eab1c3fe1bbcaea31ff64f6a32a5e7f56ecd4e80236ff50a454cfa17bbb50b04
run2/proposals/.applied/2026-10-16-memory-literature-review/.ingest-snapshot/preview/concepts/memkernel-memory-literature-review.md=63bedaba1c7073e51a721b5e8858ed39c9710a1ee6489146036ecdc5463600a3
run2/proposals/.applied/2026-10-16-memory-literature-review/.ingest-snapshot/preview/decisions/memkernel-tiered-memory-decision.md=8ae206acd384cdf0d52f60910daa68cc40be69a284c26c25d92d2abe1954f13a
run2/proposals/.applied/2026-10-16-memory-literature-review/.ingest-snapshot/preview/index.md=e8815cb1c2af1cb6b14b17400d77c2b876030f71743dafe86cd2f35f9c14d7af
run2/proposals/.applied/2026-10-16-memory-literature-review/.ingest-snapshot/preview/log.md=ef64468447f9cd19b9eb20b9b8a28487d66607b7b0a85e381334408e23ff71e8
run2/proposals/.applied/2026-10-16-memory-literature-review/plan.json=eab1c3fe1bbcaea31ff64f6a32a5e7f56ecd4e80236ff50a454cfa17bbb50b04
run2/proposals/.applied/2026-10-16-memory-literature-review/preview/concepts/memkernel-memory-literature-review.md=63bedaba1c7073e51a721b5e8858ed39c9710a1ee6489146036ecdc5463600a3
run2/proposals/.applied/2026-10-16-memory-literature-review/preview/decisions/memkernel-tiered-memory-decision.md=8ae206acd384cdf0d52f60910daa68cc40be69a284c26c25d92d2abe1954f13a
run2/proposals/.applied/2026-10-16-memory-literature-review/preview/index.md=e8815cb1c2af1cb6b14b17400d77c2b876030f71743dafe86cd2f35f9c14d7af
run2/proposals/.applied/2026-10-16-memory-literature-review/preview/log.md=ef64468447f9cd19b9eb20b9b8a28487d66607b7b0a85e381334408e23ff71e8
run2/proposals/.applied/2026-10-16-memory-tiers/.ingest-snapshot/plan.json=b487ea2db93e3cb0e87cb75a58cc850a47896a008aa9136863002583b8c33d5b
run2/proposals/.applied/2026-10-16-memory-tiers/.ingest-snapshot/preview/concepts/memkernel-tiered-memory.md=d7f9f394f685d5aff5f1c0ceb3c743794a7d57f20acd6c4aa3fcd09818df5160
run2/proposals/.applied/2026-10-16-memory-tiers/.ingest-snapshot/preview/log.md=7a3484c91a0592397e097280baf37e561332570659a545ce991e42b724f3ff9e
run2/proposals/.applied/2026-10-16-memory-tiers/plan.json=b487ea2db93e3cb0e87cb75a58cc850a47896a008aa9136863002583b8c33d5b
run2/proposals/.applied/2026-10-16-memory-tiers/preview/concepts/memkernel-tiered-memory.md=d7f9f394f685d5aff5f1c0ceb3c743794a7d57f20acd6c4aa3fcd09818df5160
run2/proposals/.applied/2026-10-16-memory-tiers/preview/log.md=7a3484c91a0592397e097280baf37e561332570659a545ce991e42b724f3ff9e
run2/proposals/.applied/2026-10-16-roadmap/.ingest-snapshot/plan.json=992ca459c4b04fbd746cc909713734a0c3041ea44a7ca7d2c4f5943a9757f1c6
run2/proposals/.applied/2026-10-16-roadmap/.ingest-snapshot/preview/concepts/memkernel-roadmap.md=61bf574afe95454d07fa0f4ffedeb015f2644df5b5b2fb0be047263b21c2007b
run2/proposals/.applied/2026-10-16-roadmap/.ingest-snapshot/preview/index.md=50f51c074ce7b63962f570c32fc4bb5eafaa3cd8946fbb091898c281b175ad75
run2/proposals/.applied/2026-10-16-roadmap/.ingest-snapshot/preview/log.md=6b3bd01ad416dceb7fb2c6c2feef8a8a60d51cbd31a3ca9355c69cfb2ab670d5
run2/proposals/.applied/2026-10-16-roadmap/plan.json=992ca459c4b04fbd746cc909713734a0c3041ea44a7ca7d2c4f5943a9757f1c6
run2/proposals/.applied/2026-10-16-roadmap/preview/concepts/memkernel-roadmap.md=61bf574afe95454d07fa0f4ffedeb015f2644df5b5b2fb0be047263b21c2007b
run2/proposals/.applied/2026-10-16-roadmap/preview/index.md=50f51c074ce7b63962f570c32fc4bb5eafaa3cd8946fbb091898c281b175ad75
run2/proposals/.applied/2026-10-16-roadmap/preview/log.md=6b3bd01ad416dceb7fb2c6c2feef8a8a60d51cbd31a3ca9355c69cfb2ab670d5
run2/results.json=90872668d92439c9476decfdbf45c3787af67095ee936e68f92f74a35f8feede
run2/wiki/.audit/ingest-log.md=4b0c4064c01e44b9a30faf3115b73667f68881f92efb9095ce3d03a9059b4330
run2/wiki/.audit/proposals/2026-10-16-ADR-007-tiered-memory/plan.json=b9f39d6c8ef27a2c2bb8caae027440b86802820af9c5293764b4d22a7c6cd149
run2/wiki/.audit/proposals/2026-10-16-ADR-007-tiered-memory/proposal.md=22cba3da64e5923349db438e46a7751f5e0ae855c0924ae160267c723e8a7d62
run2/wiki/.audit/proposals/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/plan.json=8429737362a19898bc64264d2398d49cf05c76c31ce0462e5fbc9eb6a21f2834
run2/wiki/.audit/proposals/2026-10-16-ADR-008-llm-wiki-as-semantic-layer/proposal.md=52ba79cdcc6a6c241ded783d066cc42c1e9523e1679a559f395c2d7c6b07ae5b
run2/wiki/.audit/proposals/2026-10-16-README/plan.json=349254c25b6090b2a902e35463feaf94dc317dd3df01a0c263bfb076caccaa46
run2/wiki/.audit/proposals/2026-10-16-README/proposal.md=2000d5c7ec18e1e91a3415a6d35b11e364232f06751777f31494c4413305b2e6
run2/wiki/.audit/proposals/2026-10-16-harness-integration/plan.json=77fd9e71092fbcb9b9b25174ea7e69857cdc19ad513304f4dd033e92b8b9af2f
run2/wiki/.audit/proposals/2026-10-16-harness-integration/proposal.md=9dda4a74a1f207d6ee6a2d034779e037f953ba5b9cfb3c81f00df37cdcef9df8
run2/wiki/.audit/proposals/2026-10-16-memory-literature-review/plan.json=eab1c3fe1bbcaea31ff64f6a32a5e7f56ecd4e80236ff50a454cfa17bbb50b04
run2/wiki/.audit/proposals/2026-10-16-memory-literature-review/proposal.md=98dfdb9a4927c5f4f984998ff210115d4108d709f5c343aa709406c0b96358c6
run2/wiki/.audit/proposals/2026-10-16-memory-tiers/plan.json=b487ea2db93e3cb0e87cb75a58cc850a47896a008aa9136863002583b8c33d5b
run2/wiki/.audit/proposals/2026-10-16-memory-tiers/proposal.md=69506c491b09434909229c39dd768c4759d7a4dbae549ddadaf783277dd958b2
run2/wiki/.audit/proposals/2026-10-16-roadmap/plan.json=992ca459c4b04fbd746cc909713734a0c3041ea44a7ca7d2c4f5943a9757f1c6
run2/wiki/.audit/proposals/2026-10-16-roadmap/proposal.md=01ed3d2c371cd7b341375b68fbd648657dcb59c5445f1f364f9ee1bb8d8b4470
run2/wiki/concepts/memkernel-harness-integration.md=d09077537f0a885560c19373d61e77a6de9d0892e155206daa3fe5e44cec893c
run2/wiki/concepts/memkernel-memory-literature-review.md=63bedaba1c7073e51a721b5e8858ed39c9710a1ee6489146036ecdc5463600a3
run2/wiki/concepts/memkernel-roadmap.md=61bf574afe95454d07fa0f4ffedeb015f2644df5b5b2fb0be047263b21c2007b
run2/wiki/concepts/memkernel-tiered-memory.md=d7f9f394f685d5aff5f1c0ceb3c743794a7d57f20acd6c4aa3fcd09818df5160
run2/wiki/concepts/memkernel-wiki-bridge-and-health.md=dd73ce6b5663940855df3ae1fe6e1ae68bba7969cd99cb5902176d264b34cce3
run2/wiki/decisions/memkernel-tiered-memory-decision.md=8ae206acd384cdf0d52f60910daa68cc40be69a284c26c25d92d2abe1954f13a
run2/wiki/decisions/memkernel-wiki-semantic-layer-decision.md=3ec7146e315031ce27c20be1f93542ab141011f481e8fd251db71fc61f782c0d
run2/wiki/index.md=822568f636be0a3deed0197fa23cf0ed3bb88366467873ce0c21f53c52a971f6
run2/wiki/log.md=d21546f8aa9c108f21f23cf082c2b45a4483216c362f983e9a26c9508a4e862f
run2/wiki/playbooks/memkernel-install-troubleshooting.md=7be63d03d24d29e57d0fb909daa6cb121de058f96598653d2ccf287855072fc3
run2/wiki/workflows/memkernel-claude-code-setup.md=c302df8675f0afa2bdcc080d8e3c4afacd618383db2dab825268b6fc6e97d145
wiki/.audit/ingest-log.md=0e178e0f9d65e577005d84aa14d58379c30f9f34e61abc2113e696b95dc647db
wiki/.audit/proposals/2026-10-15-ADR-009-rlm-studio-for-documents/plan.json=ed640a73f605954437e1d9511a403e8d0e3908f565161d6f1744b6079c0bb109
wiki/.audit/proposals/2026-10-15-ADR-009-rlm-studio-for-documents/proposal.md=750a6d3b5e65665690afdfe954b4627e4214911ed1a870c87517983ec1274f06
wiki/decisions/rlm-studio-document-layer.md=4dadf0ae6bebad9a25523d9a0ab22263aadc6ce98234ed59b95ed85a926f54e9
wiki/index.md=ad8e2b41e7e657654ab4ad69d131c3d37dfc3516a8ea6f9f1401526ead0dcfe5
wiki/log.md=f6f69335e865b3e86e218de3d62e2807dd22a9cff305294f4ef99454ff02ec27
wiki/schema/WIKI_MAINTAINER.md=7ac0e97ebd281e292038078c6ae33fb8a2f068934a2666cfae09af1878660017
wiki/schema/__init__.py=e88b162b7d82c59e0c07f3294fecd7353dfbb5172b172aba78896f5aea0fd183
wiki/schema/audit-rules.md=271226450d7da00fe3a385a8ddf494ccb9015e2f81a636baa395a1ff9ab180ff
wiki/schema/citation-rules.md=ae2bf273d208119f8e7965caf9d23d51da7416ceb10ca9b98adc25614407502b
wiki/schema/ingest-rules.md=7aa6fb29f4ba3f578f83f2f747963f0695d51fa082871ab59853ff5125f32387
wiki/schema/lint-rules.md=d14d5cf2b86a9776d330c7ba22e1497ba14a2b0e90c716813c893366624fa711
wiki/schema/page-types.md=29be97579d3c6f05604c5772bb283dbc5a740cfe37b445eb95ef96a8e9c71b4f
"""

# The held-out set (FR-026, FR-028): every tracked file under these directories and these two files are frozen
# once ``heldout/wiki/`` exists; the manifest, the results and the attempt marker are written by the one run.
HELDOUT_FROZEN_DIRS = ("wiki", "proposals", "corpus")
HELDOUT_FROZEN_FILES = ("questions.json", "gold.json")
HELDOUT_RUN_WRITES = ("manifest.json", "results.json", "run-attempt.json")
HELDOUT_POST_HOC_GLOB = "results-post-hoc-*.json"

# ``<path under eval/navigation/heldout>=<sha256>``, pinned from ``git ls-files`` on 2026-10-28 after the freeze
# (FR-027): the corpus, the frozen wiki, the archived proposals, the questions and the gold. Never ``manifest.json``,
# ``results.json``, ``run-attempt.json`` or ``results-post-hoc-*.json``, which the run writes.
HELDOUT_PINS = """
corpus/README.md=a063f0d253be8ff704541b0dc4d56a962ccb5bb3dc725a7a769a457013fa020d
corpus/apps__demo__README.md=2097b97a736e1adbe1421140148670568c2667fd8d0721b03920bd6c00ddfbbc
corpus/packages__core__README.md=ed7022f683dde23afa3d51a8aee522ce92941820e0a76081acbf016675a00507
corpus/packages__maplibre__README.md=3bdc61071ff4e2d4a144ff6567adfcfcbfc0e53b15b4f60e66639852ac4a357e
corpus/packages__offline-pmtiles__README.md=d917f41c629d43d137bd5f0066bfff2fbfaad59c5a348164f725ad1905e04f1f
corpus/packages__react__README.md=69b28a42be315d204a680d49984f73557aab61665f75e6de1cb707b18fa0e430
corpus/packages__recorder-web__README.md=c492f7f3aede097d084bcdef5e2c6845850e4d768b4c2307dd0236f727181950
corpus/packages__storage-idb__README.md=2687ffd97fddfd116e1298e95066c52947cbe405fda12694759d5288f715196c
gold.json=791aa0da35ccef086e3f3a20f83e93c4757f0970f1c9004095a60fd4b37cd8a8
proposals/.applied/2026-10-28-README/.ingest-snapshot/plan.json=f5394a6f294729051f32db7f756e0ce52572d5cbf19c8a2a9087be7f0bbe6829
proposals/.applied/2026-10-28-README/.ingest-snapshot/preview/concepts/harness-neutral-specs-contract.md=7110808a3fe91b52dfb46a8cf30e865ce80b8fea27dfa11cbef84d58e98b44d5
proposals/.applied/2026-10-28-README/.ingest-snapshot/preview/concepts/map-atlas-engine.md=9b9aca5b5e61ad1300647ebf5d20aebbedc60541852cc4ec7d7f7ebb9216d756
proposals/.applied/2026-10-28-README/.ingest-snapshot/preview/concepts/map-data-licensing.md=ccd8e903b33cdee04fd17aa5aec35720bd0f1c3e4d20affa9514195d173ed291
proposals/.applied/2026-10-28-README/.ingest-snapshot/preview/index.md=f917a718ba8913a6dbaf711c827f6663f063d15ec75a8f5694273a8756bd430e
proposals/.applied/2026-10-28-README/.ingest-snapshot/preview/index.md.2=f67145c524147be6756120b519247665eac23400448e8abf860fb7c1836d030a
proposals/.applied/2026-10-28-README/.ingest-snapshot/preview/index.md.3=3f89cfab657c5178e4f3453d0599e3d27adf76ff504b1b227ab7f45c68d5e8b0
proposals/.applied/2026-10-28-README/.ingest-snapshot/preview/log.md=fa85128b5efc8dd9f9ee57d114147f856d866ed6d7104a8956aa37d4235b5e92
proposals/.applied/2026-10-28-README/.ingest-snapshot/preview/log.md.2=14b98e5f7e18319ba0863eae39755a7b8426a04f00ad6d0592687393042e5b53
proposals/.applied/2026-10-28-README/.ingest-snapshot/preview/log.md.3=1901401f30a070496ae4e9a24365e39de29e94fcf8bf461246debf340d6c3f0e
proposals/.applied/2026-10-28-README/plan.json=f5394a6f294729051f32db7f756e0ce52572d5cbf19c8a2a9087be7f0bbe6829
proposals/.applied/2026-10-28-README/preview/concepts/harness-neutral-specs-contract.md=7110808a3fe91b52dfb46a8cf30e865ce80b8fea27dfa11cbef84d58e98b44d5
proposals/.applied/2026-10-28-README/preview/concepts/map-atlas-engine.md=9b9aca5b5e61ad1300647ebf5d20aebbedc60541852cc4ec7d7f7ebb9216d756
proposals/.applied/2026-10-28-README/preview/concepts/map-data-licensing.md=ccd8e903b33cdee04fd17aa5aec35720bd0f1c3e4d20affa9514195d173ed291
proposals/.applied/2026-10-28-README/preview/index.md=f917a718ba8913a6dbaf711c827f6663f063d15ec75a8f5694273a8756bd430e
proposals/.applied/2026-10-28-README/preview/index.md.2=f67145c524147be6756120b519247665eac23400448e8abf860fb7c1836d030a
proposals/.applied/2026-10-28-README/preview/index.md.3=3f89cfab657c5178e4f3453d0599e3d27adf76ff504b1b227ab7f45c68d5e8b0
proposals/.applied/2026-10-28-README/preview/log.md=fa85128b5efc8dd9f9ee57d114147f856d866ed6d7104a8956aa37d4235b5e92
proposals/.applied/2026-10-28-README/preview/log.md.2=14b98e5f7e18319ba0863eae39755a7b8426a04f00ad6d0592687393042e5b53
proposals/.applied/2026-10-28-README/preview/log.md.3=1901401f30a070496ae4e9a24365e39de29e94fcf8bf461246debf340d6c3f0e
proposals/.applied/2026-10-28-README/receipt.json=5c3ed8375626366642426a6fa69f931e0c530f93bc29589fc664f4e33a0b1358
proposals/.applied/2026-10-28-apps__demo__README/.ingest-snapshot/plan.json=3a1f0b827b380034c3152fdcbe9a6daae5b8ef40b1f8b313902b9237b0ffaebc
proposals/.applied/2026-10-28-apps__demo__README/.ingest-snapshot/preview/concepts/map-atlas-engine.md=a8bcdb39639135eca1842247aadc448317906db226cecab1c96fb36f2aff6901
proposals/.applied/2026-10-28-apps__demo__README/.ingest-snapshot/preview/concepts/map-data-licensing.md=1bccc07f5f5d56cda611cc08937564955946d4fd4aa7818e645ec55acdd25341
proposals/.applied/2026-10-28-apps__demo__README/.ingest-snapshot/preview/concepts/mapatlas-demo-app.md=0dd2e3d2f24e98284464e5a65aeac8300feaeb87f4f74127c6c11f64d90d17e3
proposals/.applied/2026-10-28-apps__demo__README/.ingest-snapshot/preview/concepts/mapatlas-offline-pmtiles-package.md=ee36dda28e757bb9e6a206c20cc44516b5952f495b3e9f02d36fc03832af9498
proposals/.applied/2026-10-28-apps__demo__README/.ingest-snapshot/preview/index.md=e32e207203e4e8ee2607b75bea4e850e11f20e4367ce8abd6509f092f047c393
proposals/.applied/2026-10-28-apps__demo__README/.ingest-snapshot/preview/log.md=0ef444eb11ddc3f5dedb705ad6bff8d3273b628bfd64eccb93bff6268596c765
proposals/.applied/2026-10-28-apps__demo__README/plan.json=3a1f0b827b380034c3152fdcbe9a6daae5b8ef40b1f8b313902b9237b0ffaebc
proposals/.applied/2026-10-28-apps__demo__README/preview/concepts/map-atlas-engine.md=a8bcdb39639135eca1842247aadc448317906db226cecab1c96fb36f2aff6901
proposals/.applied/2026-10-28-apps__demo__README/preview/concepts/map-data-licensing.md=1bccc07f5f5d56cda611cc08937564955946d4fd4aa7818e645ec55acdd25341
proposals/.applied/2026-10-28-apps__demo__README/preview/concepts/mapatlas-demo-app.md=0dd2e3d2f24e98284464e5a65aeac8300feaeb87f4f74127c6c11f64d90d17e3
proposals/.applied/2026-10-28-apps__demo__README/preview/concepts/mapatlas-offline-pmtiles-package.md=ee36dda28e757bb9e6a206c20cc44516b5952f495b3e9f02d36fc03832af9498
proposals/.applied/2026-10-28-apps__demo__README/preview/index.md=e32e207203e4e8ee2607b75bea4e850e11f20e4367ce8abd6509f092f047c393
proposals/.applied/2026-10-28-apps__demo__README/preview/log.md=0ef444eb11ddc3f5dedb705ad6bff8d3273b628bfd64eccb93bff6268596c765
proposals/.applied/2026-10-28-apps__demo__README/receipt.json=1a0b653a9b3e27531a7df206ad3867d86e71b7a474133d2e0366470f7057df07
proposals/.applied/2026-10-28-packages__core__README/.ingest-snapshot/plan.json=1de9945c8e62abba3e1ad79e91eb62e3ff78b0dc2ce6682b5e805ed5456860a1
proposals/.applied/2026-10-28-packages__core__README/.ingest-snapshot/preview/concepts/harness-neutral-specs-contract.md=f681b18df59abc442b13ddd0e456773a475694a862b76f2bd983f2063c0077e3
proposals/.applied/2026-10-28-packages__core__README/.ingest-snapshot/preview/concepts/map-atlas-engine.md=09c503e5982647a4913e43c5f70502b64c5ae6b648316a8887d723dd7150f82e
proposals/.applied/2026-10-28-packages__core__README/.ingest-snapshot/preview/concepts/mapatlas-core-package.md=6886362df34aa987f7f95c14a6dd4f58f26091e2661e333d2c46713f3698748e
proposals/.applied/2026-10-28-packages__core__README/.ingest-snapshot/preview/index.md=8780f4956ecf7bef16ff13a8d0220e0d8fb9bb3ce4dc36b70f55426f98a3183a
proposals/.applied/2026-10-28-packages__core__README/.ingest-snapshot/preview/log.md=91f882ac9015374f3c855b960b8c937897981c504380551a4c39601e2f3e17e0
proposals/.applied/2026-10-28-packages__core__README/plan.json=1de9945c8e62abba3e1ad79e91eb62e3ff78b0dc2ce6682b5e805ed5456860a1
proposals/.applied/2026-10-28-packages__core__README/preview/concepts/harness-neutral-specs-contract.md=f681b18df59abc442b13ddd0e456773a475694a862b76f2bd983f2063c0077e3
proposals/.applied/2026-10-28-packages__core__README/preview/concepts/map-atlas-engine.md=09c503e5982647a4913e43c5f70502b64c5ae6b648316a8887d723dd7150f82e
proposals/.applied/2026-10-28-packages__core__README/preview/concepts/mapatlas-core-package.md=6886362df34aa987f7f95c14a6dd4f58f26091e2661e333d2c46713f3698748e
proposals/.applied/2026-10-28-packages__core__README/preview/index.md=8780f4956ecf7bef16ff13a8d0220e0d8fb9bb3ce4dc36b70f55426f98a3183a
proposals/.applied/2026-10-28-packages__core__README/preview/log.md=91f882ac9015374f3c855b960b8c937897981c504380551a4c39601e2f3e17e0
proposals/.applied/2026-10-28-packages__core__README/receipt.json=82e3b43f365504ecb641e41571b12b7bc565092d1bc42fe7a6ef14173b91b10c
proposals/.applied/2026-10-28-packages__maplibre__README/.ingest-snapshot/plan.json=897cfb979e750a3a06ae226465ca7fe1b9dcaaee2b24fa1d5e5917c9c2f76e09
proposals/.applied/2026-10-28-packages__maplibre__README/.ingest-snapshot/preview/concepts/harness-neutral-specs-contract.md=58814190f0ab1d4bc7f15002db4a319cf1ccb44d797fc3cfe8ec9da2a40a360e
proposals/.applied/2026-10-28-packages__maplibre__README/.ingest-snapshot/preview/concepts/map-atlas-engine.md=96d51eb3c99512e330626abe806e95d8c6b270975fe0db3867041c101743a753
proposals/.applied/2026-10-28-packages__maplibre__README/.ingest-snapshot/preview/concepts/map-data-licensing.md=d43f813e098ee128a9be4c1d8836f8885932a17abef0034824df9254cdca86f1
proposals/.applied/2026-10-28-packages__maplibre__README/.ingest-snapshot/preview/concepts/mapatlas-maplibre-package.md=b0a0df05418e8199eb08b0c032faee0962b985b91546009b6499f74515818e51
proposals/.applied/2026-10-28-packages__maplibre__README/.ingest-snapshot/preview/index.md=5b0da6c13800e59c40870d95c0b33c27e5a20e5c95c57c38e5a044022f03a3a6
proposals/.applied/2026-10-28-packages__maplibre__README/.ingest-snapshot/preview/log.md=efe74bc19162cb7a350106730f17ec42e7ddb5aafc6c9a56f1acbd0ae57376c4
proposals/.applied/2026-10-28-packages__maplibre__README/plan.json=897cfb979e750a3a06ae226465ca7fe1b9dcaaee2b24fa1d5e5917c9c2f76e09
proposals/.applied/2026-10-28-packages__maplibre__README/preview/concepts/harness-neutral-specs-contract.md=58814190f0ab1d4bc7f15002db4a319cf1ccb44d797fc3cfe8ec9da2a40a360e
proposals/.applied/2026-10-28-packages__maplibre__README/preview/concepts/map-atlas-engine.md=96d51eb3c99512e330626abe806e95d8c6b270975fe0db3867041c101743a753
proposals/.applied/2026-10-28-packages__maplibre__README/preview/concepts/map-data-licensing.md=d43f813e098ee128a9be4c1d8836f8885932a17abef0034824df9254cdca86f1
proposals/.applied/2026-10-28-packages__maplibre__README/preview/concepts/mapatlas-maplibre-package.md=b0a0df05418e8199eb08b0c032faee0962b985b91546009b6499f74515818e51
proposals/.applied/2026-10-28-packages__maplibre__README/preview/index.md=5b0da6c13800e59c40870d95c0b33c27e5a20e5c95c57c38e5a044022f03a3a6
proposals/.applied/2026-10-28-packages__maplibre__README/preview/log.md=efe74bc19162cb7a350106730f17ec42e7ddb5aafc6c9a56f1acbd0ae57376c4
proposals/.applied/2026-10-28-packages__maplibre__README/receipt.json=ee751588131b7356225ae43863c0469789c59cd34fc35bac43b35e28914e363c
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/.ingest-snapshot/plan.json=283164a2714d65e106b3dce46ff500d64c854be58cf0fa14125b8ce31b5fb362
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/.ingest-snapshot/preview/concepts/harness-neutral-specs-contract.md=e9403b7d6ab9101259ddbc0dd68e7698992178f082baf0739997354610827e27
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/.ingest-snapshot/preview/concepts/map-atlas-engine.md=7c72e6207fc5ea928ea7e13f41ef983732b3ab61db91d704cc32a14db635ca9b
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/.ingest-snapshot/preview/concepts/map-data-licensing.md=73b6b539cfb06f4f6794632337155f694cf8ebf2c9110a8d5be73d33534b416e
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/.ingest-snapshot/preview/concepts/mapatlas-offline-pmtiles-package.md=133ef56b0aa392b072fc916a4f151b04c4da3349b4443369864b97b3fe20f93b
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/.ingest-snapshot/preview/index.md=8f807088b09e527dd49771d6a122b9427ed56f2f22ffc5e3875aef1ccb39c90d
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/.ingest-snapshot/preview/log.md=faa9e21580af3cc129ef2ae094e1e062b6befa02b1b3bd450b63a5371254cd26
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/plan.json=283164a2714d65e106b3dce46ff500d64c854be58cf0fa14125b8ce31b5fb362
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/preview/concepts/harness-neutral-specs-contract.md=e9403b7d6ab9101259ddbc0dd68e7698992178f082baf0739997354610827e27
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/preview/concepts/map-atlas-engine.md=7c72e6207fc5ea928ea7e13f41ef983732b3ab61db91d704cc32a14db635ca9b
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/preview/concepts/map-data-licensing.md=73b6b539cfb06f4f6794632337155f694cf8ebf2c9110a8d5be73d33534b416e
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/preview/concepts/mapatlas-offline-pmtiles-package.md=133ef56b0aa392b072fc916a4f151b04c4da3349b4443369864b97b3fe20f93b
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/preview/index.md=8f807088b09e527dd49771d6a122b9427ed56f2f22ffc5e3875aef1ccb39c90d
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/preview/log.md=faa9e21580af3cc129ef2ae094e1e062b6befa02b1b3bd450b63a5371254cd26
proposals/.applied/2026-10-28-packages__offline-pmtiles__README/receipt.json=0d0d6db6baaffd9e279b3632d74eb99aec42406de2504be276cb8c2dac451a47
proposals/.applied/2026-10-28-packages__react__README/.ingest-snapshot/plan.json=bd6bf20867e091fb67b6094c4f7eb073aa921b538b4c2db8c5e2c016f6a6dd70
proposals/.applied/2026-10-28-packages__react__README/.ingest-snapshot/preview/concepts/harness-neutral-specs-contract.md=b4e595dd6e88a2c549aa62d418c1662c7e19621f045300ddd628b1faa898fcf8
proposals/.applied/2026-10-28-packages__react__README/.ingest-snapshot/preview/concepts/map-atlas-engine.md=da5c7a336d8b3a31001db5b0b4b2de9062a58f23ceeb4ae6961af761eb93b799
proposals/.applied/2026-10-28-packages__react__README/.ingest-snapshot/preview/concepts/mapatlas-react-package.md=e61a0e204d443f24705444d6848c75e0e05b2c6a41eae2a5964cda20249a0c31
proposals/.applied/2026-10-28-packages__react__README/.ingest-snapshot/preview/index.md=5f92b1b77136514c06b7715475c27eefc44d86a1feda643324409685af195e81
proposals/.applied/2026-10-28-packages__react__README/.ingest-snapshot/preview/log.md=e593fe28c3cb9d35e7256977806468d523b11750c01ec905fb366f6e124bf327
proposals/.applied/2026-10-28-packages__react__README/plan.json=bd6bf20867e091fb67b6094c4f7eb073aa921b538b4c2db8c5e2c016f6a6dd70
proposals/.applied/2026-10-28-packages__react__README/preview/concepts/harness-neutral-specs-contract.md=b4e595dd6e88a2c549aa62d418c1662c7e19621f045300ddd628b1faa898fcf8
proposals/.applied/2026-10-28-packages__react__README/preview/concepts/map-atlas-engine.md=da5c7a336d8b3a31001db5b0b4b2de9062a58f23ceeb4ae6961af761eb93b799
proposals/.applied/2026-10-28-packages__react__README/preview/concepts/mapatlas-react-package.md=e61a0e204d443f24705444d6848c75e0e05b2c6a41eae2a5964cda20249a0c31
proposals/.applied/2026-10-28-packages__react__README/preview/index.md=5f92b1b77136514c06b7715475c27eefc44d86a1feda643324409685af195e81
proposals/.applied/2026-10-28-packages__react__README/preview/log.md=e593fe28c3cb9d35e7256977806468d523b11750c01ec905fb366f6e124bf327
proposals/.applied/2026-10-28-packages__react__README/receipt.json=599394d491583b0c65459a241ec0b02560cf1540f1f0696d56610390b909bbec
proposals/.applied/2026-10-28-packages__recorder-web__README/.ingest-snapshot/plan.json=fb7b68dde46fb67adfaefc3927b79631900378ca62bbc793749b55fd1b86aece
proposals/.applied/2026-10-28-packages__recorder-web__README/.ingest-snapshot/preview/concepts/harness-neutral-specs-contract.md=9afbd7c6ee50516851215340e23e297257adf83ee67b9b933dd68d4add4866f3
proposals/.applied/2026-10-28-packages__recorder-web__README/.ingest-snapshot/preview/concepts/map-atlas-engine.md=7fd061ce11f5eb3f3774d7ba6cb98da5f3b5826e0fe48272f63967fd4f5f7eb3
proposals/.applied/2026-10-28-packages__recorder-web__README/.ingest-snapshot/preview/concepts/mapatlas-react-package.md=f65a43268ab5be6a6a91b7d5b0e112697074cd3c2716c1fac07223928d244f40
proposals/.applied/2026-10-28-packages__recorder-web__README/.ingest-snapshot/preview/concepts/mapatlas-recorder-web-package.md=30a579af45d27404806daaa97c4159fb9732cddc4012e8481e756b58da1d1731
proposals/.applied/2026-10-28-packages__recorder-web__README/.ingest-snapshot/preview/index.md=ba6884dbb9f4efc941b043ff02056387f62e08794718e926f989635e2dd587eb
proposals/.applied/2026-10-28-packages__recorder-web__README/.ingest-snapshot/preview/log.md=9ee3803345434843bde5ae34c15db48d30f12b4e981573326f947b405d2ae1e1
proposals/.applied/2026-10-28-packages__recorder-web__README/plan.json=fb7b68dde46fb67adfaefc3927b79631900378ca62bbc793749b55fd1b86aece
proposals/.applied/2026-10-28-packages__recorder-web__README/preview/concepts/harness-neutral-specs-contract.md=9afbd7c6ee50516851215340e23e297257adf83ee67b9b933dd68d4add4866f3
proposals/.applied/2026-10-28-packages__recorder-web__README/preview/concepts/map-atlas-engine.md=7fd061ce11f5eb3f3774d7ba6cb98da5f3b5826e0fe48272f63967fd4f5f7eb3
proposals/.applied/2026-10-28-packages__recorder-web__README/preview/concepts/mapatlas-react-package.md=f65a43268ab5be6a6a91b7d5b0e112697074cd3c2716c1fac07223928d244f40
proposals/.applied/2026-10-28-packages__recorder-web__README/preview/concepts/mapatlas-recorder-web-package.md=30a579af45d27404806daaa97c4159fb9732cddc4012e8481e756b58da1d1731
proposals/.applied/2026-10-28-packages__recorder-web__README/preview/index.md=ba6884dbb9f4efc941b043ff02056387f62e08794718e926f989635e2dd587eb
proposals/.applied/2026-10-28-packages__recorder-web__README/preview/log.md=9ee3803345434843bde5ae34c15db48d30f12b4e981573326f947b405d2ae1e1
proposals/.applied/2026-10-28-packages__recorder-web__README/receipt.json=076079c7626e671c6dfc27dc252b9d023fdf237fc5284fc2851f2f6e8316b559
proposals/.applied/2026-10-28-packages__storage-idb__README/.ingest-snapshot/plan.json=55773b60c61034ae2854c4df12327c49916b342889f1fbff18d2ab736b723b64
proposals/.applied/2026-10-28-packages__storage-idb__README/.ingest-snapshot/preview/concepts/harness-neutral-specs-contract.md=c936212d52dcd4721e26773cd379c78ab52f6de9e9a50fc6cdf26976c8653216
proposals/.applied/2026-10-28-packages__storage-idb__README/.ingest-snapshot/preview/concepts/map-atlas-engine.md=7e66f086d2aae3dfc86b8ac48e5c60689cb87dd0ab56ecd2b2bff9a62e215ac4
proposals/.applied/2026-10-28-packages__storage-idb__README/.ingest-snapshot/preview/concepts/mapatlas-core-package.md=a26e0695ea9c06c07e140ad67f1cd8b40aec7035a1871a2b4a5f3ebf47e0a546
proposals/.applied/2026-10-28-packages__storage-idb__README/.ingest-snapshot/preview/concepts/mapatlas-storage-idb-package.md=66cb8350de871f626badfd6d2107f207f49e035823d17234fa6bdee7466b6c93
proposals/.applied/2026-10-28-packages__storage-idb__README/.ingest-snapshot/preview/index.md=d1a3ac1b790b4389553390b35fd1818dba08b8f3a4a2a0a286f543779324daa1
proposals/.applied/2026-10-28-packages__storage-idb__README/.ingest-snapshot/preview/log.md=5a5999e7af06ce0d14351b96e4ec2eceb4e4b38a71b6150a52c72cca55ea102e
proposals/.applied/2026-10-28-packages__storage-idb__README/plan.json=55773b60c61034ae2854c4df12327c49916b342889f1fbff18d2ab736b723b64
proposals/.applied/2026-10-28-packages__storage-idb__README/preview/concepts/harness-neutral-specs-contract.md=c936212d52dcd4721e26773cd379c78ab52f6de9e9a50fc6cdf26976c8653216
proposals/.applied/2026-10-28-packages__storage-idb__README/preview/concepts/map-atlas-engine.md=7e66f086d2aae3dfc86b8ac48e5c60689cb87dd0ab56ecd2b2bff9a62e215ac4
proposals/.applied/2026-10-28-packages__storage-idb__README/preview/concepts/mapatlas-core-package.md=a26e0695ea9c06c07e140ad67f1cd8b40aec7035a1871a2b4a5f3ebf47e0a546
proposals/.applied/2026-10-28-packages__storage-idb__README/preview/concepts/mapatlas-storage-idb-package.md=66cb8350de871f626badfd6d2107f207f49e035823d17234fa6bdee7466b6c93
proposals/.applied/2026-10-28-packages__storage-idb__README/preview/index.md=d1a3ac1b790b4389553390b35fd1818dba08b8f3a4a2a0a286f543779324daa1
proposals/.applied/2026-10-28-packages__storage-idb__README/preview/log.md=5a5999e7af06ce0d14351b96e4ec2eceb4e4b38a71b6150a52c72cca55ea102e
proposals/.applied/2026-10-28-packages__storage-idb__README/receipt.json=59877bc07e150b5dbbf4d14a1b1adc59d2ed711f3c9a460e70abd521558a5807
questions.json=096b55c06ce8c6eb77518df9c9928d63f864cc0ee9144566b890688c64c91325
wiki/.audit/ingest-log.md=1066e03249617f17ac814f69dd8be9e3279c07fdc8fa2370d7888224af85849e
wiki/.audit/proposals/2026-10-28-README/plan.json=f5394a6f294729051f32db7f756e0ce52572d5cbf19c8a2a9087be7f0bbe6829
wiki/.audit/proposals/2026-10-28-README/proposal.md=292b4dc67dbae7c70e6b83a28baf74a8040e18d11e669c4f19716bc8f320fe79
wiki/.audit/proposals/2026-10-28-apps__demo__README/plan.json=3a1f0b827b380034c3152fdcbe9a6daae5b8ef40b1f8b313902b9237b0ffaebc
wiki/.audit/proposals/2026-10-28-apps__demo__README/proposal.md=5dc001ef3e6979de78bf084ba494fb395b3461f2417c034fb350f2a9b1c5c33b
wiki/.audit/proposals/2026-10-28-packages__core__README/plan.json=1de9945c8e62abba3e1ad79e91eb62e3ff78b0dc2ce6682b5e805ed5456860a1
wiki/.audit/proposals/2026-10-28-packages__core__README/proposal.md=27715efad63454a5118ab96908d0c83e3a8e7486eaa74286fd2c4f3eb006194e
wiki/.audit/proposals/2026-10-28-packages__maplibre__README/plan.json=897cfb979e750a3a06ae226465ca7fe1b9dcaaee2b24fa1d5e5917c9c2f76e09
wiki/.audit/proposals/2026-10-28-packages__maplibre__README/proposal.md=b59bcf981d3d1557686492ed3164971b6c223243651429388a5e2f8a19c42210
wiki/.audit/proposals/2026-10-28-packages__offline-pmtiles__README/plan.json=283164a2714d65e106b3dce46ff500d64c854be58cf0fa14125b8ce31b5fb362
wiki/.audit/proposals/2026-10-28-packages__offline-pmtiles__README/proposal.md=8f8758f88b20b68ce0c88b5bcd4bf0527ea37931f0a132bab802afaaf4a2a539
wiki/.audit/proposals/2026-10-28-packages__react__README/plan.json=bd6bf20867e091fb67b6094c4f7eb073aa921b538b4c2db8c5e2c016f6a6dd70
wiki/.audit/proposals/2026-10-28-packages__react__README/proposal.md=22d588529c614296000f9502fd7a81fc93ef51af99503d339e88a31e52793559
wiki/.audit/proposals/2026-10-28-packages__recorder-web__README/plan.json=fb7b68dde46fb67adfaefc3927b79631900378ca62bbc793749b55fd1b86aece
wiki/.audit/proposals/2026-10-28-packages__recorder-web__README/proposal.md=6db58876b2c85fe5777f33ac7cfc73d0c1b4aa4f4b5674fa0f3ba1ca406d3316
wiki/.audit/proposals/2026-10-28-packages__storage-idb__README/plan.json=55773b60c61034ae2854c4df12327c49916b342889f1fbff18d2ab736b723b64
wiki/.audit/proposals/2026-10-28-packages__storage-idb__README/proposal.md=4d09857f0a9625bfe292ac1d37ad6fb85fa611e7bb9645bbdace687fc2c08f47
wiki/.wiki-studio.json=1a03caf0727cd6d3116576f6a429c3d3b04532ec6cc7e45ee15bffb205b54592
wiki/concepts/harness-neutral-specs-contract.md=c936212d52dcd4721e26773cd379c78ab52f6de9e9a50fc6cdf26976c8653216
wiki/concepts/map-atlas-engine.md=a8bcdb39639135eca1842247aadc448317906db226cecab1c96fb36f2aff6901
wiki/concepts/map-data-licensing.md=1bccc07f5f5d56cda611cc08937564955946d4fd4aa7818e645ec55acdd25341
wiki/concepts/mapatlas-core-package.md=a26e0695ea9c06c07e140ad67f1cd8b40aec7035a1871a2b4a5f3ebf47e0a546
wiki/concepts/mapatlas-demo-app.md=0dd2e3d2f24e98284464e5a65aeac8300feaeb87f4f74127c6c11f64d90d17e3
wiki/concepts/mapatlas-maplibre-package.md=b0a0df05418e8199eb08b0c032faee0962b985b91546009b6499f74515818e51
wiki/concepts/mapatlas-offline-pmtiles-package.md=ee36dda28e757bb9e6a206c20cc44516b5952f495b3e9f02d36fc03832af9498
wiki/concepts/mapatlas-react-package.md=f65a43268ab5be6a6a91b7d5b0e112697074cd3c2716c1fac07223928d244f40
wiki/concepts/mapatlas-recorder-web-package.md=30a579af45d27404806daaa97c4159fb9732cddc4012e8481e756b58da1d1731
wiki/concepts/mapatlas-storage-idb-package.md=66cb8350de871f626badfd6d2107f207f49e035823d17234fa6bdee7466b6c93
wiki/index.md=3d1e27b0c01649dbfa61432f8cc3ea30305d37268517520caa81de433fbd7b33
wiki/log.md=07808151acc5ba1e705b194edf701d5899fde5abe16bfc44705edc13760e64bb
"""


def _parse(block: str) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in block.split():
        path, _, digest = line.rpartition("=")
        pins[path] = digest
    return pins


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tracked(prefix: str) -> list[str]:
    """``git ls-files`` under ``prefix`` (a path from the repository root), relative to it: how the pins were taken."""
    listed = subprocess.run(
        ["git", "ls-files", "--", prefix], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [path.removeprefix(f"{prefix}/") for path in listed]


def _is_git_checkout() -> bool:
    return shutil.which("git") is not None and (REPO_ROOT / ".git").exists()


def _written_by_the_run(rel: str) -> bool:
    return rel in HELDOUT_RUN_WRITES or fnmatch.fnmatch(rel, HELDOUT_POST_HOC_GLOB)


def _heldout_pin_problems(root: Path, tracked: list[str], pins: dict[str, str]) -> list[str]:
    """What is wrong with ``pins`` for the held-out tree at ``root``; empty when every frozen file is pinned unchanged.

    A tracked file under a frozen directory (or one of the two frozen files)
    without a pin, a pin on a file the run writes, and a pinned file that is
    missing or no longer hashes to its pin are each one problem.
    """
    frozen = {rel for rel in tracked if rel.split("/", 1)[0] in HELDOUT_FROZEN_DIRS or rel in HELDOUT_FROZEN_FILES}
    problems = [f"{rel} is frozen but not pinned" for rel in sorted(frozen - set(pins))]
    for rel in sorted(pins):
        if _written_by_the_run(rel):
            problems.append(f"{rel} is written by the run and must not be pinned")
        elif not (root / rel).is_file():
            problems.append(f"{rel} is pinned but missing")
        elif _sha256(root / rel) != pins[rel]:
            problems.append(f"{rel} changed; it is frozen")
    return problems


class TestFrozenRunsArePinned(unittest.TestCase):
    def test_every_pinned_file_is_unchanged(self) -> None:
        for rel, digest in _parse(FROZEN_PINS).items():
            with self.subTest(path=rel):
                self.assertEqual(_sha256(NAVIGATION / rel), digest, f"eval/navigation/{rel} changed; it is frozen")

    def test_the_named_files_are_pinned(self) -> None:
        pins = _parse(FROZEN_PINS)
        for name in NAMED_FILES:
            with self.subTest(name=name):
                self.assertIn(name, pins)

    def test_every_tracked_file_under_a_frozen_directory_is_pinned(self) -> None:
        if not _is_git_checkout():
            self.skipTest("not a git checkout")
        tracked = {f"{d}/{rel}" for d in FROZEN_DIRS for rel in _tracked(f"eval/navigation/{d}")}
        pinned = {rel for rel in _parse(FROZEN_PINS) if rel.split("/", 1)[0] in FROZEN_DIRS}
        self.assertEqual(tracked, pinned)


class TestRunnerWritesNothingIntoFrozenDirectories(unittest.TestCase):
    def test_a_runner_pass_leaves_run2_unchanged(self) -> None:
        before = _tree_hash(RUN2)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = discovery.main(
                ["run", "--fixture", str(RUN2), "--shared", str(NAVIGATION), "--config", str(UNTUNED_CONFIG)]
            )
        self.assertEqual(code, 0)
        self.assertIn('"navigation"', out.getvalue())
        self.assertEqual(_tree_hash(RUN2), before)
        self.assertEqual(list(RUN2.glob(CACHE_GLOB)), [])
        self.assertEqual(list(NAVIGATION.glob(CACHE_GLOB)), [])

    def test_a_search_cache_inside_the_fixture_is_refused(self) -> None:
        cache = RUN2 / "cache.sqlite"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = discovery.main(
                ["run", "--fixture", str(RUN2), "--shared", str(NAVIGATION), "--search-cache", str(cache)]
            )
        self.assertEqual(code, 1)
        self.assertIn("FR-019", err.getvalue())
        self.assertFalse(cache.exists())


class TestHeldOutPins(unittest.TestCase):
    def test_every_pinned_heldout_file_is_unchanged(self) -> None:
        pins = _parse(HELDOUT_PINS)
        self.assertTrue(pins, "the held-out corpus is committed and pinned")
        for rel, digest in pins.items():
            with self.subTest(path=rel):
                self.assertFalse(_written_by_the_run(rel), f"HELDOUT_PINS pins {rel}, which the run writes")
                self.assertEqual(_sha256(HELDOUT / rel), digest, f"eval/navigation/heldout/{rel} changed; it is frozen")

    def test_the_frozen_heldout_set_is_pinned(self) -> None:
        """Once the wiki exists, every tracked frozen file is pinned and nothing the run writes is (FR-026)."""
        if not (HELDOUT / "wiki").exists():
            self.skipTest("heldout/wiki/ does not exist yet (the owner's ingest, FR-025)")
        if not _is_git_checkout():
            self.skipTest("not a git checkout")
        tracked = _tracked("eval/navigation/heldout")
        self.assertEqual(_heldout_pin_problems(HELDOUT, tracked, _parse(HELDOUT_PINS)), [])

    def test_the_pin_check_on_a_temporary_tree(self) -> None:
        frozen = (
            "wiki/index.md",
            "wiki/concepts/alpha.md",
            "wiki/.audit/ingest-log.md",
            "proposals/.applied/2026-10-30-README/plan.json",
            "corpus/README.md",
            "questions.json",
            "gold.json",
        )
        written = ("manifest.json", "results.json", "run-attempt.json", "results-post-hoc-rerun-1.json")
        unpinned = ("protocol.md", "ingest-logs/01-ingest.stdout.txt")  # tracked, neither frozen nor the run's
        tracked = [*frozen, *written, *unpinned]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in tracked:
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(rel, encoding="utf-8")
            pins = {rel: _sha256(root / rel) for rel in frozen}
            self.assertEqual(_heldout_pin_problems(root, tracked, pins), [])
            self.assertEqual(
                _heldout_pin_problems(root, tracked, {}),
                [f"{rel} is frozen but not pinned" for rel in sorted(frozen)],
                "an empty table fails once the frozen files exist",
            )
            for rel in written:
                with self.subTest(pinned=rel):
                    self.assertEqual(
                        _heldout_pin_problems(root, tracked, {**pins, rel: _sha256(root / rel)}),
                        [f"{rel} is written by the run and must not be pinned"],
                    )
            (root / "wiki/index.md").write_text("edited after the freeze", encoding="utf-8")
            self.assertEqual(_heldout_pin_problems(root, tracked, pins), ["wiki/index.md changed; it is frozen"])
            (root / "wiki/index.md").unlink()
            self.assertEqual(_heldout_pin_problems(root, tracked, pins), ["wiki/index.md is pinned but missing"])


if __name__ == "__main__":
    unittest.main()
