# AgentFirewall 项目总结

## 项目最终目标 🎯

**构建一个统一的运行时防火墙核心，能够在不改变策略语义、审批行为或审计模式的前提下，保护多个不同运行时（LangGraph、OpenAI Agents、MCP 等）的 AI 代理系统。**

### 核心愿景

- **一个核心，多个适配器**：共享的策略引擎、审批流程、审计模式
- **标准化执行面**：prompt、tool_call、command、file_access、http_request
- **适配器无关性**：新增运行时适配器时，无需修改核心策略逻辑
- **可重复的评估证据**：每个官方适配器都必须通过一致性测试和评估套件

---

## 当前状态 (1.0.0) ✅

### 已发布的核心能力

| 组件 | 状态 | 说明 |
|------|------|------|
| **核心防火墙** | ✅ 稳定 | `agentfirewall` 包，运行时无关的类型和构造 |
| **LangGraph 适配器** | ✅ 官方支持 | `agentfirewall.langgraph`，完整的 shell/HTTP/file 工具 |
| **审批处理器** | ✅ 稳定 | Terminal、Static、Custom Callback |
| **审计 Sink** | ✅ 稳定 | Console、JsonLines、Multi、InMemory |
| **内置规则** | ✅ 7 条规则 | 37 个注入模式、28 个命令模式、27 个文件路径模式 |
| **评估套件** | ✅ 19 个案例 | LangGraph 本地评估，无需 API Key |

### 已验证的能力

```bash
# 6 个攻击场景演示
python examples/attack_scenarios.py

# LangGraph 快速开始（无需 API Key）
python examples/langgraph_quickstart.py

# 10 个多步骤工作流追踪
python examples/langgraph_trial_run.py

# 19 个评估案例
python -m agentfirewall.evals.langgraph

# 84 个单元测试和集成测试
python -m pytest tests/ -v
```

**评估结果**: `total=19, passed=19, failed=0`

---

