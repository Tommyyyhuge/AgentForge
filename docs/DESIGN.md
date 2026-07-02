# AgentForge 设计规范

## 1. 设计定位

AgentForge 是面向个人开发者的深色技术控制台。界面应当冷静、可扫描、可检查，服务于任务执行、Agent 状态观察、Provider 配置和问题诊断，而不是营销展示。

设计系统需要支持：

- Task 执行监控。
- Agent 状态检查。
- Timeline 型详情页。
- Provider 与 API Key 配置。
- 高信息密度但可读的开发者工作流。

## 2. 设计原则

- 清晰优先：每个视觉元素都要帮助用户理解状态、层级或操作。
- 操作密度：Dashboard 和表格应展示有用信息，不做大面积宣传式留白。
- 稳定布局：状态变化、Step 流式追加、加载状态不得让核心布局剧烈跳动。
- 系统状态可见：loading、empty、success、warning、error、degraded 都要明确。
- 术语一致：UI 文案使用 Task、Agent、Planner、Execution、Step、Memory、Provider、API Key。
- 默认保护隐私：secret 掩码展示，metrics 不展示敏感 prompt 内容。

## 3. 视觉方向

主风格：

- 深色技术控制台。
- 克制的边框和面板。
- 紧凑间距。
- 明确的语义状态色。
- 品牌色只用于主操作、焦点和少量强调。

避免：

- 应用内部出现营销 hero。
- 装饰性渐变光斑、大块空卡片、宣传式大标题。
- 只由蓝色和紫色组成的单调界面。
- 卡片嵌套卡片。
- 除空状态和错误状态外，用长段文字解释产品怎么用。

## 4. 信息架构

一级导航保持：

- Dashboard。
- Tasks。
- Agents。
- Chat。
- Settings。

导航职责：

- Dashboard 负责总览和跳转。
- Tasks 负责 Task 列表、创建、详情、结果和 Step timeline。
- Agents 负责 Agent 状态和消息监控。
- Chat 是辅助交互入口。
- Settings 负责 Provider、API Key、主题和本地偏好。

新增一级导航前必须同步更新 PRD、TECH、SPEC。

## 5. 布局系统

### 5.1 应用外壳

桌面端：

- 左侧常驻 Sidebar。
- Header 展示当前页面标题、全局状态、用户操作和快捷控制。
- 主内容区域在阅读型页面使用最大宽度限制。
- 数据密集页面可以使用完整可用宽度。

移动端：

- Sidebar 折叠为菜单或抽屉。
- 主内容优先展示。
- 表格转为堆叠列表。
- Timeline 仍保持纵向可读。

### 5.2 间距

推荐间距：

- 4px：图标和文字之间的微小间距。
- 8px：紧凑内部间距。
- 12px：表单字段组和工具栏间距。
- 16px：列表项和局部区块间距。
- 24px：页面区块间距。
- 32px：大型内容组间距。

组件尺寸：

- Icon button 使用稳定方形尺寸，通常 32px 或 36px。
- 主按钮高度通常为 36px 到 40px。
- 卡片和面板圆角最大 8px。
- 表格行保持紧凑但可读。

## 6. 颜色系统

现有 `forge` 色板保留为品牌强调色，但界面不得只依赖蓝紫色。

### 6.1 基础 token

| Token | 用途 | 示例 |
| --- | --- | --- |
| `surface.bg` | 应用背景 | `#0a0a0a` |
| `surface.panel` | 主面板 | `#141414` |
| `surface.raised` | 浮层和弹出面板 | `#181a20` |
| `surface.border` | 边框和分割线 | `#262626` |
| `text.primary` | 主文字 | `#f5f5f5` |
| `text.secondary` | 次级文字 | `#a3a3a3` |
| `text.muted` | 弱化元信息 | `#737373` |
| `brand.primary` | 主操作 | `#4a72ff` |
| `brand.strong` | hover/active | `#1a3fff` |

### 6.2 语义状态色

| 状态 | 颜色角色 | 用途 |
| --- | --- | --- |
| Pending | yellow | Task 已接受但未运行 |
| Planning | blue | Planner 正在拆解 |
| Executing | violet | Agent 正在工作 |
| Completed | emerald | 成功完成 |
| Failed | red | 需要注意的失败 |
| Cancelled | neutral | 用户或系统停止 |
| Warning | amber | 可恢复风险 |
| Info | cyan | 信息事件 |

规则：

- 状态色用于 badge、timeline icon 和紧凑高亮。
- 大面积背景保持中性。
- 深色模式下文字对比度必须可读。

## 7. 字体与文字层级

默认：

- UI 使用系统 sans-serif。
- ID、模型名、API 片段、代码、Provider base URL、日志使用 monospace。

规则：

- 不使用基于 viewport 的字体缩放。
- 字距保持正常。
- 控制台内部不使用 hero 级展示字体。
- 页面标题短而功能明确。

