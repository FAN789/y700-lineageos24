# 本地自动编译与 OTA 发布

本仓库的 GitHub Actions 只负责调度，实际同步和编译由专用 Linux x86_64 self-hosted Runner 执行。公开仓库不保存厂商软件输入、账号、密码、SSH 私钥、固件签名私钥、Ubuntu 或个人应用数据。

## 自动构建

- Actions → **Y700 local build** → Run workflow：`baseline` 使用已发布的完整固定 manifest 重建；`tracking` 跟踪 manifest 内 LineageOS `lineage-24.0` 分支，社区设备/内核提交和 AOSP 固定标签仍保持锁定。
- 每周五 19:17 UTC（北京时间周六 03:17）运行 tracking；不自动跨越 Android 大版本。
- WSL 专用环境建议 20 CPU、40 GB RAM、24 GB swap；同步 -j8，编译 -j12。源码和 ccache 在 Linux ext4 中。
- 四项补丁必须能够干净应用；tracking 要求新提交是原补丁基线的后代。冲突、未知修改、厂商输入缺失或原生校验失败都会停止，不跳过 ELF、VINTF 或 SELinux 检查。
- CI 额外应用单独记录的 Updater 地址补丁（ci/patches.json），因此候选包包含 OTA 入口，不能称为原发布包的按位复现。现有四项功能补丁保持不变。
- GitHub concurrency 与本机 flock 双重串行；中断保留源码和日志。缓存不自动删除。
- 仅 main 上的手动和定时工作流可使用此 Runner。**不得添加 pull_request / pull_request_target 或执行不可信分支的任务。** 仓库写入权限意味着能够在该 Runner 上执行代码，必须限制协作者权限。
- Windows 托管 WSL 的 Runner 在专用用户登录后启动；Windows 注销、关机或网络断开时任务无法运行。不要把“GitHub 已排队”当成正在编译。

## 产物和 OTA

构建产物保留在编译机的 candidates 目录。`ci/ota-feed.py inspect` 检查整包 CRC、SHA256、payload/metadata 哈希、A/B 机型和真实 ZIP 流式偏移。它**不替代**分区重建、容量、OTA/payload 签名、AVB、SELinux/VINTF 和硬件验收。

`ci/validate-native.py` 随后使用同次构建的原生 Android host tools：校验整包及 payload 签名，从 payload 重建全部 12 个分区并匹配 manifest/target-files 的镜像哈希，检查分区及动态分区组容量，再验证 AVB 主公钥、两个子链的公钥/rollback location、各镜像描述符与 VINTF。签名信任固定为本实验渠道既有 AOSP test keys，不自动接受任意自签公钥。容量上限来自本项目已存档的单台 PRC 设备记录，仍需要实机重新确认；不代表所有同名机型布局相同。

镜像必须取自 OTA payload，并与原生 OTA 输入 `target_files/IMAGES` 对照。产品输出根目录中的早期 boot.img 中间产物可能不同，不能混作本包的维护镜像。候选包保留 offline-validation/report.json 和原生工具日志；旧失败诊断保存在 attempt-history。verify-existing 操作不重编译，但需要保留与该候选匹配的 target-files；后续构建覆盖后不能拿不同版本 target-files 证明旧包。

原生签名通过只证明与预期测试公钥一致。当前整包仍使用 AOSP 旧测试证书（签名工具采用 SHA-1 整包摘要），payload 哈希为 SHA-256；AVB 根为 SHA256_RSA4096、子链 RSA2048，继承 flags3。没有因此变为生产私钥签名或启用强制 Verified Boot。

OTA 地址预留为 `https://raw.githubusercontent.com/FAN789/y700-lineageos24/main/ota/asphalt.json`，格式采用 LineageOS 24 Updater 的数组结构。初始 feed 是空数组，平板不会因此收到尚未验收的候选包。现有固件没有配置此地址；首次接入需要在确认安装与签名迁移方式后更新固件，不能仅靠修改 GitHub 就宣称已开通 OTA。

`ci/ota-feed.py feed` 只接受与实际 OTA 哈希绑定的验收记录。所有 gate 都必须为 true：私有正式签名、payload 分区/容量、AVB、SELinux/VINTF、硬件、签名迁移、root 持续性。由维护者完成独立验收，不能由“编译成功”自动填 true。通过后才创建 Releases 资产并原子更新 feed，保留旧版本及其哈希。

当前已发布固件为 userdebug、公开 test-keys，AVB flags 3；不能称为官方签名、安全锁定启动或无条件支持私有签名覆盖安装。正式签名私钥应在独立离线/受限签名环境生成并备份，不能交给公共仓库工作流。首次签名迁移、数据保留、GApps、Magisk 及 Ubuntu 启动依赖需要单独验证，**不自动刷机、不重锁 BL、不重分区**。

## 接手与回退

先确认 Runner 在线，再检查本机 pipeline.state 与对应 logs。失败保留第一条真实错误；修复补丁应提交审查后再重跑，不能启动第二个并发编译。GitHub feed 回退只影响可见下载列表，不会自动降级已安装系统。实际系统回退仍需满足 Android 防降级、签名和数据兼容要求，并保留对应完整固件与原始备份。

参考：[LineageOS 24 Updater](https://github.com/LineageOS/android_packages_apps_Updater/blob/lineage-24.0/README.md)、[GitHub self-hosted Runner 安全要求](https://docs.github.com/en/actions/reference/security/secure-use)。