#### ✅ 已完成的核心组件
   - [`conformance.py`](file:///Users/rem/Github/agent-firewall/src/agentfirewall/integrations/conformance.py) - 一致性验证器
   - [`runtime_context.py`](file:///Users/rem/Github/agent-firewall/src/agentfirewall/runtime_context.py) - 运行时上下文契约

2. **适配器注册表**
   - [`registry.py`](file:///Users/rem/Github/agent-firewall/src/agentfirewall/integrations/registry.py) - 官方适配器注册和发现
   - [`assembly.py`](file:///Users/rem/Github/agent-firewall/src/agentfirewall/integrations/assembly.py) - 防火墙组装辅助
   - ✅ LangGraph 一致性验证通过
   - ✅ OpenAI Agents 实验性适配器测试通过（7/7）

1. **OpenAI Agents 证据包** (优先级：高)
   - [ ] 添加 `openai_agents_cases.json` 评估案例文件
   - [ ] 实现本地评估运行器（无需 API Key）
   - [ ] 添加 7+ 个评估案例
   - [ ] `create_guarded_openai_agents_http_tool()`
   - [ ] `create_guarded_openai_agents_file_reader_tool()`
3. **能力矩阵文档** (优先级：中)
   - [ ] 更新 [`ADAPTER_CAPABILITY_MATRIX.md`](file:///Users/rem/Github/agent-firewall/docs/strategy/ADAPTER_CAPABILITY_MATRIX.md)
   - [ ] 实现 `export_official_adapter_matrix()` 完整功能

4. **文档更新** (优先级：中)
---

#### 目标
++
- **第二个官方运行时适配器**：OpenAI Agents SDK
- **证明核心可复用性**：同样的策略包和审计模型在两个适配器上工作
- **轻量级集成**：保持"drop-in"体验

#### 成功信号

#### 执行计划


### 1.3 版本：MCP 预览支持 🔮

- MCP client/server 预览支持
- 为 MCP 资源读取增加共享的 `resource_access` 事件表面
- 标准化 MCP 工具和资源访问到共享审计追踪
- 仅在真正需要时引入新的共享事件类型，而不是协议特定分叉
- 让 MCP 继续保持 preview runtime support，而不是直接宣称官方支持
- `log-only` 作为新集成的默认验证路径
┌─────────────────────────────────────────────────┐
│           用户提示 / 工具输出 / 外部输入          │
                   ▼
┌─────────────────────────────────────────────────┐
│              Tool-Using Runtime                 │
│         (LangGraph / OpenAI Agents / ...)       │
└──────────────────┬──────────────────────────────┘
│              AgentFirewall Core                 │
│  ┌──────────────────────────────────────────┐   │
│  │  - OpenAI Agents Adapter (1.2)            │   │
│  │  - MCP Preview Path (1.3)                │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  核心策略引擎 (Runtime-Agnostic)          │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  - Guarded File (27 个敏感路径模式)        │   │
│  └──────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
      副作用（仅在允许时执行）
```

---

## 关键设计原则

### 1. 标准化执行面，而非框架特定 API

每个新适配器都应该将运行时行为转换为共享事件类型：
- `prompt` - 提示检查
- `tool_call` - 工具调用审查
- `command` - Shell 命令执行
- `file_access` - 文件读写
- `http_request` - 出站 HTTP 请求

### 2. 适配器契约优先

- 定义清晰的能力矩阵
- 一致性测试必须通过
- 评估证据必须可重复
- 运行时上下文必须完整

### 3. 渐进式采用路径

- `log-only` 模式用于验证
- 审查模式用于开发
- 强制模式用于生产

### 4. 本地可重复性

- 评估套件无需外部服务
- 演示脚本无需 API Key
- 所有证据可本地重现

---

## 当前工作流建议

### 对于开发者

```bash
# 1. 查看当前实现状态
cat docs/strategy/IMPLEMENTATION_1_1.md

# 2. 运行所有测试
python -m pytest tests/ -v

# 3. 运行 LangGraph 评估
python -m agentfirewall.evals.langgraph

# 4. 查看适配器能力矩阵
python -c "from agentfirewall.integrations import export_official_adapter_matrix; print(export_official_adapter_matrix())"
```

### 对于 1.1 版本完成

**优先级排序**:

1. **OpenAI Agents 评估案例包** - 证明核心可复用到第二个适配器
2. **OpenAI Agents 辅助工具** - 提供与 LangGraph 对等的工具包
3. **能力矩阵自动化** - 从代码生成文档
4. **文档更新** - 反映 1.1 新功能

---

## 项目结构

```
agent-firewall/
├── src/agentfirewall/
│   ├── __init__.py              # 核心导出
│   ├── firewall.py              # 防火墙核心
│   ├── policy.py                # 策略引擎
│   ├── approval.py              # 审批处理
│   ├── audit.py                 # 审计追踪
│   ├── events.py                # 事件模型
│   ├── enforcers/               # 执行面强制器
│   │   ├── shell.py
│   │   ├── files.py
│   │   ├── http.py
│   │   └── tools.py
│   ├── integrations/            # 适配器层
│   │   ├── contracts.py         # 适配器契约
│   │   ├── conformance.py       # 一致性测试
│   │   ├── registry.py          # 适配器注册表
│   │   ├── assembly.py          # 组装辅助
│   │   ├── langgraph.py         # LangGraph 适配器
│   │   └── openai_agents.py     # OpenAI Agents 适配器 (实验性)
│   └── evals/                   # 评估套件
│       └── cases/
│           ├── langgraph_cases.json
│           └── generic_cases.json
├── tests/                       # 测试套件
├── examples/                    # 演示脚本
└── docs/strategy/               # 战略文档
    ├── MULTI_RUNTIME_ROADMAP.md
    ├── RELEASE_1_1_PLAN.md
    ├── OPENAI_AGENTS_ADAPTER_PLAN.md
    └── ADAPTER_CAPABILITY_MATRIX.md
```

---

## 总结

**当前状态**: 1.0.0 已稳定发布，1.1 核心组件**大部分已完成**（24/24 测试通过）

**下一步重点**: 
1. 完成 OpenAI Agents 证据包和辅助工具
2. 发布 1.1 版本（适配器契约强化）
3. 启动 1.2 版本（第二个官方适配器）

**最终目标**: 构建一个统一的、可复用的运行时防火墙核心，支持多个 AI 代理运行时，保持策略语义一致性和审计可追溯性。
