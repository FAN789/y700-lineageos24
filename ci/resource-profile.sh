#!/usr/bin/env bash
# Conservative defaults for an 8-thread / 40-GiB private build host.
Y700_BUILD_JOBS=${Y700_BUILD_JOBS:-6}
Y700_SYNC_JOBS=${Y700_SYNC_JOBS:-4}
Y700_GO_MEMORY_LIMIT=${Y700_GO_MEMORY_LIMIT:-20GiB}
Y700_CCACHE_MAXSIZE=${Y700_CCACHE_MAXSIZE:-40G}
[[ "$Y700_BUILD_JOBS" =~ ^[1-8]$ ]] || { echo 'Build jobs must be between 1 and 8'; return 2; }
[[ "$Y700_SYNC_JOBS" =~ ^[1-8]$ ]] || { echo 'Sync jobs must be between 1 and 8'; return 2; }
[[ "$Y700_GO_MEMORY_LIMIT" =~ ^([4-9]|1[0-9]|2[0-4])GiB$ ]] || { echo 'Go memory limit must be 4GiB to 24GiB'; return 2; }
[[ "$Y700_CCACHE_MAXSIZE" =~ ^([1-9]|[1-7][0-9]|80)G$ ]] || { echo 'Ccache limit must be 1G to 80G'; return 2; }
export Y700_BUILD_JOBS Y700_SYNC_JOBS Y700_GO_MEMORY_LIMIT Y700_CCACHE_MAXSIZE
