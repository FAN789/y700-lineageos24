# 从固定源码重建

构建环境为 Linux x86_64；原构建在 WSL2 中使用 20 vCPU、40GB RAM、24GB swap，repo sync -j8，bacon -j12。资源仅供参考。以下命令是构建说明，不会由本仓库自动执行。

## 同步

安装 LineageOS 构建依赖、Git LFS、repo 和 Python3。保留所有项目自带许可证。

```sh
mkdir -p ~/android/y700 && cd ~/android/y700
repo init -u https://github.com/LineageOS/android.git -b lineage-24.0 --depth=1 --no-clone-bundle
```

把本仓库放在源码目录以外，以 `$PUBLIC` 表示它的绝对路径。

```sh
cp "$PUBLIC/manifests/resolved-manifest.xml" .repo/manifests/y700-release.xml
repo init -m y700-release.xml
repo sync -c -j8 --retry-fetches=3 --no-clone-bundle --no-tags --fail-fast
```

完整 manifest 已包含设备项目。不要再同时叠加 y700.xml，避免重复定义；y700.xml 供日常分支同步参考。

## 驱动输入

原构建使用 PRC ZUXOS 1.1.350 的真实软件文件，加上上游清单精确固定的兼容文件。软件 allowlist/哈希见 manifests/blob-inputs.json，兼容来源见 manifests/pinned-blob-provenance.json。

出于私密备份与原厂内容的分发边界，仓库不附个人原厂备份、解锁器或单独驱动包。准备本人可用的合法软件输入，按清单校验。使用设备树原生 extract-files.py，保留 check_elf=True 和完整 common 输入；即使 tablet 安装规则排除 phone 安装组，该组仍可能定义共享 DSP/recovery 依赖，不要删除或提供空文件。

```sh
PYTHONPATH=tools/extract-utils python3 device/lenovo/asphalt/extract-files.py /absolute/path/to/stock-software
```

原生提取逻辑包含上游 blob 修补和校验。若输入缺失，必须查明，不能跳过依赖或 ELF 检查。

## 有效补丁和构建

```sh
python3 "$PUBLIC/tools/apply-patches.py" --source "$PWD"
python3 "$PUBLIC/tools/verify-webview.py" --source "$PWD"
repo manifest -r -o resolved-for-build.xml
export BUILD_USERNAME=y700-builder BUILD_HOSTNAME=y700-lineage
export USE_CCACHE=1 CCACHE_DIR="$HOME/.cache/y700-ccache"
export SOONG_BUILDER_GOGC=50 SOONG_BUILDER_GOMEMLIMIT=28GiB
source build/envsetup.sh
breakfast asphalt userdebug
m -j12 bacon
```

原始构建 testkey/AVB flags3 保留并如实声明。新构建时间戳等可能导致二进制不同；本项目不承诺按位可复现。构建产物必须自行完成原生检查、签名/哈希/CRC、payload 分区容量与实机验收。

## 源码快照

Releases 附设备/common、完整内核、设备树、模块、Health、Settings 和 Soong 的准确修改后源码快照；对应 Git tree 和 SHA256 见 manifests/source-snapshots.json。快照采用 git archive，只含受版本管理的源码与明确列出的修改，没有编译机工作目录或个人文件。

快照已包含补丁，解压到对应目录后不要再重复应用。其他 AOSP/Lineage 项目及工具链由完整固定 manifest 获取。内核实际配置为 manifests/kernel.config；内核源码快照保留内核自身构建脚本、COPYING 及 LICENSES。
