from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_DB_PATH = DATA_DIR / "app.db"

MAX_WORKER = 20
MAX_TOKEN = 8192
SLICE_SIZE = 3000
CHUNK_SIZE = 2000
OVERLAP = 0
TEMP_DIR = r"/Users/moiley/Documents/material-ai-test-sys/temp_tasks"
ARCHIVE_DIR = r"/Users/moiley/Documents/material-ai-test-sys/temp_tasks"
MAX_WORKS = 10

SENTENCE_ENDINGS = r'[。？！.?!"…]'

# --- 配置区域 ---
# 统一的 API URL
API_URL_BASE = "https://cloud.infini-ai.com/maas/v1/chat/completions"

# 检错 Agent 使用的模型 (Detector Agent)
DETECTOR_MODEL_NAME = "qwen2.5-72b-instruct"

# 校验 Agent 使用的模型 (Reviewer Agent)
REVIEWER_MODEL_NAME = "qwen2.5-72b-instruct"

# -------------------------------------

API_URL = {
    "english": API_URL_BASE,
    "chinese": API_URL_BASE
}

MODEL = {
    "english": DETECTOR_MODEL_NAME,
    "chinese": DETECTOR_MODEL_NAME
}

# 显式定义检错模型，与 MODEL 保持一致
DETECTOR_MODEL = MODEL

# 定义校验 Agent 配置
REVIEW_AGENT_LANG = "chinese" # 默认使用中文配置
REVIEW_AGENT_API_URL = API_URL_BASE
REVIEW_AGENT_MODEL = REVIEWER_MODEL_NAME

# --- Prompt 动态选择 ---

# 1. 针对 Ours-Fixed 的 Prompt 补丁 (处理PDF提取噪音)
PDF_CLEANING_PROMPT_SUFFIX = """
\n
# 处理规则（必须同时满足）
1. 确定性原则：仅修改100%确定的错误
2. 非必要不优化原则：仅修复检测到的错误，禁止对非错误内容进行润色或改写
3. 白名单原则：豁免项直接跳过
4. 全角半角同义：全角字符和半角字符均视为正确
5. 自适应连字符：△表示连接段落或者单词的自定义特殊符号，比如"not△ba△d"代表的是"not bad"，为正常现象,忽略此类问题导致的拼写错误
6. 空格错误：忽略因为单词或者句子中存在空格导致的拼写错误
"""

# 2. 针对 Ours-Adaptive 自适应分块的 Prompt 补丁 (处理Markdown/HTML噪音)
MARKDOWN_PROMPT_SUFFIX = """
\n
# 处理规则（必须同时满足）
1. 确定性原则：仅修改100%确定的错误
2. 非必要不优化原则：仅修复检测到的错误，禁止对非错误内容进行润色或改写
3. 白名单原则：豁免项直接跳过
4. 全角半角同义：全角字符和半角字符均视为正确
5. 格式豁免原则：
   - 输入的文本采用 Markdown 格式，且包含 HTML 表格标签（如 <table>, <tr>, <td> 等）。
   - 请忽略所有的 Markdown 格式符号和 HTML 标签，**绝对不要**对它们进行拼写检查或纠错。
   - 如果表格被切分导致标签不完整，请尝试根据上下文理解内容，不要报错。
   - 仅检查文本内容本身。
"""

# 兼容旧代码
ADAPTIVE_PROMPT_SUFFIX = MARKDOWN_PROMPT_SUFFIX
# ------------------------------

STATUS_MAP = {
    "processing": "任务处理中",
    "error": "任务执行失败"
}

# SCAN_ITEMS_MAP = {
#     "scanItem1001": "英文资料存在中文字符或乱码",
#     "scanItem1002": "中文资料存在外语章节",
#     "scanItem5001": "英文单词拼写错误",
#     "scanItem5002": "中文错别字",
#     "scanItem5003": "英文单词大小写错误",
#     "scanItem5004": "英文文档低级语法错误",
#     "scanItem5005": "不规范用语或错误用语",
#     "scanItem6001": "上下文一致性错误",
#     "scanItem6002": "对称的标点符号（仅限于中英文引号、星号、书名号）只写了一半或前后不匹配",
#     "scanItem6003": "标点符号前后的空格错误",
#     "scanItem6004": "中文文档中使用了半角标点符号",
#     "scanItem12009": "文档中存在乱码",
#     "scanItem13002": "6.5版本以上是否有FusionCloud字眼",
#     "scanItem14003": "英文中是否有隐藏中文字符",
#     "scanItem99999": "敏感词扫描"
# }

