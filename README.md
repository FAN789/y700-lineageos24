# Y700 2023 · LineageOS 24（非官方）

面向 Lenovo Legion Y700 2023 **TB320FC / asphalt** 的个人构建与对应源码。基于 LineageOS 24 / Android 17、lolipuru 的设备与内核适配，内核 5.10.260。

**当前公开版本：2026-10-14，实验性预发布。不是 LineageOS 官方发行版。仅一台 PRC 设备完成下述实测，不保证其他批次、区域或原厂版本可用。**

## 下载与源码

- [固件、恢复镜像及完整设备/内核源码快照](https://github.com/FAN789/y700-lineageos24/releases)
- [已解析的完整源码 manifest](manifests/resolved-manifest.xml) 固定所有项目提交；另有 [设备 manifest](manifests/y700.xml)、[源码树与快照哈希](manifests/source-snapshots.json)。
- [构建步骤](docs/BUILD.md)、[安装与 PRC 兼容性](docs/INSTALL.md)、[实测范围与已知限制](docs/TESTING.md)。
- [隐私检查与发布边界](docs/PRIVACY.md)、[上游与许可证](NOTICE.md)。
- [本地自动构建与 OTA 发布说明](docs/AUTOMATED-BUILDS.md)：每周构建候选包，实机验收后再推广；当前 OTA 列表为空。

## 有效改动

1. 构建端 Soong Go 内存控制；不改变设备安全设置。
2. Health 服务读取设备已有只读 SOH 节点，Settings 优先显示有效的原生健康百分比，不写电池校准、不伪造容量。
3. asphalt 内核启用 USER_NS、PID_NS、IPC_NS、POSIX_MQUEUE，供独立 Linux 用户空间/桌面应用沙箱使用；保留 Android 要求的 SYSVIPC=n。

原生 ELF、依赖、SELinux 和 VINTF 检查没有被跳过。已撤销的 Wi-Fi-only 提取试验不包含在构建步骤中。

## 实测摘要

2026-10-14 的标准 A/B 更新与普通重启通过。用户反馈 Wi-Fi、前后相机、声音、旋转、双击亮屏正常；后台检查 SELinux Enforcing，桌面应用原生命名空间沙箱通过。电池页面与电量计 SOH 一致；这不等同于实测电芯容量。

## 安全属性

当前镜像继承上游 **userdebug、公开 test keys、AVB flags 3** 和 ROW 构建指纹。签名/哈希校验通过不意味着生产级 Verified Boot 强制校验。不要在此系统上重新锁定 Bootloader。

OTA 是未经 Magisk 修改的原始构建产物，不内置 GApps、Ubuntu 根文件系统、Codex 登录、个人数据或设备备份。内核只是具备 Linux 沙箱所需功能，刷入 OTA 不会自动安装 Ubuntu。
