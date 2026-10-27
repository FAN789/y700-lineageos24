# Private builder resource profile

The build defaults to six compile jobs, four source-sync jobs, a 20-GiB Go builder memory limit, and a 40-GB ccache ceiling. A host administrator can set `Y700_BUILD_JOBS`, `Y700_SYNC_JOBS`, `Y700_GO_MEMORY_LIMIT`, and `Y700_CCACHE_MAXSIZE` in the Runner service environment. Invalid or excessive values fail before source modification.

An actual AOSP prebuilt nsjail probe must succeed before building. A build that reports Soong's sandbox fallback is rejected rather than accepted as a candidate. Container namespace smoke tests alone do not satisfy this check.

Moving source files, validating a retained OTA, producing a new candidate, promoting the OTA feed, and installing a device remain separate operations. A migration never promotes or flashes an artifact automatically.
