# Quest 3 Unity Codex Skills

面向 Meta Quest 3、Unity XR/MR 项目的可移植 Agent Skills。它遵循开放的 Agent Skills 目录格式，可在 Codex 及兼容客户端中使用。

这是非官方社区项目，与 Meta Platforms、Unity Technologies 没有隶属、赞助或背书关系。

[English](README.md)

## 包含内容

| Skill | 用途 |
| --- | --- |
| `quest3-verify-first` | 在修改项目前，对 Quest、Unity、OpenXR、包版本、权限和设备能力进行实时主来源核验。 |
| `unity-xr-mr-ui-director` | 设计、实现和审查 Unity 空间 UI，覆盖物理尺寸、输入栈、MR 放置、可访问性、性能与 Quest 3 真机验收。 |

建议同时安装。UI skill 会把易变化的平台与包信息交给 `quest3-verify-first` 核验。

## 安全边界

仓库只包含指令、参考资料和一份只读 Python 审计脚本。它不携带 Unity 包、Meta SDK 二进制、`metavr`、遥测钩子、ADB 工具、3D 素材或 Unity Editor MCP。

Skill 本身不会扩大操作权限。修改 Unity 包、安装或启动 APK、设备截图与诊断，仍需当前用户请求授权，并且本机已经配置对应工具。

## 安装

克隆仓库：

```bash
git clone https://github.com/Wu030616/quest3-unity-codex-skills.git
cd quest3-unity-codex-skills
mkdir -p "$HOME/.agents/skills"
ln -s "$PWD/skills/quest3-verify-first" "$HOME/.agents/skills/quest3-verify-first"
ln -s "$PWD/skills/unity-xr-mr-ui-director" "$HOME/.agents/skills/unity-xr-mr-ui-director"
```

目标目录已经存在时先停止，检查旧版本，不要直接覆盖。其他 Agent Skills 客户端可能使用不同目录，请按对应客户端文档安装。

## 使用示例

```text
使用 $quest3-verify-first，先核验这个 Unity 项目的 Quest 3、OpenXR
和包版本要求，再提出修改方案。
```

```text
使用 $unity-xr-mr-ui-director，为 Quest 3 设计一个绑定到房间墙面的
MR 菜单，给出物理尺寸、输入方式和真机验收门槛。
```

## 只读审计

```bash
python3 skills/unity-xr-mr-ui-director/scripts/audit_unity_xr_ui.py \
  /Unity项目绝对路径
```

Unity Hub 使用自定义编辑器目录时：

```bash
python3 skills/unity-xr-mr-ui-director/scripts/audit_unity_xr_ui.py \
  /Unity项目绝对路径 \
  --unity-editors-path /Unity/Hub/Editor目录
```

也可以设置 `UNITY_HUB_EDITORS_PATH`；多个目录使用当前操作系统的路径分隔符。解析优先级为命令行参数、环境变量、平台默认目录。

脚本输出 JSON。确定问题写入 `warnings` 并影响退出码；无法单靠静态文件判断的内容写入 `observations`，不会让审计失败。脚本不打开 Unity，也不改项目。静态检查无法替代编译、交互测试和 Quest 3 头显内的可读性、舒适度判断。

## 本地验证

需要 Python 3.10 或更新版本：

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```

初始公开版本为 `0.1.0`。授权见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)，第三方边界见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
