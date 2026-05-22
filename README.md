# RL Config Analysis Platform

强化学习配置文件分析工作台，用于导入、查看、对比和搜索 IsaacLab 训练配置文件（`env.yaml`、`agent.yaml`）。

## 项目结构

```
config-analyzer/
├── backend/                          # Flask 后端
│   ├── app.py                        # 入口，端口 5000
│   ├── config.py                     # 路径和数据库配置
│   ├── utils.py                      # 工具函数（类型推断、关键词提取）
│   ├── models/
│   │   └── database.py               # SQLite 数据库：建表 + CRUD
│   ├── parsers/
│   │   ├── yaml_cleaner.py           # 预处理 !!python/tuple 等特殊标签
│   │   ├── env_parser.py             # env.yaml 逐段解析
│   │   └── agent_parser.py           # agent.yaml 解析
│   ├── routes/
│   │   ├── runs.py                   # 运行管理、导入、评价编辑
│   │   ├── config.py                 # 按段查询配置
│   │   ├── compare.py                # 运行对比
│   │   └── search.py                 # 参数/评价搜索、统计
│   └── services/
│       ├── comparison.py             # 对比算法（奖励/delta/事件差异）
│       └── summarizer.py             # 统计汇总
├── frontend/                         # Vue 3 + Vite 前端
│   ├── index.html                    # 入口 HTML
│   ├── package.json                  # 依赖（vue、vite、@vitejs/plugin-vue）
│   ├── vite.config.js                # Vite 配置（开发代理 :5000）
│   └── src/
│       ├── main.js                   # Vue 应用入口
│       ├── App.vue                   # 根组件 + 标签页导航
│       ├── api.js                    # API 请求封装
│       ├── views/
│       │   ├── Dashboard.vue         # 仪表盘：运行列表、导入、批量导入
│       │   ├── RunDetail.vue         # 运行详情：Agent/奖励/事件/评价
│       │   ├── Compare.vue           # 对比分析：奖励权重/Agent参数/delta
│       │   └── SearchView.vue        # 搜索：参数值、评价内容
│       ├── components/
│       │   └── ImportDialog.vue      # 文件上传导入弹窗
│       └── styles/
│           └── main.css              # 自定义样式（基于 Pico.css）
├── requirements.txt                  # Python 依赖
├── config_analyzer.db                # SQLite 数据库（自动生成）
└── README.md                         # 本文件
```

## 环境要求

- **Python** 3.8+
- **Node.js** 16+（仅前端开发模式需要，生产模式直接使用编译产物）

## 快速开始

### 1. 安装后端依赖

```bash
cd config-analyzer
pip install -r requirements.txt
```

依赖：`flask`、`flask-cors`、`pyyaml`

### 2. 安装前端依赖（仅开发模式）

```bash
cd frontend
npm install
```

### 3. 启动

**方式一：仅后端（前端已编译）**

```bash
python backend/app.py
```
打开浏览器访问 **http://localhost:5000**

**方式二：开发模式（前后端分别启动）**

```bash
# 终端 1：启动后端
python backend/app.py

# 终端 2：启动前端开发服务器
cd frontend
npm run dev
```
打开浏览器访问 **http://localhost:3000**（Vite 自动代理 API 到 5000 端口）

**方式三：前端重新编译**

```bash
cd frontend
npx vite build
# 产物输出到 frontend/dist/，Flask 自动服务
```

## 功能说明

### 仪表盘

- 查看所有已导入的训练运行记录
- 支持按机器人类型（SF/PF/WF）和任务类型（Walk/Flat/Stand）筛选
- 表格排序、多选/对比
- **导入配置**：上传 env.yaml + agent.yaml + 评价.txt
- **批量导入**：从目录路径批量扫描并导入，支持三种目录结构：
  1. **直接结构**：`目录/params/env.yaml`（目录本身就是 run 目录）
  2. **平铺结构**：`目录/2026-05-19.../params/env.yaml`（子目录是 run 目录）
  3. **嵌套结构**：`目录/实验名/运行名/params/env.yaml`

### 运行详情

左侧导航可快速跳转到各配置段：

