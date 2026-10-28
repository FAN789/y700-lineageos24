# 自动构建、专用签名与 OTA 发布

唯一编译环境为 NAS 上独立 android-builder Linux 容器；保留 8 CPU / 40 GiB 上限，构建 -j3、同步 -j4、Go 内存 20 GiB 和现有 source/out/cache。GitHub Actions 仅调度可信 main 的手动／定时构建；不执行不可信 PR 代码。每周五 19:17 UTC（北京时间周六 03:17）生成候选，不自动跨 Android 大版本。

固件签名私钥只在 NAS 宿主受限目录及隔离签名环境使用，不挂入 builder、不上传仓库。公开仓库只包含重建脚本、补丁、manifest 与公开验证策略，不含厂商原始私密输入或账号。原生 CRC、payload/整包签名、12 分区容量和哈希、AVB、VINTF、内核、保留脚本及 APK/APEX 身份检查必须通过；源码冲突、未知改动和检查失败即停止。现有历史目录内少量 target-files 是 USB／Recovery 比较校验基线，不应在清理候选时一并删除。

20261028 / 1793184607 使用专用发布签名，已完成一次真实标准 A/B 更新及双 USB-C Recovery 冷启动验收。完整记录见 docs/RELEASE-20261028.md 和 ota/acceptance 内与整包 SHA256 绑定的记录。该实机结果不代表未来每周候选已自动完成硬件验收。

Updater 地址为 https://raw.githubusercontent.com/FAN789/y700-lineageos24/main/ota/asphalt.json 。推广只接受与具体 OTA 哈希绑定的独立验收记录，下载后的 SHA、分区和签名验证不会因发布而跳过。编译成功不能自动把硬件和保留检查填成 true；每周调度不等于无条件自动发布。旧 test-key 系统不能直接通过此渠道完成保留数据签名迁移。

发布是原生未 root OTA，不内置 GApps 或个人环境。已安装 GApps/Magisk 的保留需适用脚本和实机验收。继承 userdebug、AVB flags3、解锁 BL，不是官方认证或锁定 Verified Boot；不得重锁 BL。OTA 列表变更不等于已安装设备能够强制降级，回退需核对签名、数据、快照、防降级及对应备份。
