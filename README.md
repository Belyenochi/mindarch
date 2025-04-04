# MindArch - 知识图谱管理系统

MindArch是一个知识图谱管理系统，专注于从文本中提取结构化知识，构建语义关系网络，并提供直观的可视化和交互界面。系统使用DeepSeek-R1模型进行智能知识处理，支持多种知识表示和分析功能。

## 功能特点

- 从文本文件中自动提取知识单元和关系
- 基于RDF三元组模型的知识表示
- 交互式知识图谱可视化
- AI驱动的实体识别、关系提取和消歧
- 灵活的知识单元自定义和编辑
- RESTful API支持系统集成

## 技术栈

- **后端**: Python 3.9+, FastAPI
- **数据库**: MongoDB
- **AI处理**: DeepSeek-R1
- **前端**: React.js, D3.js (可视化)
- **部署**: Docker, Nginx

## 目录结构

```
mindarch/
├── api/                       # API层
│   ├── app.py                 # FastAPI应用入口
│   ├── routes/                # API路由
│   │   ├── knowledge_units.py # 知识单元API端点
│   │   ├── semantic_triples.py# 语义三元组API端点
│   │   ├── knowledge_graphs.py# 知识图谱API端点
│   │   └── file_imports.py    # 文件导入API端点
│   ├── middleware/            # 中间件
│   │   └── auth.py            # 认证中间件
│   └── schemas/               # 请求/响应模型
│       ├── knowledge_units.py # 知识单元模式
│       ├── semantic_triples.py# 语义三元组模式
│       └── knowledge_graphs.py# 知识图谱模式
│
├── core/                      # 核心业务逻辑
│   ├── config.py              # 系统配置
│   ├── models/                # 数据模型
│   │   ├── knowledge_unit.py  # 知识单元数据模型
│   │   ├── semantic_triple.py # 语义三元组数据模型
│   │   └── knowledge_graph.py # 知识图谱数据模型
│   └── services/              # 业务服务
│       ├── knowledge_unit.py  # 知识单元服务
│       ├── semantic_triple.py # 语义三元组服务
│       └── knowledge_graph.py # 知识图谱服务
│
├── ai/                        # AI服务
│   ├── client.py              # DeepSeek-R1 API客户端
│   ├── extraction/            # 知识提取
│   │   ├── unit_extractor.py  # 知识单元提取器
│   │   ├── relation_extractor.py # 关系提取器
│   │   └── entity_resolver.py # 实体消歧器
│   ├── prompts/               # 提示模板
│   │   ├── unit_prompts.py    # 知识单元提取提示
│   │   ├── relation_prompts.py# 关系提取提示
│   │   └── resolution_prompts.py # 实体消歧提示
│   └── evaluation/            # AI结果评估
│       ├── confidence.py      # 置信度评估
│       └── quality.py         # 质量评估
│
├── importers/                 # 文件导入
│   ├── base.py                # 基础导入器
│   ├── txt_importer.py        # TXT文件导入器
│   ├── md_importer.py         # Markdown文件导入器
│   └── manager.py             # 导入管理器
│
├── db/                        # 数据库
│   ├── connection.py          # 数据库连接
│   └── repositories/          # 数据存储库
│       ├── knowledge_unit_repo.py # 知识单元仓库
│       ├── semantic_triple_repo.py # 语义三元组仓库
│       └── knowledge_graph_repo.py # 知识图谱仓库
│
├── services/                  # 系统服务
│   ├── auth.py                # 认证服务
│   └── cache.py               # 缓存服务
│
├── tests/                     # 测试
│   ├── conftest.py            # 测试配置
│   └── integration/           # 集成测试
│       ├── test_api.py        # API测试
│       └── test_import.py     # 导入测试
│
├── main.py                    # 应用入口
├── requirements.txt           # 依赖列表
├── Dockerfile                 # Docker配置
├── docker-compose.yml         # Docker Compose配置
├── .env.example               # 环境变量示例
└── README.md                  # 项目说明
```

## 核心模块说明

### API层 (api/)

API层处理HTTP请求和响应，将客户端请求路由到相应的业务服务。