| 段落 | 内容 |
|------|------|
| 概览 | 运行名称、实验、机器人/任务类型、导入时间 |
| Agent 配置 | 算法类型、学习率、网络结构（Actor/Critic/Encoder 维度） |
| 奖励配置 | 正向奖励（绿色）和负向惩罚（红色），含权重和函数名 |
| 事件配置 | 域随机化事件，按启动时/重置时/间隔触发分组 |
| 指令配置 | 步态命令（频率/偏移/持续/抬脚高度）和速度命令范围 |
| 评价记录 | 查看和**在线编辑**评价内容，自动提取问题标签 |
| 原始参数 | 所有扁平化参数的键值对列表 |

### 对比分析

- 选择 2–4 条运行记录进行对比
- **奖励对比**：逐项展示权重差异，相同/不同状态标注
- **Agent 参数对比**：超参数一列一列对比
- **Delta 分析**（2 条时）：列出新增/修改/移除的奖励项和事件

### 搜索

- 按参数路径或值搜索（如 `pen_joint_torque`、`keep_balance`）
- 按评价内容搜索（如 `原地踏步`、`倾斜`）
- 结果按参数路径分组展示，点击直接跳转运行详情

## API 路由一览

### 运行管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/runs` | 列出所有运行（支持 `?robot_type=`、`?experiment=` 筛选） |
| GET | `/api/runs/<id>` | 获取运行完整详情 |
| POST | `/api/runs/import` | 文件上传导入（multipart form） |
| POST | `/api/runs/import-directory` | 批量目录导入 |
| PUT | `/api/runs/<id>/evaluation` | 更新评价记录 |
| DELETE | `/api/runs/<id>` | 删除运行 |

### 配置查询
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/runs/<id>/config/rewards` | 奖励配置 |
| GET | `/api/runs/<id>/config/events` | 事件配置 |
| GET | `/api/runs/<id>/config/commands` | 指令配置 |
| GET | `/api/runs/<id>/config/agent` | Agent 配置 |
| GET | `/api/runs/<id>/config/sim` | 仿真参数 |
| GET | `/api/runs/<id>/config/terminations` | 终止条件 |

### 对比 & 搜索
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/compare/rewards?ids=1,2` | 奖励对比 |
| GET | `/api/compare/agent?ids=1,2` | Agent 参数对比 |
| GET | `/api/compare/delta/<a>/<b>` | 两运行差异分析 |
| GET | `/api/search?q=关键词` | 参数搜索 |
| GET | `/api/search/eval?q=关键词` | 评价搜索 |
| GET | `/api/stats/overview` | 总览统计 |
| GET | `/api/stats/reward-distribution` | 奖励分布统计 |

## 数据库说明

SQLite 数据库文件 `config_analyzer.db` 首次运行时自动创建，包含 6 张表：

| 表名 | 说明 |
|------|------|
| `runs` | 训练运行记录（名称、实验、机器人类型等） |
| `config_params` | 扁平化参数键值对（支持通用搜索） |
| `reward_terms` | 归一化奖励项（权重、类别、函数名） |
| `events` | 域随机化事件（模式、函数名） |
| `agent_config` | Agent/算法配置（PPO 超参数、网络结构） |
| `evaluations` | 评价记录（内容 + 自动提取的问题标签） |

## YAML 标签处理

IsaacLab 的 YAML 配置文件使用 Python 专属标签（`!!python/tuple`、`!!python/object/apply:builtins.slice`、YAML 锚点 `&id001` / `*id001`），标准 `yaml.safe_load()` 无法解析。

平台内置 **`yaml_cleaner.py`** 预处理器，在解析前自动处理：

| 原始内容 | 处理方式 |
|---------|---------|
| `!!python/tuple [1.0, 2.0]` | 转为 `[1.0, 2.0]`（标准 YAML 列表） |
| `key: !!python/tuple`（多行块） | 保留 `key:`，后续列表项保持原样 |
| `!!python/object/apply:builtins.slice` | 替换为 `null` |
| `&id001`（锚点定义） | 移除 |
| `*id001`（锚点引用） | 替换为 `null` |

`env_parser.py` 和 `agent_parser.py` 均通过 `safe_load_yaml()` 统一调用预处理。

## 技术栈

- **后端**：Flask + PyYAML + SQLite
- **前端**：Vue 3 + Vite + Pico.css
- **无需重型框架**，一个 Python 进程 + 静态文件即可运行
