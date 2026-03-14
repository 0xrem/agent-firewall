# 1.1 版本实现清单

## 已完成 ✅

### 1. 核心层 (Runtime-Agnostic)
- [x] `events` - 标准化事件类型和负载语义
- [x] `policy` - 决策语义和规则执行
- [x] `approval` - 审查解决语义
- [x] `audit` - 审计条目和摘要模式
- [x] `enforcers` - 共享的 shell、file、HTTP 执行面
- [x] `runtime_context` - 跨嵌套事件的关联元数据传播

### 2. 适配器契约层
- [x] 适配器元数据模型 (`RuntimeAdapterSpec`)
- [x] 能力声明模型 (`AdapterCapability`)
- [x] 运行时上下文字段契约 (`REQUIRED_RUNTIME_CONTEXT_FIELDS`)
- [x] 共享一致性夹具和断言 (`conformance.py`)
- [x] 运行时转换辅助工具
- [x] 共享适配器组装辅助工具 (`assembly.py`)

### 3. 官方适配器
- [x] LangGraph 适配器 ([langgraph.py](file:///Users/rem/Github/agent-firewall/src/agentfirewall/langgraph.py))
- [x] LangGraph 防护工具
- [x] OpenAI Agents 实验性适配器 ([openai_agents.py](file:///Users/rem/Github/agent-firewall/src/agentfirewall/openai_agents.py))

### 4. 测试套件
- [x] 适配器组装测试 ([test_adapter_assembly.py](file:///Users/rem/Github/agent-firewall/tests/test_adapter_assembly.py))
- [x] 适配器一致性测试 ([test_adapter_conformance.py](file:///Users/rem/Github/agent-firewall/tests/test_adapter_conformance.py))
- [x] 评估契约测试 ([test_eval_contracts.py](file:///Users/rem/Github/agent-firewall/tests/test_eval_contracts.py))
- [x] LangGraph 评估案例 ([langgraph_cases.json](file:///Users/rem/Github/agent-firewall/src/agentfirewall/evals/cases/langgraph_cases.json))
- [x] 通用评估案例 ([generic_cases.json](file:///Users/rem/Github/agent-firewall/src/agentfirewall/evals/cases/generic_cases.json))

## 待完成 📋

### 1. 能力矩阵文档化
- [ ] 更新 [ADAPTER_CAPABILITY_MATRIX.md](file:///Users/rem/Github/agent-firewall/docs/strategy/ADAPTER_CAPABILITY_MATRIX.md) 的 LangGraph 完整能力行
- [ ] 添加 OpenAI Agents 实验性能力行
- [ ] 实现 `export_official_adapter_matrix()` 函数

### 2. 适配器注册表
- [ ] 完善 [registry.py](file:///Users/rem/Github/agent-firewall/src/agentfirewall/integrations/registry.py) 的官方适配器注册逻辑
- [ ] 实现 `get_official_adapter_spec()` 统一入口
- [ ] 添加适配器发现机制

### 3. OpenAI Agents 证据包
- [ ] 添加 OpenAI Agents 评估案例文件 (`openai_agents_cases.json`)
- [ ] 实现本地评估运行器（无需 API Key）
- [ ] 添加 7+ 个评估案例：
  - 安全提示 + 安全函数工具
  - 触发审查的提示
  - 安全工具调用
  - 未审批的审查工具调用
  - 已审批的审查工具调用
  - log-only 函数工具工作流
  - 嵌套副作用关联（shell/file/HTTP）

### 4. OpenAI Agents 辅助工具包
- [ ] `create_guarded_openai_agents_shell_tool()`
- [ ] `create_guarded_openai_agents_http_tool()`
- [ ] `create_guarded_openai_agents_file_reader_tool()`
- [ ] `create_guarded_openai_agents_file_writer_tool()`

### 5. 文档更新
- [ ] 更新 README.md 的 1.1 新功能说明
- [ ] 添加适配器开发指南
- [ ] 更新 [PRODUCT_STATUS.md](file:///Users/rem/Github/agent-firewall/docs/strategy/PRODUCT_STATUS.md) 反映 1.1 进展

## 下一步建议

### 优先级 1：完善适配器注册表
让适配器发现和使用更加规范化，为 1.2 的第二个官方适配器做准备。

### 优先级 2：OpenAI Agents 证据包
完成评估案例和辅助工具，证明核心可复用到第二个适配器。

### 优先级 3：能力矩阵自动化
从代码自动生成能力矩阵，避免文档与实现不同步。
