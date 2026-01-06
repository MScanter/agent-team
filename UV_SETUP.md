# 使用 uv 管理依赖和虚拟环境

本项目已从传统的 `pip` 和 `requirements.txt` 迁移到 `uv` 进行依赖管理和虚拟环境管理。`uv` 是一个高性能的 Python 包管理工具，可以显著加快依赖解析和安装速度。

## 安装 uv

如果你还没有安装 `uv`，可以通过以下方式安装：

```bash
# 使用 pip
pip install uv

# 或使用 Homebrew (macOS)
brew install uv

# 或使用其他方式，请参考官方文档
```

## 项目设置

### 1. 创建虚拟环境

```bash
cd backend
uv venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
# 安装项目依赖
uv pip install -e .

# 或者，如果需要开发依赖
uv pip install -e ".[dev]"
```

### 3. 运行应用

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行后端应用
python -m app.main
```

## 常用命令

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装新依赖
uv pip install package_name

# 添加依赖到 pyproject.toml
uv add package_name  # 注意：这需要 uv 支持 PEP 621 的工具

# 更新所有依赖
uv pip sync requirements.txt  # 如果有 requirements.txt

# 运行测试
uv run pytest

# 运行应用
uv run python -m app.main
```

## 与传统 pip 的区别

- 使用 `pyproject.toml` 而不是 `requirements.txt` 管理依赖
- 虚拟环境创建和依赖安装速度更快
- 更好的依赖解析算法
- 与现代 Python 生态系统更好地集成

## 故障排除

如果遇到问题，请尝试：

1. 确保使用 Python 3.13 或更高版本
2. 清除虚拟环境并重新创建：
   ```bash
   rm -rf .venv
   uv venv
   source .venv/bin/activate
   uv pip install -e .
   ```
3. 检查 uv 版本是否为最新版