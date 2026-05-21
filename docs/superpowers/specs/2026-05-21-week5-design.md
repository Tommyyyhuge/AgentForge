# Week 5 设计文档：API Key 加密 + 测试体系 + 性能优化

> **版本**: 1.0
> **日期**: 2026-05-21
> **基于**: Week 4 完成的 UI 打磨 + 流程图 + 主题系统
> **目标**: API Key 加密存储、前端测试体系搭建、性能优化
> **核心原则**: 安全优先、测试驱动、增量优化

---

## 目录

1. [概述](#1-概述)
2. [API Key 加密存储](#2-api-key-加密存储)
3. [前端测试体系](#3-前端测试体系)
4. [性能优化](#4-性能优化)
5. [实施计划](#5-实施计划)
6. [验收标准](#6-验收标准)

---

## 1. 概述

### 1.1 Week 5 目标

- **API Key 加密存储**：Fernet (PBKDF2 派生) 加密，数据库存储，前后端集成
- **前端测试体系**：Vitest + React Testing Library，覆盖组件/页面/Hook/Store
- **性能优化**：路由懒加载、React.memo、防抖节流、LLM 缓存

### 1.2 与已完成的衔接

```
Week 4 完成:
├── UI 组件库          → Week 5 测试覆盖
├── 登录/注册          → Week 5 API Key 与用户绑定
├── Settings 页面      → Week 5 API Key 管理卡片
├── 代码分割           → Week 5 路由懒加载
└── Dashboard          → Week 5 React.memo 优化

Week 5 新增:
├── utils/encryption.py        # PBKDF2 → Fernet 加密
├── database/models.py (扩展)  # APIKeyORM
├── api/routes/keys.py         # Key CRUD
├── core/llm_client.py (改造)  # 集成 APIKeyManager
├── tests/                     # 前端测试套件
├── App.tsx (优化)             # 路由懒加载
└── stores/* (优化)            # 防抖节流
```

---

## 2. API Key 加密存储

### 2.1 加密方案

**技术选型**: `cryptography` 库的 Fernet + PBKDF2 密钥派生

**为什么不用直接 Fernet(key)**：
- Fernet 要求 key 必须是 32 字节 url-safe base64
- 环境变量 `ENCRYPTION_KEY` 可能很短或不符合格式
- PBKDF2 可安全地将任意长度字符串派生为 32 字节密钥

**实现** (`utils/encryption.py`):

```python
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

class APIKeyEncryption:
    """API Key 加密管理器"""
    
    def __init__(self, master_key: str, salt: str):
        key = self._derive_key(master_key, salt)
        self._fernet = Fernet(key)
    
    def _derive_key(self, master_key: str, salt: str) -> bytes:
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=480_000,  # OWASP 2024 推荐
        )
        return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    
    def encrypt(self, plaintext: str) -> str:
        """加密明文 → base64 密文"""
        return self._fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """解密 base64 密文 → 明文"""
        return self._fernet.decrypt(ciphertext.encode()).decode()
    
    @staticmethod
    def mask_key(key: str) -> str:
        """生成掩码格式：sk-****-abcd"""
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}****{key[-4:]}"
```

**密钥来源**:
- `ENCRYPTION_KEY`: 环境变量，生产环境使用 `openssl rand -hex 32` 生成
- `ENCRYPTION_SALT`: 环境变量，固定字符串或随机值

### 2.2 数据库模型

**扩展 `database/models.py`**:

```python
class APIKeyORM(Base):
    """API Key 加密存储"""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False)     # kimi, deepseek
    encrypted_key = Column(String, nullable=False) # AES-128-CBC 密文
    masked_key = Column(String, nullable=False)    # sk-****-abcd
    permission = Column(String, default="write")   # read / write / admin
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("UserORM", back_populates="api_keys")
```

**权限分级**:
| 权限 | 查看 masked_key | 用于 LLM 调用 | 创建/删除 |
|------|:---:|:---:|:---:|
| `read` | ✅ | ❌ | ❌ |
| `write` | ✅ | ✅ | ❌ |
| `admin` | ✅ | ✅ | ✅ |

### 2.3 API 设计

**文件**: `api/routes/keys.py`

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/keys` | POST | 添加 API Key（传入明文，加密后存储） |
| `/api/v1/keys` | GET | 列出当前用户的 API Key（只返回 masked_key） |
| `/api/v1/keys/{id}` | GET | 获取单个 Key 详情（含权限、使用统计） |
| `/api/v1/keys/{id}` | DELETE | 删除 API Key（软删除，设置 is_active=False） |
| `/api/v1/keys/{id}/usage` | GET | 获取 Key 使用统计 |

**POST 请求体**:
```json
{
  "provider": "kimi",
  "api_key": "sk-xxxxxxxxxxxx",
  "permission": "write"
}
```

**POST 响应**:
```json
{
  "id": "uuid",
  "provider": "kimi",
  "masked_key": "sk-x****xxxx",
  "permission": "write",
  "created_at": "2026-05-21T10:00:00Z"
}
```

**GET 列表响应**:
```json
[
  {
    "id": "uuid-1",
    "provider": "kimi",
    "masked_key": "sk-x****xxxx",
    "permission": "write",
    "usagage_count": 42
  }
]
```

### 2.4 LLM 客户端集成

**改造 `core/llm_client.py`**:

当前 LLM 客户端直接从 `settings.KIMI_API_KEY` 读取明文 Key。改造后：

```python
class APIKeyManager:
    """API Key 管理器 - 从加密存储获取并解密 Key"""
    
    def __init__(self, encryption: APIKeyEncryption, db_session):
        self._encryption = encryption
        self._db = db_session
        self._cache: dict[str, str] = {}  # provider → decrypted_key（短期缓存）
    
    async def get_key(self, provider: str) -> str | None:
        # 1. 检查缓存
        if provider in self._cache:
            return self._cache[provider]
        
        # 2. 查询数据库
        key_orm = await self._db.execute(
            select(APIKeyORM).where(
                APIKeyORM.provider == provider,
                APIKeyORM.is_active == True,
                APIKeyORM.permission == "write",
            )
        )
        key_record = key_orm.scalar_one_or_none()
        if not key_record:
            return None
        
        # 3. 解密
        decrypted = self._encryption.decrypt(key_record.encrypted_key)
        
        # 4. 缓存（短期，用完丢弃）
        self._cache[provider] = decrypted
        
        # 5. 更新使用统计
        key_record.usage_count += 1
        key_record.last_used_at = datetime.utcnow()
        await self._db.commit()
        
        return decrypted
    
    def clear_cache(self):
        """清空解密缓存（安全清理）"""
        self._cache.clear()


class LLMRouter:
    def __init__(self, api_key_manager: APIKeyManager):
        self.api_key_manager = api_key_manager
    
    async def route(self, messages, provider="kimi", model=None):
        api_key = await self.api_key_manager.get_key(provider)
        if not api_key:
            raise ValueError(f"No active API key for provider: {provider}")
        # ... 使用 api_key 发起请求
```

**安全原则**:
- 解密后的 Key 只缓存在内存中，不落盘
- 请求结束后可调用 `clear_cache()` 清理
- 应用关闭时缓存自动销毁

### 2.5 前端 Key 管理

**改造 Settings 页面**:

将现有 localStorage 存储改为通过 API 管理。新增"API 密钥管理"卡片：

```tsx
function APIKeySection() {
  const [keys, setKeys] = useState<APIKey[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ provider: 'kimi', api_key: '', permission: 'write' })
  
  // 加载已有 Keys
  useEffect(() => {
    apiClient.get('/keys').then(res => setKeys(res.data))
  }, [])
  
  // 添加 Key
  async function handleAdd() {
    await apiClient.post('/keys', form)
    // 刷新列表
    const res = await apiClient.get('/keys')
    setKeys(res.data)
    setShowAdd(false)
  }
  
  // 删除 Key
  async function handleDelete(id: string) {
    await apiClient.delete(`/keys/${id}`)
    setKeys(prev => prev.filter(k => k.id !== id))
  }
  
  return (
    <section className="forge-card !bg-surface-dark space-y-4">
      <div className="flex items-center gap-2">
        <Key className="h-5 w-5 text-forge-400" />
        <h3 className="text-base font-semibold text-white">API 密钥管理</h3>
      </div>
      
      {keys.map(key => (
        <div key={key.id} className="flex items-center justify-between rounded-forge border border-surface-border px-4 py-3">
          <div>
            <p className="text-sm text-white">{key.provider}</p>
            <p className="text-xs text-neutral-400 font-mono">{key.masked_key}</p>
          </div>
          <Badge>{key.permission}</Badge>
          <Button variant="ghost" size="sm" onClick={() => handleDelete(key.id)}>删除</Button>
        </div>
      ))}
      
      <Button variant="secondary" onClick={() => setShowAdd(true)} leftIcon={<Plus />}>
        添加 API Key
      </Button>
      
      {showAdd && (
        <Modal isOpen={showAdd} onClose={() => setShowAdd(false)} title="添加 API Key">
          {/* 表单：provider 选择、key 输入、permission 设置 */}
        </Modal>
      )}
    </section>
  )
}
```

---

## 3. 前端测试体系

### 3.1 技术选型

| 工具 | 用途 |
|------|------|
| Vitest | 测试框架（与 Vite 原生集成） |
| @testing-library/react | 组件渲染与查询 |
| @testing-library/jest-dom | DOM 断言扩展 |
| @testing-library/user-event | 用户交互模拟 |
| jsdom | DOM 环境模拟 |
| @vitest/coverage-v8 | 代码覆盖率 |

### 3.2 测试目录结构

```
frontend/
├── tests/
│   ├── setup.ts                        # 全局 setup（Mock、样式导入）
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Modal.test.tsx
│   │   │   ├── Toast.test.tsx
│   │   │   ├── Button.test.tsx
│   │   │   ├── Loading.test.tsx
│   │   │   └── Card.test.tsx
│   │   ├── flow/
│   │   │   └── AgentFlow.test.tsx
│   │   └── auth/
│   │       └── ProtectedRoute.test.tsx
│   ├── pages/
│   │   ├── Login.test.tsx
│   │   ├── Register.test.tsx
│   │   └── Settings.test.tsx
│   ├── hooks/
│   │   ├── useTheme.test.ts
│   │   └── useToastManager.test.ts
│   ├── stores/
│   │   ├── authStore.test.ts
│   │   ├── taskStore.test.ts
│   │   └── agentStore.test.ts
│   └── utils/
│       └── toast.test.ts
├── src/
│   └── ...（业务代码）
└── vitest.config.ts
```

### 3.3 Vitest 配置

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 60,
        statements: 70,
      },
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.d.ts',
        'vite.config.ts',
      ],
    },
  },
})
```

### 3.4 全局 Setup

```typescript
// tests/setup.ts
import '@testing-library/jest-dom'

// Mock framer-motion 以避免动画相关测试问题
vi.mock('framer-motion', () => ({
  motion: {
    div: 'div',
    button: 'button',
  },
  AnimatePresence: ({ children }: { children: ReactNode }) => children,
}))

// Mock reactflow 避免 DOM 相关测试问题
vi.mock('reactflow', () => ({
  ReactFlow: () => null,
  Handle: () => null,
  Position: { Top: 'top', Bottom: 'bottom' },
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  useNodesState: () => [[], () => {}],
  useEdgesState: () => [[], () => {}],
}))
```

### 3.5 关键测试场景

#### Modal 组件测试 (6 个)

```typescript
describe('Modal', () => {
  it('打开时渲染标题和内容')
  it('关闭时不渲染')
  it('点击遮罩层触发 onClose')
  it('ESC 键触发 onClose')
  it('打开时锁定背景滚动')
  it('关闭时恢复背景滚动')
})
```

#### Toast 组件测试 (4 个)

```typescript
describe('Toast', () => {
  it('显示 Toast 消息')
  it('自动关闭（默认 3 秒）')
  it('点击关闭按钮移除')
  it('同时显示多个 Toast 堆叠')
})
```

#### Login 页面测试 (5 个)

```typescript
describe('Login', () => {
  it('空用户名显示校验错误')
  it('密码太短显示校验错误')
  it('登录成功调用 login 函数')
  it('登录失败显示错误信息')
  it('已登录用户重定向到首页')
})
```

#### authStore 测试 (4 个)

```typescript
describe('AuthStore', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
  })
  
  it('登录成功更新状态')
  it('注册成功更新状态')
  it('登出清空状态')
  it('认证失败设置 error')
})
```

### 3.6 覆盖率目标

| 层级 | 目标 | 预计测试数 |
|------|------|-----------|
| 组件（UI） | 70% | ~15 |
| 组件（Flow/Charts） | 50% | ~3 |
| 页面 | 60% | ~12 |
| Hook | 80% | ~8 |
| Store | 70% | ~10 |
| 工具函数 | 80% | ~5 |
| **总计** | **70%** | **~50** |

---

## 4. 性能优化

### 4.1 路由懒加载

**改造 App.tsx**（当前全部静态 import）：

```tsx
import { lazy, Suspense } from 'react'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Tasks = lazy(() => import('./pages/Tasks'))
const TaskDetail = lazy(() => import('./pages/TaskDetail'))
const AgentMonitor = lazy(() => import('./pages/AgentMonitor'))
const Chat = lazy(() => import('./pages/Chat'))
const Settings = lazy(() => import('./pages/Settings'))
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))

// 使用
<Suspense fallback={<PageLoading />}>
  <Routes>...</Routes>
</Suspense>
```

**效果**：首屏只加载 Dashboard 代码，其他页面按需加载，首屏 JS 减少 ~60%。

### 4.2 React.memo 缓存

**目标组件**（纯展示、props 不变时不需重渲染）：

```tsx
// Badge.tsx, Card.tsx - 已存在，添加 memo
export default memo(Badge)
export default memo(Card)

// AgentNode.tsx - React Flow 频繁重渲染时优化
export default memo(AgentNode)

// Loading.tsx - 纯展示组件
export default memo(Loading)
```

**Dashboard 计算缓存**：

```tsx
// Dashboard.tsx
const statValues = useMemo(() => ({
  total: tasks.length,
  running: tasks.filter(t => t.status === 'running').length,
  completed: tasks.filter(t => t.status === 'completed').length,
}), [tasks])
```

### 4.3 防抖/节流

**SSE 实时更新节流**（避免高频重渲染）：

```typescript
// stores/agentStore.ts - subscribeToAgents 改造
function throttle(fn: Function, delay: number) {
  let lastTime = 0
  return (...args: any[]) => {
    const now = Date.now()
    if (now - lastTime >= delay) {
      fn(...args)
      lastTime = now
    }
  }
}

subscribeToAgents: () => {
  const throttledUpdate = throttle((data) => {
    get().updateAgents(data)
  }, 500) // 每 500ms 最多更新一次
  
  // ... SSE 连接使用 throttledUpdate
}
```

**搜索输入防抖**（避免频繁 API 调用）：

```typescript
// utils/debounce.ts
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout>
  return (...args) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}
```

### 4.4 LLM 调用缓存（后端）

```python
# core/llm_client.py - 添加缓存层
from functools import lru_cache

class LLMRouter:
    def __init__(self):
        self._response_cache: dict[str, dict] = {}
        self._cache_ttl = 300  # 5 分钟
    
    async def route(self, messages, provider="kimi", model=None):
        # 生成缓存键
        cache_key = self._make_cache_key(messages, provider, model)
        
        # 检查缓存
        if cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            if (datetime.utcnow() - cached["timestamp"]).seconds < self._cache_ttl:
                return cached["response"]
        
        # 发起请求
        response = await self._call_llm(messages, provider, model)
        
        # 存入缓存
        self._response_cache[cache_key] = {
            "response": response,
            "timestamp": datetime.utcnow(),
        }
        
        return response
    
    def _make_cache_key(self, messages, provider, model):
        return hashlib.md5(
            f"{provider}:{model}:{json.dumps(messages)}".encode()
        ).hexdigest()
```

---

## 5. 实施计划

### Day 1: API Key 加密（后端）

**上午**:
- `utils/encryption.py` — PBKDF2 + Fernet 加密类
- `database/models.py` — 扩展 APIKeyORM 模型

**下午**:
- `api/routes/keys.py` — CRUD API（POST/GET/DELETE/usage）
- `api/routes/__init__.py` + `main.py` — 注册路由

**验证**:
- 加密/解密循环正确
- API 端点可访问
- JWT 认证保护生效

### Day 2: API Key 集成（前端 + LLM 客户端）

**上午**:
- `core/llm_client.py` — 改造集成 APIKeyManager
- Settings 页面 — API Key 管理卡片

**下午**:
- Modal 表单 — 添加 Key
- 列表 + 删除功能
- 后端测试补完

**验证**:
- 前端可添加/查看/删除 Key
- LLM 调用可解密并正确使用 Key
- Key 掩码格式正确

### Day 3: 前端测试体系搭建

**上午**:
- 安装依赖 + vitest.config.ts + setup.ts
- 组件测试：Modal + Button + Loading

**下午**:
- 组件测试：Card + Toast
- 工具函数测试：toast.ts
- 设置覆盖率命令

**验证**:
- `npm test` 可执行
- 覆盖率报告生成

### Day 4: 测试覆盖扩展

**上午**:
- Hook 测试：useTheme + useToastManager
- Store 测试：authStore

**下午**:
- Store 测试：taskStore + agentStore
- 页面测试：Login + Register
- 路由测试：ProtectedRoute

**验证**:
- 测试数量 > 40
- 覆盖率 > 60%

### Day 5: 性能优化

**上午**:
- App.tsx 路由懒加载
- React.memo 缓存（Badge/Card/AgentNode）

**下午**:
- SSE 节流
- LLM 调用缓存
- 构建验证

**验证**:
- 首屏 chunk < 250KB
- 页面切换流畅

### Day 6: 联调 + 补测试 + 打磨

**上午**:
- API Key 全流程测试（前端 → 后端 → LLM 调用）
- 测试覆盖率补充到 70%

**下午**:
- ESLint + 构建验证
- 性能最终检查
- 运行全部测试

---

## 6. 验收标准

### 6.1 API Key 加密

- [ ] PBKDF2 密钥派生正确（任意长度 ENCRYPTION_KEY 均可工作）
- [ ] 加密/解密循环正确（encrypt(plaintext) → decrypt(ciphertext) = plaintext）
- [ ] API Key 只以加密形式存储数据库
- [ ] 前端只显示 masked_key 格式（sk-****-abcd）
- [ ] LLM 客户端可解密并正确使用 Key
- [ ] 权限 control 生效（read 权限不允许 LLM 调用）

### 6.2 前端测试

- [ ] `npm test` 可执行，所有测试通过
- [ ] 测试数量 > 40
- [ ] 覆盖率 > 70%（lines）
- [ ] 组件测试覆盖 Modal/Loading/Toast/Button/Card
- [ ] 页面测试覆盖 Login/Register
- [ ] Hook 测试覆盖 useTheme
- [ ] Store 测试覆盖 authStore/taskStore

### 6.3 性能优化

- [ ] 路由懒加载生效（首屏 JS < 250KB）
- [ ] React.memo 减少不必要的重渲染
- [ ] SSE 更新节流（500ms）
- [ ] 搜索框防抖（300ms）
- [ ] LLM 调用缓存正确（TTL 5min）

### 6.4 全站验证

- [ ] 前端构建成功
- [ ] ESLint 零错误
- [ ] 后端测试全部通过（387+）
- [ ] 前端测试全部通过（40+）

---

## 附录 A: 依赖清单

### 新增前端依赖

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitest/coverage-v8
```

### 新增 Python 依赖

```
# cryptography 已在 requirements.txt 中（Week 3）
cryptography==41.0.7  # ✅ 已安装
```

---

## 附录 B: 文件清单

### 新增文件

```
backend/agent_forge/
├── utils/
│   └── encryption.py              # Day 1
├── api/routes/
│   └── keys.py                    # Day 1
└── core/
    └── api_key_manager.py         # Day 2

frontend/
├── tests/
│   ├── setup.ts                   # Day 3
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Modal.test.tsx     # Day 3
│   │   │   ├── Toast.test.tsx     # Day 3
│   │   │   ├── Button.test.tsx    # Day 3
│   │   │   ├── Loading.test.tsx   # Day 3
│   │   │   └── Card.test.tsx      # Day 3
│   │   ├── flow/
│   │   │   └── AgentFlow.test.tsx # Day 4
│   │   └── auth/
│   │       └── ProtectedRoute.test.tsx # Day 4
│   ├── pages/
│   │   ├── Login.test.tsx         # Day 4
│   │   └── Register.test.tsx      # Day 4
│   ├── hooks/
│   │   ├── useTheme.test.ts       # Day 4
│   │   └── useToastManager.test.ts # Day 4
│   ├── stores/
│   │   ├── authStore.test.ts      # Day 4
│   │   └── taskStore.test.ts      # Day 4
│   └── utils/
│       └── toast.test.ts          # Day 3
├── vitest.config.ts               # Day 3
└── src/utils/
    └── debounce.ts                # Day 5
```

### 修改文件

```
backend/agent_forge/
├── database/
│   └── models.py                  # Day 1: 添加 APIKeyORM
├── api/routes/
│   └── __init__.py                # Day 1: 注册 keys_router
├── core/
│   └── llm_client.py              # Day 2: 集成 APIKeyManager
└── main.py                        # Day 1: 注册 keys 路由

frontend/
├── src/
│   ├── App.tsx                    # Day 5: 路由懒加载
│   ├── pages/
│   │   ├── Dashboard.tsx          # Day 5: useMemo 优化
│   │   └── Settings.tsx           # Day 2: API Key 管理
│   ├── components/
│   │   ├── ui/Badge.tsx           # Day 5: React.memo
│   │   ├── ui/Card.tsx            # Day 5: React.memo
│   │   ├── ui/Loading.tsx         # Day 5: React.memo
│   │   └── flow/AgentNode.tsx     # Day 5: React.memo
│   └── stores/
│       └── agentStore.ts          # Day 5: SSE 节流
└── package.json                   # Day 3: 添加测试脚本
```
