# /archon-init

检查环境并初始化 daemon-archon

## 用法

```
/archon-init
```

## 说明

交互式初始化向导，包括：
1. 检测 conda 环境，让用户选择使用已有环境、新建环境或使用系统 Python
2. 检查运行所需的依赖是否满足
3. 提供手动安装或自动安装选项（使用国内镜像源）

## 初始化流程

### 第一步：环境选择

检测是否存在 conda，如果存在则提供选项：
- 使用当前激活的 conda 环境
- 新建 `daemon-archon` 专用环境
- 使用系统 Python 环境

### 第二步：依赖检查

检查以下依赖：
- Claude CLI
- Python >= 3.8
- fastapi, uvicorn, apscheduler, psutil, anthropic, croniter

### 第三步：安装方式

如果有缺失依赖，提供选项：
- 自动安装（使用清华源）
- 手动安装（显示安装命令）

## 实现

执行以下脚本进行初始化：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_wizard.py
```

## 输出示例

```
daemon-archon 初始化向导
========================

[1/3] 环境检测
-------------
检测到 conda 环境

请选择 Python 环境：
  1. 使用当前环境: base (Python 3.10.12)
  2. 新建 daemon-archon 专用环境
  3. 使用系统 Python

请输入选项 [1/2/3]: 2

正在创建 conda 环境 daemon-archon...
conda create -n daemon-archon python=3.10 -y
环境创建成功！

[2/3] 依赖检查
-------------
检查项                          状态   详情
------------------------------------------------------------
Claude CLI                     ✓     claude 2.1.0
Python 版本                    ✓     Python 3.10.12
Python 包: fastapi             ✗     未安装
Python 包: uvicorn             ✗     未安装
Python 包: apscheduler         ✗     未安装
Python 包: psutil              ✗     未安装
Python 包: anthropic           ✗     未安装
Python 包: croniter            ✗     未安装
工作目录权限                    ✓     ~/.claude/daemon-archon

[3/3] 安装依赖
-------------
检测到 6 个缺失的依赖包

请选择安装方式：
  1. 自动安装（使用清华镜像源）
  2. 手动安装（显示安装命令）

请输入选项 [1/2]: 1

正在安装依赖（使用清华源）...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple fastapi uvicorn apscheduler psutil anthropic croniter

安装完成！

✓ 初始化完成，可以运行 /archon-start 启动服务
```

## 国内镜像源

自动安装使用清华大学 PyPI 镜像：
```
https://pypi.tuna.tsinghua.edu.cn/simple
```

## 示例

```bash
# 运行初始化向导
/archon-init

# 初始化完成后启动服务
/archon-start
```