- **app.py**: FastAPI应用实例和全局配置
- **routes/**: API端点定义，包括知识单元、语义三元组和知识图谱的CRUD操作
- **schemas/**: 请求和响应数据模型，使用Pydantic进行验证

### 核心业务逻辑 (core/)

包含系统的主要业务逻辑和数据模型。

- **models/**: 核心数据模型定义，使用Beanie ODM
- **services/**: 业务服务实现，处理复杂业务逻辑和事务

### AI服务 (ai/)

AI服务处理智能知识提取和关系构建。

- **client.py**: DeepSeek-R1 API调用封装
- **extraction/**: 知识提取逻辑，包括单元提取、关系提取和实体消歧
- **prompts/**: 提示工程模板，用于指导AI生成结构化输出
- **evaluation/**: AI生成内容的质量评估和置信度计算

### 文件导入 (importers/)

处理不同格式文件的导入和解析。

- **base.py**: 导入器基类和通用处理逻辑
- **txt_importer.py/md_importer.py**: 特定格式文件的导入实现
- **manager.py**: 导入流程管理和任务调度

### 数据库 (db/)

数据库连接和数据访问层。

- **connection.py**: 数据库连接管理
- **repositories/**: 数据访问对象，封装数据库操作

## 数据模型

### 知识单元 (Knowledge Unit)

知识单元是系统的基本数据单位，表示从文本中提取的知识片段。

```python
class KnowledgeUnit:
    id: ObjectId                # 唯一标识符
    title: str                  # 标题(限20中文/40英文字符)
    content: str                # 内容
    unit_type: str              # 单元类型(note/entity/concept等)
    canonical_name: str         # 规范名称(用于消歧)
    aliases: List[str]          # 别名列表
    tags: List[str]             # 标签列表
    source: Source              # 来源信息
    status: Status              # 状态信息
    knowledge: Knowledge        # 知识表示
    metrics: Metrics            # 度量指标
    created_at: datetime        # 创建时间
    updated_at: datetime        # 更新时间
    created_by: str             # 创建者
    merged_units: List[str]     # 已合并单元ID
    parent_units: List[str]     # 父级单元ID
    metadata: Dict              # 元数据
```

### 语义三元组 (Semantic Triple)

语义三元组表示知识单元之间的关系，采用RDF结构。

```python
class SemanticTriple:
    id: ObjectId                # 唯一标识符
    subject_id: ObjectId        # 主语知识单元ID
    predicate: str              # 谓词(关系类型)
    object_id: ObjectId         # 宾语知识单元ID
    confidence: float           # 关系置信度(0-1)
    relation_type: str          # 关系类别(is-a/part-of等)
    bidirectional: bool         # 是否为双向关系
    created_at: datetime        # 创建时间
    updated_at: datetime        # 更新时间
    source_id: ObjectId         # 来源ID
    context: str                # 上下文描述
    metadata: Dict              # 元数据
```

### 知识图谱 (Knowledge Graph)

知识图谱组织相关的知识单元和语义三元组。

```python
class KnowledgeGraph:
    id: ObjectId                # 唯一标识符
    name: str                   # 图谱名称
    description: str            # 图谱描述
    owner_id: str               # 所有者ID
    root_units: List[ObjectId]  # 根知识单元ID
    included_units: List[ObjectId] # 包含的单元ID
    included_triples: List[ObjectId] # 包含的三元组ID
    created_at: datetime        # 创建时间
    updated_at: datetime        # 更新时间
    status: str                 # 状态(active/archived)
    is_public: bool             # 是否公开
    metadata: Dict              # 元数据
    visual_settings: Dict       # 可视化设置
```

## 安装与运行

### 环境要求

- Python 3.9+
- MongoDB 5.0+
- Docker (可选)

### 安装步骤

1. 克隆仓库
   ```bash
   git clone https://github.com/yourusername/mindarch.git
   cd mindarch
   ```

2. 创建虚拟环境
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或 venv\Scripts\activate  # Windows
   ```

3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

4. 配置环境变量
   ```bash
   cp .env.example .env
   # 编辑.env文件，配置MongoDB连接和DeepSeek-R1 API密钥
   ```

5. 运行应用
   ```bash
   python main.py
   ```

### Docker部署

使用Docker Compose进行部署：

```bash
docker-compose up -d
```

## API文档

运行应用后，可通过以下地址访问API文档：

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 使用示例

### 导入文件并提取知识

```python
import requests

# 上传文件
files = {'file': open('document.txt', 'rb')}
response = requests.post('http://localhost:8000/api/v1/import', files=files)
import_id = response.json()['import_id']

# 查询导入状态
status = requests.get(f'http://localhost:8000/api/v1/import/{import_id}')
print(status.json())

# 获取生成的知识图谱
graph_id = status.json()['graph_id']
graph = requests.get(f'http://localhost:8000/api/v1/graphs/{graph_id}')
print(graph.json())
```

### 查询知识单元

```python
# 搜索知识单元
response = requests.post('http://localhost:8000/api/v1/units/search', 
                        json={'query': '数据结构', 'limit': 10})
units = response.json()

# 获取单元详情
unit_id = units[0]['id']
unit = requests.get(f'http://localhost:8000/api/v1/units/{unit_id}')
print(unit.json())

# 获取单元相关关系
relations = requests.get(f'http://localhost:8000/api/v1/triples/by-unit/{unit_id}')
print(relations.json())
```

## 贡献指南

欢迎贡献代码、报告问题或提出新功能建议。请遵循以下步骤：

1. Fork项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 详情见 [LICENSE](LICENSE) 文件

## 联系方式

项目维护者: JasonZhu - 491537461q@gmail.com

项目链接: [https://github.com/yourusername/mindarch](https://github.com/yourusername/mindarch)

---

*MindArch - 将非结构化文本转化为结构化知识的智能系统*