# DIRECTORY_MAP_DICT = {
#     "英文资料存在中文字符或乱码": "scanItem1001",
#     "中文资料存在外语章节": "scanItem1002",
#     "英文单词拼写错误": "scanItem5001",
#     "中文错别字": "scanItem5002",
#     "英文单词大小写错误": "scanItem5003",
#     "英文文档低级语法错误": "scanItem5004",
#     "不规范用语或错误用语": "scanItem5005",
#     "上下文一致性错误": "scanItem6001",
#     "对称的标点符号（仅限于中英文引号、星号、书名号）只写了一半或前后不匹配": "scanItem6002",
#     "标点符号前后的空格错误": "scanItem6003",
#     "中文文档中使用了半角标点符号": "scanItem6004",
#     "文档中存在乱码": "scanItem12009",
#     "6.5版本以上是否有FusionCloud字眼": "scanItem13002",
#     "英文中是否有隐藏中文字符": "scanItem14003",
#     "敏感词扫描": "scanItem99999",
#     "错别字、拼写错误": "default"
# }

# SCAN_ITEMS_PROMPT_MAP = {
#     "scanItem1001": "SKIP_EXECUTION",
#     "scanItem1002": "SKIP_EXECUTION",
#     "scanItem5001": "[仅检查英文字母]！不对字母大小写、中文字符和标点符号做任何检查！",
#     "scanItem5002": "[仅检查中文汉字]！不对英文字母和标点符号做任何检查！",
#     # "scanItem5002": "1.仅检查[中文字符]，不对英文字符做任何检查！\n2.检查[形近字混淆]：字形相似但意义和用法完全不同（如已、己、巳） \n3.检查[音近字混用]：读音相近，容易听错写错（如州和洲）\n4.检查[词义辨析不清]：词语意思相近，但适用范围不同（如权利和权力）\n",
#     "scanItem5003": "SKIP_EXECUTION",
#     "scanItem5004": "SKIP_EXECUTION",
#     "scanItem5005": "SKIP_EXECUTION",
#     "scanItem6001": "若同一用语在不同句子中的前后表述不一致，且<因此一定会引发歧义或误解>并造成事实性错误，才进行纠错；否则，不对此句进行任何纠错。",
#     "scanItem6002": "1.仅检查以下列出的标点符号：单引号、双引号、星号、书名号，并忽略其他所有符号！\n2.检查 [标点缺失]：成对符号缺失，只有半边的符号，如“你好（缺少右半边引号）。 \n3.检查 [标点不匹配]：前后符号不成对，如'双城记》（应为《双城记》）和‘I'm Jack.”（应为'I'm Jack.'）等",
#     "scanItem6003": "SKIP_EXECUTION",
#     # "scanItem6003": "英文文档中标点符号前后的空格错误，对于目录和标题、图、表中的问题不是错误，同时有关空格的错误，只有连续多个空格才认为是问题",
#     "scanItem6004": "SKIP_EXECUTION",
#     "scanItem12009": "检查[编码混淆型错误]: \n1.[GBK读UTF-8]型错误: 出现古文、日文、韩文混合; \n2.[UTF-8读GBK/ISO-8859-1]型错误: 出现一串无意义的符号（如??, €, Â¿, □等）。",
#     "scanItem13002": "SKIP_EXECUTION",
#     "scanItem14003": "SKIP_EXECUTION",
#     "scanItem99999": "SKIP_EXECUTION"
# }

SCAN_ITEMS_MAP = {
    "scanItem1001": "英文资料存在中文字符或乱码",
    "scanItem1002": "中文资料存在外语章节",
    "scanItem5001": "英文单词拼写错误",
    "scanItem5002": "中文错别字",
    "scanItem5003": "英文单词大小写错误",
    "scanItem5004": "英文文档低级语法错误",
    "scanItem5005": "不规范用语或错误用语",
    "scanItem6001": "上下文一致性错误",
    "scanItem6002": "标点符号成对匹配检查",
    "scanItem6003": "标点符号前后的空格错误",
    "scanItem6004": "中文文档中使用了半角标点符号",
    "scanItem12009": "文档中是否存在乱码",
    "scanItem13002": "产品名称版本合规性检查",
    "scanItem14003": "英文中是否有隐藏中文字符",
    "scanItem99999": "敏感词扫描"
}

