## Code Discovery — codegraph CLI

项目已初始化 codegraph (`codegraph status` 查看状态)。
`D:/Programs/nodejs/node_global/codegraph`

### 常用命令

| 命令 | 用途 |
|------|------|
| `codegraph query <symbol>` | 搜索符号（函数/类/变量/import） |
| `codegraph callers <symbol>` | 谁调用了这个符号 |
| `codegraph callees <symbol>` | 这个符号调用了谁 |
| `codegraph impact <symbol>` | 修改该符号的影响范围 |
| `codegraph files` | 项目文件树 |
| `codegraph sync` | 增量同步变更 |
| `codegraph status` | 索引状态 |
| `codegraph context <task>` | 按任务生成上下文 markdown |

### 规则

- **codegraph FIRST** — 搜索符号、调用链、影响分析优先用 codegraph CLI
- 文本搜索（注释、字符串、配置）用 Grep/Read
- 索引滞后时 sync 一下
