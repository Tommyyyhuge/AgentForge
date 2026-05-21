# Anaconda 虚拟环境配置指南

> **重要**: 所有 Python 开发必须在 Anaconda 虚拟环境中进行，**严禁使用 base 环境**  
> **环境名称**: `agentforge`  
> **Python 版本**: 3.11

---

## 1. 创建虚拟环境

### 1.1 打开 Anaconda Prompt（Windows）或 Terminal（Mac/Linux）

```bash
# 检查当前环境（注意括号中的环境名）
conda info --envs

# 应该看到类似输出：
# base                  *  /Users/yourname/anaconda3
# agentforge               /Users/yourname/anaconda3/envs/agentforge
```

### 1.2 创建新环境

```bash
# 创建环境（指定 Python 3.11）
conda create -n agentforge python=3.11 -y

# 等待安装完成...
# 输出：
# done
# #
# # To activate this environment, use
# #     $ conda activate agentforge
# # To deactivate an active environment, use
# #     $ conda deactivate
```

### 1.3 激活环境（!!! 每次开发前必须执行)

```bash
# 激活环境
conda activate agentforge

# 验证（注意命令行前面的环境名）
(agentforge) C:\Users\yourname> 

# 验证 Python 路径
which python
# 应该输出类似：
# /Users/yourname/anaconda3/envs/agentforge/bin/python

# 验证 Python 版本
python --version
# 应该输出：Python 3.11.x
```

### 1.4 设置默认环境（可选，推荐）

```bash
# 让 VS Code 默认使用这个环境
# 在 VS Code 中按 Ctrl+Shift+P（Cmd+Shift+P on Mac）
# 输入 "Python: Select Interpreter"
# 选择：~/anaconda3/envs/agentforge/bin/python
```

---

## 2. 安装依赖

### 2.1 升级基础工具

```bash
# 确保在 agentforge 环境中
conda activate agentforge

# 升级 pip
pip install --upgrade pip setuptools wheel
```

### 2.2 创建 requirements.txt

在 `backend/` 目录下创建 `requirements.txt`：

```
# ============================================
# AgentForge 依赖清单
# ============================================

# Web 框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# 数据验证
pydantic==2.5.2
pydantic-settings==2.1.0
email-validator==2.1.0

# 数据库
sqlalchemy==2.0.23
aiosqlite==0.19.0
asyncpg==0.29.0
alembic==1.12.1

# 向量数据库
chromadb==0.4.18

# LLM 客户端
openai==1.3.6
httpx==0.25.2

# 工具库
duckduckgo-search==3.9.6
beautifulsoup4==4.12.2
PyPDF2==3.0.1

# 安全
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
cryptography==41.0.7

# 缓存/消息队列
redis==5.0.1

# 监控
psutil==5.9.6

# 配置管理
python-dotenv==1.0.0
PyYAML==6.0.1

# 日志
structlog==23.2.0

# ============================================
# 测试依赖
# ============================================
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
factory-boy==3.3.0
faker==20.1.0

# ============================================
# 代码质量工具
# ============================================
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1

# 类型提示
types-PyYAML==6.0.12.12
```

### 2.3 安装生产依赖

```bash
# 在 backend/ 目录下
cd backend

# 安装依赖（可能需要 5-10 分钟）
pip install -r requirements.txt

# 如果安装慢，使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2.4 安装开发依赖（可选）

```bash
# 安装开发工具
pip install jupyter ipython

# 或者创建单独的 requirements-dev.txt
pip install -r requirements-dev.txt
```

### 2.5 验证安装

```bash
# 检查关键包是否安装成功
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import pydantic; print(f'Pydantic: {pydantic.__version__}')"
python -c "import sqlalchemy; print(f'SQLAlchemy: {sqlalchemy.__version__}')"
python -c "import chromadb; print('ChromaDB: OK')"
python -c "import openai; print(f'OpenAI: {openai.__version__}')"

# 检查测试工具
pytest --version
black --version
mypy --version
```

---

## 3. 环境管理命令速查

### 日常开发流程

```bash
# 1. 激活环境（每次打开终端都要执行）
conda activate agentforge

# 2. 确认环境正确
which python
# 应该包含：.../envs/agentforge/...

# 3. 开始开发
python main.py
# 或
uvicorn main:app --reload
```

### 环境管理

```bash
# 查看所有环境
conda env list

# 激活环境
conda activate agentforge

# 退出当前环境
conda deactivate

# 删除环境（如果出问题需要重建）
conda env remove -n agentforge

# 克隆环境（备份）
conda create --name agentforge_backup --clone agentforge

# 导出环境配置
conda env export > environment.yml

# 从配置文件创建环境
conda env create -f environment.yml
```

### 包管理

```bash
# 查看已安装的包
pip list

# 查看特定包
pip show fastapi

# 卸载包
pip uninstall package_name

# 升级包
pip install --upgrade package_name