DIRECTORY_MAP_DICT = {
    "英文资料存在中文字符或乱码": "scanItem1001",
    "中文资料存在外语章节": "scanItem1002",
    "英文单词拼写错误": "scanItem5001",
    "中文错别字": "scanItem5002",
    "英文单词大小写错误": "scanItem5003",
    "英文文档低级语法错误": "scanItem5004",
    "不规范用语或错误用语": "scanItem5005",
    "上下文一致性错误": "scanItem6001",
    "标点符号成对匹配检查": "scanItem6002",
    "标点符号前后的空格错误": "scanItem6003",
    "中文文档中使用了半角标点符号": "scanItem6004",
    "文档中是否存在乱码": "scanItem12009",
    "产品名称版本合规性检查": "scanItem13002",
    "英文中是否有隐藏中文字符": "scanItem14003",
    "敏感词扫描": "scanItem99999",
    "错别字、拼写错误": "default"
}

SCAN_ITEMS_PROMPT_MAP = {
    "scanItem1001": "SKIP_EXECUTION",
    "scanItem1002": "SKIP_EXECUTION",
    "scanItem5001": """
    1. 任务目标：仅检查[英文单词]的拼写错误（如漏字母、多字母、字母顺序错误）。
    2. 严格豁免（绝对不要修改）：
       - 所有中文内容、标点符号。
       - 编程相关的命名风格（如 camelCase, snake_case, PascalCase）。
       - 全大写的缩写词（如 HTTP, JSON）。
       - 包含数字的词（如 v6.5, 3D）。
    3. 判定标准：只有当单词明显不符合英语构词法且不是技术术语时，才判定为错误。
    """,
    "scanItem5002": """
    1. 任务目标：仅检查[中文字符]的错误。
    2. 检查维度：
       - 同音错别字（如“账号”误写为“帐号”，“部署”误写为“步署”）。
       - 形近错别字（如“己”和“已”）。
       - 输入法联想错误（如“云服务”误写为“云浮雾”）。
    3. 严格豁免：
       - 不检查英文单词、数字、公式。
       - 不检查文言文引用或成语的通假字用法。
    """,
    # "scanItem5002": "1.仅检查[中文字符]，不对英文字符做任何检查！\n2.检查[形近字混淆]：字形相似但意义和用法完全不同（如已、己、巳） \n3.检查[音近字混用]：读音相近，容易听错写错（如州和洲）\n4.检查[词义辨析不清]：词语意思相近，但适用范围不同（如权利和权力）\n",
    "scanItem5003": "SKIP_EXECUTION",
    "scanItem5004": "SKIP_EXECUTION",
    "scanItem5005": "SKIP_EXECUTION",
    "scanItem6001": "仅当同一[专有名词]在前后文中出现明显的写法不一致（如前文用'帐号'后文用'账号'）时才报错。",
    # "scanItem6001": "若同一用语在不同句子中的前后表述不一致，且<因此一定会引发歧义或误解>并造成事实性错误，才进行纠错；否则，不对此句进行任何纠错。",
    "scanItem6002": """
    1. 检查范围：仅检查成对标点符号（引号 "", '', “”, ‘’；书名号 《》；括号 ()）。
    2. 错误定义：
       - [缺失]：只有左半边或右半边（如：“你好 ）。
       - [不匹配]：左边是中文符号，右边是英文符号（如：《产品介绍> ）。
    3. 豁免：代码块中的引号、数学公式中的括号不在此列。
    """,
    "scanItem6003": "SKIP_EXECUTION",
    # "scanItem6003": "英文文档中标点符号前后的空格错误，对于目录和标题、图、表中的问题不是错误，同时有关空格的错误，只有连续多个空格才认为是问题",
    "scanItem6004": "SKIP_EXECUTION",
    "scanItem12009": """
    检查文本中是否出现明显的[乱码符号]。
    特征参考：
    - 出现连续的无意义字符，如 "Åäö", "??", "â‚¬", "□□"。
    - 或者是GBK/UTF-8编码转换错误导致的古文堆砌感（如“锟斤拷”）。
    - 正常的特殊符号（如版权号©、注册商标®）不算乱码。
    """,
    "scanItem13002": "SKIP_EXECUTION",
    "scanItem14003": "SKIP_EXECUTION",
    "scanItem99999": "SKIP_EXECUTION"
}

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "test_result_db",
    "charset": "utf8mb4"
}

MATERIAL_TYPE_DICT = {
    "docx": "Word文档",
    "pdf": "PDF文档",
    "xlsx": "Excel文档",
    "chm": "CHM文档"
}
