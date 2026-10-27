# Copyright (c) 2026 EGOGE
# SPDX-License-Identifier: Apache-2.0
"""The frozen evaluation runs are never edited (0.8.0 FR-019, FR-026).

Runs 1 and 2 call the live selector, so their numbers are only evidence while
their inputs stay byte for byte what was published. Every frozen file is pinned
here by sha256; the list was taken from ``git ls-files`` at pin time, so an
untracked file beside them is never pinned. The discovery runner keeps its
search cache in a temporary directory; a runner pass must leave run 2's tree
unchanged.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import shutil
import subprocess
import unittest
from pathlib import Path

from eval.navigation import discovery
from eval.navigation.run2_protocol import _tree_hash

NAVIGATION = Path(__file__).resolve().parents[1] / "eval" / "navigation"
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

# ``<path under eval/navigation/heldout>=<sha256>`` for the frozen held-out wiki, its archived proposals
# and its manifest (FR-026), added by the evidence PR once ``heldout/wiki/`` exists.
HELDOUT_PINS = """
"""


def _parse(block: str) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in block.split():
        path, _, digest = line.rpartition("=")
        pins[path] = digest
    return pins


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        if shutil.which("git") is None or not (NAVIGATION.parents[1] / ".git").exists():
            self.skipTest("not a git checkout")
        listed = subprocess.run(
            ["git", "ls-files", "--", *(f"eval/navigation/{d}" for d in FROZEN_DIRS)],
            cwd=NAVIGATION.parents[1],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        tracked = {path.removeprefix("eval/navigation/") for path in listed}
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
    def test_the_frozen_heldout_wiki_is_pinned(self) -> None:
        if not (HELDOUT / "wiki").exists():
            self.skipTest("heldout/wiki/ does not exist yet (the owner's ingest, FR-025)")
        pins = _parse(HELDOUT_PINS)
        self.assertTrue(pins, "heldout/wiki/ exists: pin its files, the archived proposals and the manifest (FR-026)")
        self.assertTrue(any(rel.startswith("wiki/") for rel in pins))
        for rel, digest in pins.items():
            with self.subTest(path=rel):
                self.assertEqual(_sha256(HELDOUT / rel), digest, f"eval/navigation/heldout/{rel} changed; it is frozen")


if __name__ == "__main__":
    unittest.main()
