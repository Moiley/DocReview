# 企业文档智能审校系统 - 项目指南

---

## 目录

1. [项目概述](#1-项目概述)
2. [目录结构](#2-目录结构)
3. [技术层 - 系统实现](#3-技术层---系统实现)
4. [实验评估层](#4-实验评估层)
5. [技术支撑材料](#5-技术支撑材料)
6. [快速开始](#6-快速开始)
7. [方案学术化命名](#7-方案学术化命名)

---

## 1. 项目概述

本项目是一个基于大语言模型（LLM）的企业文档智能审校系统，核心特点：

- **多策略文档解析**：支持 Baseline-Naive、Ours-Fixed（SSLA）、Ours-Adaptive（HDCA） 三种解析+分块策略
- **双Agent协同架构**：Detector Agent + Reviewer Agent 实现高召回+高精度
- **异构文档支持**：PDF、DOCX、PPTX、Excel、CHM 等多种格式

### 核心参数

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `strategy` | `baseline-naive`, `ours-fixed`, `ours-adaptive` | 分块策略 |
| `agent_mode` | `detector-only`, `dual-agent` | Agent 架构模式 |

---

## 2. 目录结构

```
material-ai-test-sys/
├── api.py                      # FastAPI 应用入口
├── processor.py                # 核心处理流程
├── config/
│   └── config.py               # 全局配置（API URL、模型、Prompt等）
├── models/                     # 数据模型定义
│   ├── chunk.py                # TextChunk 模型
│   ├── material.py             # Material 文档模型
│   └── task.py                 # Task 任务模型
├── utils/                      # 工具类
│   ├── chunker_util.py         # 【核心】分块策略实现
│   ├── llm_util.py             # LLM API 调用封装
│   ├── common.py               # 通用工具函数
│   └── logger.py               # 日志配置
├── service/                    # 服务层
│   ├── material_service.py     # 文档服务
│   └── task_service.py         # 任务服务
├── dao/                        # 数据访问层
│   ├── material_dao.py         # 文档 DAO
│   └── task_dao.py             # 任务 DAO
├── storage/
│   └── sqlite_storage.py       # SQLite 存储
├── files/                      # 测试数据
│   ├── clean_pdf/              # 干净的 PDF 文档（实验一）
│   ├── clean_md/               # MinerU 解析后的 Markdown（实验一）
│   ├── dirty_md/               # 带错误的 Markdown（实验二）
│   └── ground_truth/           # Ground Truth 标注数据
├── temp_tasks/                 # 实验任务输出目录
│   ├── adaptive + dual-agent/  # 各配置的实验结果
│   └── ...
├── scripts/                    # 【实验评估】评估脚本和可视化
│   ├── exp1/                   # 实验一：分块策略评估
│   ├── exp2/                   # 实验二：消融实验
│   └── dataset_description/    # 数据集统计与可视化
├── experiment_design/          # 实验报告
│   ├── 实验结果分析报告_v4.md  # 实验一报告
│   └── 实验结果分析报告_exp2_v2.md  # 实验二报告
├── support_material/           # 【技术支撑】论文写作材料
│   ├── technical_analysis_report.md  # 技术分析综合报告
│   ├── ssla_algorithms.tex     # SSLA 伪代码（STP+PCSW）
│   ├── TRAC.tex                # TRAC 伪代码
│   ├── algorithm_paper_text.md # 论文级伪代码配套说明
│   └── academic_comparison.md  # SSLA与HDCA学术对比
└── logs/                       # 运行日志
```

---

## 3. 技术层 - 系统实现

### 3.1 API 入口

**文件**: `api.py`

```python
# 核心 API 端点
POST /v1/tasks          # 创建审校任务
GET  /v1/result         # 获取任务结果
GET  /v1/issues         # 获取问题列表
GET  /v1/download       # 下载结果文件
```

**关键参数处理** (第163-211行):
```python
@app.post("/v1/tasks")
async def create_task(
    file: List[UploadFile],
    scan_items: str,
    strategy: str = "ours-adaptive",      # 分块策略
    agent_mode: str = "dual-agent"        # Agent模式
)
```

### 3.2 核心处理流程

**文件**: `processor.py`

| 函数 | 行号 | 功能 |
|------|------|------|
| `start_task()` | 137-213 | 主任务入口，协调整个流程 |
| `chunking_materials()` | 51-134 | 根据 strategy 选择分块方法 |
| `start_scaning_process()` | 349-372 | 异步调用 Detector Agent |
| `agent_check_report_jsonl()` | 215-263 | Reviewer Agent 过滤误报 |
| `get_response()` | 375-421 | 单个 chunk 的 LLM 调用 |

**策略选择逻辑** (`chunking_materials`, 第70-123行):
```python
if strategy == "baseline-naive":
    splitter = BaselineNaiveSplitter(...)    # PyPDF2 + 滑动窗口
elif strategy == "ours-fixed":
    splitter = DocumentSplitter(..., adaptive_chunk=False)  # pdfplumber + 段落感知
elif strategy == "ours-adaptive":
    splitter = DocumentSplitter(..., adaptive_chunk=True)   # MinerU + 结构感知
```

### 3.3 分块策略实现

**文件**: `utils/chunker_util.py`

这是系统的核心文件，包含三种分块策略的完整实现：

| 类名 | 行号 | 对应策略 | 说明 |
|------|------|----------|------|
| `BaselineNaiveSplitter` | 1461-1546 | `baseline-naive` | PyPDF2 原始提取 + 纯滑动窗口 |
| `DocumentSplitter` | 475-933 | `ours-fixed` | PrecisionPDFProcessor + 段落感知分块 |
| `MarkdownSemanticSplitter` | 45-472 | `ours-adaptive` | Markdown 树形解析 + 结构感知分块 |
| `PrecisionPDFProcessor` | 951-1458 | (被 Fixed 策略调用) | 精细化 PDF 解析 |

**Baseline-Naive 实现** (第1461-1546行):
```python
class BaselineNaiveSplitter:
    def _extract_text_pypdf2(self, file_path):     # PyPDF2 原始提取
    def _sliding_window_split(self, text):         # 纯滑动窗口分块
```

**Ours-Fixed (SSLA) 实现** (第475-933行):
```python
class DocumentSplitter:
    def _split_pdf(self, file_path):               # 调用 PrecisionPDFProcessor
    def split_text_into_chunks(self, text):        # 段落感知固定分块
    def split_long_paragraph(self, para):          # 超长段落处理
```

**Ours-Adaptive (HDCA) 实现** (第45-472行):
```python
class MarkdownSemanticSplitter:
    def _parse_to_tree(self, lines):               # Markdown → 树形结构
    def _recursive_split(self, node, acc, chunks): # 递归贪心分块
    def _split_and_flush_long_text(self, text):    # 长表格续表机制
```

### 3.4 LLM 调用封装

**文件**: `utils/llm_util.py`

| 方法 | 功能 |
|------|------|
| `call_llm_api()` | Detector Agent 调用（纠错检测） |
| `call_llm_check_api()` | Reviewer Agent 调用（误报过滤） |

### 3.5 配置文件

**文件**: `config/config.py`

```python
# 核心配置项
CHUNK_SIZE = 1000           # 默认分块大小
OVERLAP = 50                # 重叠窗口
MAX_WORKER = 10             # 最大并发数

# LLM 配置
API_URL = {...}             # API 端点
MODEL = {...}               # 模型名称

# Prompt 配置
SCAN_ITEMS_PROMPT_MAP = {...}       # 各扫描项的 Prompt
MARKDOWN_PROMPT_SUFFIX = "..."      # Markdown 模式补丁
PDF_CLEANING_PROMPT_SUFFIX = "..."  # PDF 模式补丁
```

### 3.6 数据模型

**文件**: `models/chunk.py`
```python
class TextChunk:
    file_path: str
    text: str
    length: int
    language: str
    metadata: dict  # 包含 strategy 信息
```

**文件**: `models/task.py`
```python
class Task:
    task_id: str
    strategy: str       # baseline-naive | ours-fixed | ours-adaptive
    agent_mode: str     # detector-only | dual-agent
    materials: List[Material]
```

---

## 4. 实验评估层

### 4.1 实验一：分块策略评估

**目录**: `scripts/exp1/`

| 文件 | 功能 |
|------|------|
| `evaluate_performance_v4.py` | 主评估脚本 |
| `plot_results_v4.py` | 可视化生成脚本 |
| `plots_v4/` | 输出图表目录 |

**评估脚本核心逻辑** (`evaluate_performance_v4.py`):

| 函数/类 | 行号 | 功能 |
|---------|------|------|
| `TrueBaselineStrategy` | 68-121 | Baseline-Naive 策略封装 |
| `OursFixedStrategy` | 124-155 | Ours-Fixed 策略封装 |
| `OursAdaptiveStrategy` | 158-198 | Ours-Adaptive 策略封装 |
| `evaluate_parsing_quality()` | 298-305 | 解析质量评估 |
| `check_valid_start_v3()` | 315-355 | 有效起始率检查 |
| `check_valid_end_v3()` | 358-401 | 有效结尾率检查 |
| `check_table_fragmentation_v3()` | 404-425 | 表格破碎率检查 |

**指标计算代码位置**:

| 指标 | 计算位置 | 行号 |
|------|----------|------|
| Structure Marker Density | `calculate_structure_marker_density()` | 245-273 |
| Information Density | `calculate_information_density()` | 276-295 |
| Valid Start Rate | `check_valid_start_v3()` | 315-355 |
| Valid End Rate | `check_valid_end_v3()` | 358-401 |
| Fully Intact Rate | `evaluate_chunk_quality()` | 428-441 |
| Table Fragmentation Ratio | `check_table_fragmentation_v3()` | 404-425 |

**实验报告**: `experiment_design/实验结果分析报告_v4.md`

### 4.2 实验二：消融实验

**目录**: `scripts/exp2/`

| 文件 | 功能 |
|------|------|
| `evaluate_ablation.py` | 消融实验评估脚本 |
| `plot_ablation.py` | 可视化生成脚本 |
| `figures/` | 输出图表目录 |
| `ablation_results.csv` | 所有运行结果 |
| `ablation_best.csv` | 最佳结果汇总 |

**评估脚本核心逻辑** (`evaluate_ablation.py`):

| 函数/类 | 行号 | 功能 |
|---------|------|------|
| `EvaluationMetrics` | 32-78 | 指标数据类定义 |
| `ExperimentResult` | 81-99 | 实验结果数据类 |
| `parse_experiment_dir()` | 106-141 | 解析目录名获取配置 |
| `check_match()` | 255-282 | GT 与报告匹配算法 |
| `evaluate_report()` | 285-320 | 单报告评估 |
| `evaluate_experiment()` | 327-401 | 单实验评估 |

**指标计算代码位置**:

| 指标 | 计算位置 | 行号 |
|------|----------|------|
| Recall | `EvaluationMetrics.recall` | 42-45 |
| Precision | `EvaluationMetrics.precision_dedup` | 51-54 |
| Recall | `EvaluationMetrics.recall_dedup` | 56-57 |
| F1-Score | `EvaluationMetrics.f1_dedup` | 59-63 |
| FPR | `EvaluationMetrics.false_positive_rate` | 65-68 |
| Redundancy | `EvaluationMetrics.redundancy` | 70-73 |

**匹配算法** (`check_match()`, 第255-282行):
```python
def check_match(gt_row, rpt_row):
    # 条件1: injected_text 是 问题所在句子 的子串
    condition1 = injected_text in problem_sentence
    # 条件2: expected_correction 在 修改建议 中
    # 或关键词匹配
    return condition1 and (expected_correction in suggestion or keyword_match)
```

**实验报告**: `experiment_design/实验结果分析报告_exp2_v2.md`

### 4.3 数据集描述

**目录**: `scripts/dataset_description/`

| 文件 | 功能 |
|------|------|
| `generate_dataset_stats.py` | 数据集统计生成脚本 |
| `dataset_table.tex` | LaTeX 数据集表格 |
| `README.md` | 数据集详细说明 |
| `figures/` | 可视化图表（构成图、摘要图、密度图） |

**数据集概况**:
- **来源**: 华为云公开文档 (https://support.huaweicloud.com/)
- **文档数**: 5 篇 PDF
- **总页数**: 296 页
- **总字符数**: 239,556 字符
- **注入错误数**: 200 个

| 文档 | 页数 | 字符数 | 注入错误数 |
|------|------|--------|-----------|
| 常见问题 | 102 | 84,560 | 70 |
| 计费说明 | 73 | 52,716 | 50 |
| 产品介绍 | 56 | 42,512 | 40 |
| 抽屉式帮助 | 33 | 23,223 | 20 |
| 快速入门 | 32 | 36,545 | 20 |

### 4.4 Ground Truth 数据

**文件**: `files/ground_truth/对象存储服务 OBS 产品介绍_dirty.csv`

| 字段 | 说明 |
|------|------|
| `file_name` | 文档名称 |
| `page` | 页码 |
| `scan_item` | 扫描项代码 |
| `error_type` | 错误类型 |
| `injected_text` | 注入的错误文本 |
| `expected_correction` | 期望的修正文本 |

**错误类型分布**:
- 中文错别字: 18
- 英文拼写错误: 12
- 错误用词: 5
- 标点符号不闭合: 4
- 乱码错误: 1

### 4.5 实验输出目录

**目录**: `temp_tasks/`

每个实验配置的输出结构：
```
temp_tasks/{配置名}/
├── report.csv              # 最终报告（Reviewer 后）
├── report.jsonl            # 最终报告 JSON 格式
├── report_detector.csv     # Detector 阶段报告
├── report_detector.jsonl   # Detector 阶段 JSON
├── chunk_stats.csv         # 分块统计
├── {扫描项目录}/           # 各扫描项结果
│   └── scan_result.csv
└── *.pdf                   # 原始文档
```

---

## 5. 技术支撑材料

**目录**: `support_material/`

本目录包含为论文写作准备的技术分析文档和伪代码，目标是让读者（人类或LLM）能够**完全掌握项目技术细节**，实现与代码的解耦。

### 5.1 文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `technical_analysis_report.md` | 技术报告 | 三种策略的详尽技术分析，含代码行号引用、架构图 |
| `ssla_algorithms.tex` | LaTeX伪代码 | STP（解析）和 PCSW（分块）的完整伪代码 |
| `TRAC.tex` | LaTeX伪代码 | TRAC 分块算法伪代码 |
| `algorithm_paper_text.md` | 论文配套 | 可直接用于论文的伪代码说明段落、复杂度分析 |
| `academic_comparison.md` | 学术对比 | SSLA 与 HDCA 的深度对比，含实验数据、场景指南 |

### 5.2 技术分析报告结构

`technical_analysis_report.md` 包含：

| 章节 | 内容 |
|------|------|
| 第1-2章 | 问题定义、术语表、系统架构总览 |
| 第3章 | Baseline-Naive 简要介绍 |
| 第4章 | **SSLA 完整技术分析**：STP 解析（边界框过滤、精确换行处理）、PCSW 分块 |
| 第5章 | **HDCA 完整技术分析**：HSP 解析（MinerU）、TRAC 分块（语义树、续表机制） |
| 第6章 | 方案对比分析表 |
| 第7章 | 代码路径索引 |

### 5.3 伪代码文件

**SSLA 伪代码** (`ssla_algorithms.tex`):
- 算法1: STP 主流程（边界框过滤、文本提取）
- 算法2: STP 辅助函数（重叠检测、换行处理、单词重组）
- 算法3: PCSW 主流程（段落约束分块）
- 算法4: PCSW 超长段落处理（两级切分策略）

**TRAC 伪代码** (`TRAC.tex`):
- 算法1: 主流程（语义树构建 + 递归遍历）
- 算法2: 超长叶子节点处理（表格续表机制）
- 算法3: 碎片防御策略

### 5.4 论文写作支持

`algorithm_paper_text.md` 提供：
- 每个算法的**可直接用于论文的描述段落**
- 时间/空间复杂度分析
- 关键创新点陈述

`academic_comparison.md` 提供：
- 技术路线对比图
- 解析模块对比（STP vs HSP）
- 分块模块对比（PCSW vs TRAC）
- 实验数据对比表
- 论文章节结构建议
- 图表规划建议

---

## 6. 快速开始

### 6.1 安装依赖

```bash
pip install -r requirements.txt
```

### 6.2 启动服务

```bash
python api.py
# 服务运行在 http://localhost:8082
```

### 6.3 API 调用示例

```bash
# 使用最优配置（Ours-Adaptive + Dual-Agent）
curl -X POST "http://localhost:8082/v1/tasks" \
  -F "file=@document.pdf" \
  -F "scan_items=scanItem5001,scanItem5002" \
  -F "strategy=ours-adaptive" \
  -F "agent_mode=dual-agent"

# 使用轻量级配置（Ours-Fixed + Dual-Agent）
curl -X POST "http://localhost:8082/v1/tasks" \
  -F "file=@document.pdf" \
  -F "strategy=ours-fixed" \
  -F "agent_mode=dual-agent"
```

### 6.4 运行评估实验

```bash
# 实验一：分块策略评估
cd scripts/exp1
python evaluate_performance_v4.py
python plot_results_v4.py

# 实验二：消融实验评估
cd scripts/exp2
python evaluate_ablation.py
python plot_ablation.py
```

---

## 附录：关键数学公式

### 实验一指标

| 指标 | 公式 |
| :--- | :--- |
| Structure Density | $\frac{\sum_i \text{count}(\text{marker}_i)}{\lvert \text{text} \rvert} \times 1000$ |
| Information Density | $\frac{\lvert \text{text} \rvert - \lvert \text{whitespace} \rvert}{\lvert \text{text} \rvert}$ |
| Valid Start Rate | $\frac{\sum_{c \in C} \mathbb{1}[\text{valid\_start}(c)]}{\lvert C \rvert}$ |
| Valid End Rate | $\frac{\sum_{c \in C} \mathbb{1}[\text{valid\_end}(c)]}{\lvert C \rvert}$ |
| Fully Intact Rate | $\frac{\sum_{c \in C} \mathbb{1}[\text{valid\_start}(c) \land \text{valid\_end}(c)]}{\lvert C \rvert}$ |
| TFR | $\frac{\lvert \{c : \text{table\_start}(c) \neq \text{table\_end}(c)\} \rvert}{\lvert C \rvert}$ |

### 实验二指标

| 指标 | 公式 |
| :--- | :--- |
| Recall | $\frac{\text{matched\_gt\_count}}{\lvert \text{GT} \rvert}$ |
| Precision | $\frac{\text{matched\_output\_count}}{\lvert \text{Report}_{\text{dedup}} \rvert}$ |
| F1-Score | $\frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$ |
| FPR | $1 - \text{Precision}$ |

**重要关系**: 在本实验设置中，**Precision = 1 - FPR** 恒成立（详见实验报告 3.4.2 节）。


## 7. 方案学术化命名

### 📊 命名方案

### **Ours-Fixed 方案**

| 层级 | 中文命名 | 英文命名 | 缩写 |
|------|---------|---------|------|
| **整体架构** | 基于文本流语义的轻量化上下文构建架构 | Stream-based Semantic Lightweight Architecture | **SSLA** |
| **解析模块** | 流式文本精细解析 | Stream-based Text Parsing | **STP** |
| **分块算法** | 段落约束型滑动窗口分块算法 | Paragraph-Constrained Sliding Window | **PCSW** |

### **Ours-Adaptive 方案**

| 层级 | 中文命名 | 英文命名 | 缩写 |
|------|---------|---------|------|
| **整体架构** | 基于文档层级结构的深度上下文构建架构 | Hierarchy-based Deep Context Architecture | **HDCA** |
| **解析模块** | 文档层级结构解析（基于MinerU） | Hierarchical Structure Parsing | **HSP**（标注为外部工具） |
| **分块算法** | 基于文档树的递归自适应分块算法 | Tree-based Recursive Adaptive Chunking | **TRAC** |

---

### **🎯 命名体系总览**

```
┌─────────────────────────────────────────────────────────────────┐
│                    文档审校系统 - 上下文构建层                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────┐    ┌─────────────────────────────┐ │
│  │   SSLA (轻量化方案)       │    │   HDCA (深度方案)            │ │
│  │   ─────────────────     │    │   ─────────────────         │ │
│  │   解析: STP (文本流解析)  │    │   解析: HSP (层级解析/MinerU) │ │
│  │   分块: PCSW (段落约束)   │    │   分块: TRAC (树递归自适应)    │ │
│  │                         │    │                             │ │
│  │   特点: CPU推理/低延迟    │    │   特点: GPU加速/高质量         │ │
│  └─────────────────────────┘    └─────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```