推荐层级：

- 页面标题：24-28px。
- 区块标题：16-18px。
- 表格和正文：13-14px。
- 元信息：12px。

## 8. 组件规范

### 8.1 按钮

类型：

- Primary：页面主操作，如 Create Task、Save Provider、Test Connection。
- Secondary：常见非破坏操作。
- Ghost：工具栏和导航操作。
- Danger：Delete Key、Cancel Task 等破坏性操作。

规则：

- 常见工具操作优先使用图标。
- 容易歧义的操作使用文字标签。
- loading 按钮宽度保持稳定。
- 禁用原因不明显时需要说明。

### 8.2 Badge

用于：

- Task status。
- Agent status。
- Provider capability。
- Provider health。
- API Key permission。

规则：

- Badge 紧凑且语义明确。
- 标签必须直接映射领域值。
- 不用 badge 做无意义装饰。

### 8.3 卡片和面板

适合使用卡片：

- 移动端重复列表项。
- 指标摘要项。
- Modal 内容。
- 独立 Settings 分组。

避免：

- 卡片嵌套卡片。
- 把每个页面区块都做成浮动卡片。
- 内容很少的大装饰卡片。

### 8.4 表单

表单标准：

- Label 始终可见。
- Helper text 只在能避免误操作时使用。
- 必填字段明确。
- 校验错误靠近字段显示。
- secret 输入仅在安全时支持显示/隐藏。
- API Key 保存后只显示掩码。

Provider 表单必须包含：

- Provider type。
- Display name。
- Base URL。
- API key。
- Default model。
- Capability toggles 或检测到的 capabilities。
- Timeout、streaming、tool calling 等开关。
- Test Connection 操作。

### 8.5 表格

用于：

- Task 列表。
- API Key 列表。
- Provider/model 列表。
- Agent 状态列表。

规则：

- 识别对象的列放第一列。
- 状态和操作列位置稳定。
- 行支持键盘 focus。
- 移动端转为堆叠列表卡片。

### 8.6 Modal

用于：

- 创建 Task。
- 添加 Provider/API Key。
- 确认破坏性操作。
- 展示详细错误或测试结果。

规则：

- 标题说明对象和动作。
- 桌面端主操作在右下角。
- 破坏性操作需要明确确认。
- 非破坏性 modal 支持 Esc 和 backdrop 关闭。

### 8.7 Toast

用于：

- 保存成功。
- Provider 测试结果。
- 非阻塞错误。
- 后台操作完成。

规则：

- 重要 Task 或 Provider 错误不能只靠 toast 记录。
- 错误 toast 应尽量指向受影响区域。

## 9. 页面规范

### 9.1 Dashboard

目的：

- 汇总 AgentForge 状态并提供入口。

必备内容：

- Task 状态计数。
- 最近 Task 列表。
- Agent 状态摘要。
- 没有可用 Provider 时的健康提醒。
- 可用时展示基本 metrics。

状态：

- 空状态：还没有 Task，主操作为 Create Task。
- 降级状态：后端可用但 Provider 缺失或不健康。
- 错误状态：metrics 不可用但导航仍可用。

当前实现：

- Dashboard 顶部展示 Task 状态计数。
- Dashboard 展示 Provider 状态面板；没有 active Provider 或没有 active healthy Provider 时显示 warning 并提供 Provider Settings 入口。
- Provider 状态面板显示 active Provider、默认模型和已有 health 状态，不在 Dashboard 自动发起供应商连接测试。
- Metrics 加载失败时 Dashboard 在 metrics 区域显示局部错误状态，保留 Create Task、Provider Settings 和页面导航。
- Dashboard 在 Agent 列表前展示 idle/busy/error 状态摘要，并保留最近 Task 列表和 metrics 图表。

### 9.2 Tasks

目的：

- 管理 Task 生命周期。

必备内容：

- Create Task 操作。
- 可实现时按状态和文本筛选。
- Task 列表展示标题、状态、优先级、Agent、创建/更新时间。
- 空状态引导创建第一个 Task。

Task 行内容：

- 标题和短描述。
- 状态 badge。
- 优先级 badge。
- 更新时间。
- 打开详情的操作。

### 9.3 Task Detail

目的：

- 检查 Task Execution 和结果。

必备内容：

- Task 标题、状态、优先级、创建/更新/完成时间。
- 结果或错误。
- Step timeline。
- 每个 Step 的 Agent 归属。
- 可取消时显示 Cancel 操作。
- 实时流连接状态。

Timeline 规则：

- Step 按顺序排序。
- Step 类型使用语义图标和颜色。
- 长内容可读且可复制。
- Error Step 明显但不过度刺眼。

当前实现：