# 清理缓存
pip cache purge
```

---

## 4. IDE 配置

### VS Code 配置

#### 4.1 选择 Python 解释器

1. 按 `Ctrl+Shift+P`（Mac: `Cmd+Shift+P`）
2. 输入 `Python: Select Interpreter`
3. 选择 `~/anaconda3/envs/agentforge/bin/python`

#### 4.2 配置 settings.json

```json
{
    "python.defaultInterpreterPath": "~/anaconda3/envs/agentforge/bin/python",
    "python.analysis.typeCheckingMode": "basic",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

#### 4.3 推荐插件

- Python (Microsoft)
- Pylance
- Black Formatter
- isort
- autoDocstring
- Error Lens

---

## 5. 常见问题

### Q1: 提示 "conda 不是内部或外部命令"

**原因**: Anaconda 没有添加到系统 PATH  
**解决**:
```bash
# Windows: 使用 Anaconda Prompt（开始菜单搜索）
# Mac/Linux: 添加以下到 ~/.bashrc 或 ~/.zshrc
export PATH="/Users/yourname/anaconda3/bin:$PATH"
```

### Q2: 安装依赖时提示权限错误

**原因**: 可能使用了系统 Python  
**解决**:
```bash
# 确认在虚拟环境中
conda activate agentforge
which python  # 确认路径包含 envs/agentforge

# 如果还在 base 环境，不要加 sudo
pip install -r requirements.txt  # 正确
sudo pip install ...              # 错误！
```

### Q3: 包安装失败（编译错误）

**原因**: 缺少系统依赖  
**解决**:
```bash
# macOS
xcode-select --install
brew install openssl

# Windows
# 安装 Visual C++ Build Tools
# 下载地址：https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Linux (Ubuntu/Debian)
sudo apt-get install python3-dev build-essential libssl-dev
```

### Q4: 如何确认没有使用 base 环境？

```bash
# 方法 1: 看命令行提示符
(base) C:\Users\>        ← 这是 base 环境，不要在这里开发！
(agentforge) C:\Users\>   ← 这是 agentforge 环境，正确！

# 方法 2: 检查 Python 路径
import sys
print(sys.executable)
# 正确：.../anaconda3/envs/agentforge/bin/python
# 错误：.../anaconda3/bin/python

# 方法 3: 检查 conda 环境
conda info --envs
# 带 * 的是当前环境，确保是 agentforge
```

### Q5: 依赖冲突怎么办？

```bash
# 方法 1: 先卸载冲突包，再重新安装
pip uninstall package_name
pip install package_name==specific_version

# 方法 2: 重建环境
conda deactivate
conda env remove -n agentforge
conda create -n agentforge python=3.11
conda activate agentforge
pip install -r requirements.txt
```

---

## 6. 快速检查脚本

创建 `check_env.py`：

```python
"""环境检查脚本"""
import sys
import importlib

def check_environment():
    print("=" * 50)
    print("AgentForge 环境检查")
    print("=" * 50)
    
    # 检查 Python 路径
    python_path = sys.executable
    if "agentforge" in python_path:
        print(f"✅ 虚拟环境正确: {python_path}")
    else:
        print(f"❌ 虚拟环境错误: {python_path}")
        print("   请运行: conda activate agentforge")
        return False
    
    # 检查 Python 版本
    version = sys.version_info
    if version.major == 3 and version.minor == 11:
        print(f"✅ Python 版本正确: {version.major}.{version.minor}")
    else:
        print(f"⚠️  Python 版本: {version.major}.{version.minor} (推荐 3.11)")
    
    # 检查关键包
    packages = [
        ("fastapi", "0.104"),
        ("pydantic", "2.5"),
        ("sqlalchemy", "2.0"),
        ("chromadb", "0.4"),
        ("openai", "1.3"),
        ("pytest", "7.4"),
    ]
    
    print("\n包检查:")
    for package, min_version in packages:
        try:
            module = importlib.import_module(package)
            version = getattr(module, "__version__", "unknown")
            if version.startswith(min_version.split(".")[0]):
                print(f"✅ {package}: {version}")
            else:
                print(f"⚠️  {package}: {version} (推荐 {min_version}+)")
        except ImportError:
            print(f"❌ {package}: 未安装")
    
    print("\n" + "=" * 50)
    print("检查完成")
    print("=" * 50)

if __name__ == "__main__":
    check_environment()
```

运行检查：
```bash
conda activate agentforge
python check_env.py
```

---

## 7. 开发工作流

### 每日开始工作

```bash
# 1. 打开终端
# 2. 激活环境
conda activate agentforge

# 3. 进入项目目录
cd ~/Projects/AgentForge/backend

# 4. 检查环境
python check_env.py

# 5. 开始开发
uvicorn main:app --reload
```

### 代码提交前

```bash
# 1. 格式化代码
black agent_forge/
isort agent_forge/

# 2. 类型检查
mypy agent_forge/

# 3. 运行测试
pytest tests/ --cov=agent_forge --cov-report=html

# 4. 提交代码
git add .
git commit -m "feat: add xxx feature"
```

---

**Anaconda 配置完成！**

现在你可以开始按 `WEEK1_DETAILED_TASKS.md` 进行编码实现了。
