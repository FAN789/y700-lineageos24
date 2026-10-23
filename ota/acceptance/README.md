# 稳定 OTA 验收记录

仅在真实验收完成后新增 `<OTA整包SHA256>.json`。没有记录时推广任务应失败，不能用模板里的布尔值代替验证。

记录必须含整包 `sha256` 与 `checks`，以下检查全部为 true 才允许推广：`private_release_signatures`、`payload_partitions_capacity`、`avb`、`selinux_vintf`、`hardware`、`key_migration`、`root_persistence`。同时提交不含个人数据的检查方法、签名公钥指纹、分区/容量报告、受测版本和实机结论，供维护者审核。

构建成功、CRC/SHA256 正确，或者该设备以前运行过另一个版本，都不能证明本次已通过这些检查。缺失项目保持未验收，不填写 true。私钥、个人日志、账号和设备私有分区不进入仓库。

验收记录进入 main 后，仓库所有者才能手动运行 **Promote accepted Y700 OTA**，指定 Releases 中的实际 tag、完整文件名和 SHA256。任务重新下载并验证资产，随后更新 `ota/asphalt.json` 并保留 feed 历史。它不对平板发出安装、重分区或重锁命令。