- Task Detail 从 task store 接收已排序 Step；持久化 Step 和 SSE step update 使用相同 timeline order。
- Timeline 中展示的 Step 编号来自稳定 `Step.order`，不是当前数组位置。
- Task Detail 在 Step timeline 标题旁展示 `SSE connecting/connected/disconnected` 实时流状态。
- Error Step 的结果或失败原因在 Step 内以局部 `alert` 区域展示，使用克制红色状态样式并保留 Agent 归属。
- Step type badge 展示 PRD 枚举值 `thought/action/observation/final/error`，颜色按语义类型区分。

### 9.4 Agents

目的：

- 检查内置 Agent 状态和通信。

必备内容：

- Agent role、name、status。
- 当前 Task。
- model/provider。
- Agent state stream 连接状态。
- 后端支持时显示消息面板。

规则：

- Planner 不作为五个内置可执行 Agent 展示。
- Agent status 和 Task status 视觉上分组区分。

当前实现：

- Agent role 列表只展示 `researcher/coder/writer/reviewer/executor` 五个可执行 Agent。
- Planner 通过 Task planning 状态和 Execution timeline 保持可见，不作为 Agent row、Agent message receiver 或 Agent worker 展示。

### 9.5 Chat

目的：

- 提供辅助对话入口。

必备内容：

- 会话列表或当前会话。
- 消息输入框。
- 可用时展示相关 Task/Step 上下文。
- 流式响应状态。

规则：

- Chat 不是 Task 的权威记录。
- 触发 Task 的消息需要链接到对应 Task。

### 9.6 Settings

目的：

- 管理本地 AgentForge 配置。

必备区块：

- Profile/auth 状态。
- Provider 配置。
- API Keys。
- 主题偏好。
- 可用时展示运行时/配置诊断。

Provider 设置要求：

- 列出已配置 Provider。
- 展示健康状态和最近测试时间。
- 从 preset 添加官方 Provider。
- 通过自定义 Base URL 添加 Relay Provider。
- 编辑默认模型和 capability flags。
- 测试连接。
- 删除或停用 Provider。

当前实现：

- Settings 已包含 Provider Configuration 分组。
- 支持通过 Provider type 选择官方 implemented preset 或 OpenAI-compatible Relay Provider。
- 官方 preset 会填入 Display name、Base URL、Default model 与 capability flags；Relay Provider 支持自定义 Base URL。
- Provider 表单包含 API Key、Default model、Streaming、Tool calling 和 capability badge 展示。
- Provider 列表展示 Provider type、Default model、health 状态。
- 已配置 Provider 加载 model listing 后展示 model select；listing degraded 或没有模型时展示 manual model entry。
- Provider test failure 和 model listing degraded 状态在分组内展示，不只依赖 toast。
- API Key 提交后不在 Provider config 或 store state 中显示明文。

API Key 要求：

- 添加 key。
- 掩码展示 key。
- 展示 provider 和 permission。
- 展示 created time、last used、usage count。
- 删除 key 时需要确认。

## 10. 交互规则

加载：

- 页面级加载使用 skeleton 或稳定 loading panel。
- 按钮级加载保持宽度稳定。
- 流式 Step 加载使用 timeline append 状态。

空状态：

- 说明缺少什么对象，并提供一个主操作。

错误：

- 展示哪个对象失败、已知原因、用户下一步能做什么。
- 后端/API 错误使用归一化消息。
- Provider 错误安全展示 provider、model 和错误类别。

实时：

- 需要流式能力的页面展示 SSE connected/disconnected 状态。
- 重连不得导致 Step 重复。

破坏性操作：

- Delete API Key 和 Cancel Task 需要确认。
- 破坏性按钮使用 danger 样式。

## 11. 可访问性

- 所有交互控件可通过键盘访问。
- focus 状态可见。
- 纯图标按钮有可访问标签。
- 颜色不是唯一状态提示。
- 表单字段有 label。
- 错误信息尽量关联到字段。
- 深色主题文字对比度尽量满足 WCAG AA。

## 12. 响应式要求

桌面：

- 使用 sidebar 布局。
- 表格展示完整列。
- Task detail 可使用双列布局。

平板：

- Sidebar 可折叠。
- 密集面板在宽度受限时堆叠。

移动：

- 单列布局。
- 表格转为卡片。
- 主操作保持可访问。
- Timeline 长内容换行，代码块可横向滚动。

## 13. 文案风格

语气：

- 直接、技术化、冷静。
- 操作使用动词：Create Task、Test Provider、Cancel Task、Delete Key。
- 避免泛泛营销词。

标签：

- 使用 Task、Agent、Planner、Execution、Step、Memory、Provider、API Key。
- 当前范围避免 workspace、administrator、knowledge base、run history。

错误文案：

- 说明失败对象。
- 说明已知原因。
- 提供下一步操作。

示例：

`Provider test failed: DeepSeek returned 401. Check the API key or provider base URL.`
