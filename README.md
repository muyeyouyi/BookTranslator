# 书籍翻译器

使用大语言模型将 PDF 书籍中的文字翻译为简体中文，输出 Markdown、PDF 或 Word。PDF 的读取、图片提取和文件生成均在本地执行，只有提取出来的待翻译文字会发送给配置的模型接口。

## 功能

- 支持 YAML 配置和命令行参数，命令行只覆盖明确传入的字段。
- 在本地提取 PDF 正文、可识别的表格和图片。
- 按段落组织正文并分段翻译，支持并发请求，按原文顺序输出。
- 普通表格整表序列化成带行列信息的 JSON，一次请求完成翻译，按单元格编号校验回填。
- 同一批次的重复分段只请求一次，已完成译文可从缓存恢复。
- 支持 Markdown、PDF 和可编辑的 Word（`.docx`）输出。
- 图片按实际对象边界导出，PDF 和 Word 会嵌入图片。
- 支持页码范围、仅本地提取预览、失败重试及日志记录。

## 环境与安装

需要 **Python 3.11 或以上版本**，建议使用虚拟环境，并在工程根目录执行命令。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows 的虚拟环境激活命令为 `.venv\Scripts\activate`。如果已有 Conda 环境，也可以直接使用，例如：

```bash
conda activate py312
python -m pip install -r requirements.txt
```

主要使用的库：

| 库 | 用途 |
| --- | --- |
| `openai` | 调用兼容 OpenAI Chat Completions 的模型接口 |
| `pdfplumber` | 本地 PDF 文字、表格和图片区域提取 |
| `PyYAML` | 读取配置文件 |
| `pillow` | 图片处理和尺寸检查 |
| `reportlab` | 生成 PDF |
| `python-docx` | 生成 Word 文档 |
| `loguru` | 终端和文件日志 |

## 快速开始

### 1. 准备配置

首次使用时，将 `config.example.yaml` 复制为 `config.yaml`。已有配置时跳过此步。

```bash
cp -n config.example.yaml config.yaml
```

修改模型名称、接口地址及输入文件路径：

```yaml
llm:
  model: your-model-name
  base_url: https://your-provider.example/v1
  api_key_env: OPENAI_API_KEY

common:
  book: test/test.pdf
  input_format: pdf
  output_format: markdown
  output_dir: output
  log_dir: log
  chunk_size: 3000
  max_output_tokens: 4096
  timeout: 120
  max_retries: 3
  concurrency: 3
  start_page: 1
  # end_page: 10
  # pdf_font: /path/to/chinese-font.ttf
```

`your-model-name` 和示例接口地址均为占位内容，需要替换成服务商实际提供的值。接口需要支持 Chat Completions 调用；模型是否可用及调用额度由服务商决定。

### 2. 配置密钥

macOS / Linux：

```bash
export OPENAI_API_KEY="你的 API Key"
```

Windows PowerShell：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
```

也可以在 `llm` 下直接设置 `api_key`。程序优先读取 `api_key_env` 指定的环境变量，默认变量名为 `OPENAI_API_KEY`；环境变量为空或未设置时，使用配置中的 `api_key`。

程序不会自动读取 `.env` 文件。在 PyCharm 中运行时，可以在运行配置中设置环境变量。

### 3. 先检查本地提取效果

```bash
python main.py --extract-only
```

此命令不调用模型，也不要求填写模型名称和密钥，会生成 `output/书名.extracted.md`。检查正文顺序、表格和图片后再开始翻译。

### 4. 开始翻译

```bash
python main.py
```

默认读取工程根目录的 `config.yaml`，输出格式由配置决定；未设置输出格式时使用 Markdown。

## 常见用法

```bash
# 覆盖模型、输入文件和输入格式
python main.py --model MODEL_NAME --input ./books/book.pdf --input-format pdf

# 指定配置文件
python main.py --config ./my-config.yaml

# 选择输出格式，每次运行输出一种格式
python main.py --output-format md
python main.py --output-format pdf
python main.py --output-format word

# 指定输出目录、日志目录和并发数
python main.py --output-dir ./output --log-dir ./log --concurrency 3

# 只处理第 1 至第 5 页，包含起止页
python main.py --start-page 1 --end-page 5

# 预览 Word 输出，不调用模型
python main.py --extract-only --output-format word

# 指定 PDF 中文字体
python main.py --output-format pdf --pdf-font /path/to/chinese-font.ttf

# 忽略已有翻译缓存，重新请求模型
python main.py --no-resume

# 查看帮助
python main.py --help
```

文件路径中有空格时，需要加引号，例如 `--input "./books/My Book.pdf"`。

## 参数说明

| 命令行参数 | 配置字段 | 说明 |
| --- | --- | --- |
| `--config` | — | YAML 路径，默认是工程根目录的 `config.yaml` |
| `--model` | `llm.model` | 模型名称 |
| `--input` / `--book` | `common.input` / `common.book` | 本地输入文件路径 |
| `--input-format` | `common.input_format` | 目前仅支持 `pdf`，默认 `pdf` |
| `--output-format` | `common.output_format` | 支持 `markdown`、`md`、`pdf`、`word`、`docx` |
| `--output-dir` | `common.output_dir` | 输出目录，默认 `output` |
| `--log-dir` | `common.log_dir` | 日志目录，默认 `log` |
| `--concurrency` | `common.concurrency` | 请求并发数，默认 `3`，设为 `1` 时串行处理 |
| `--start-page` | `common.start_page` | 起始页，从 `1` 开始，默认 `1` |
| `--end-page` | `common.end_page` | 结束页，包含该页；默认处理至最后一页 |
| `--pdf-font` | `common.pdf_font` | 可选的 PDF 中文字体路径 |
| `--extract-only` | — | 仅本地提取，不调用模型 |
| `--no-resume` | — | 忽略已有翻译缓存 |

以下参数通过 YAML 配置：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `llm.base_url` | 未设置 | 模型服务接口地址；不设置时由 SDK 使用其默认地址 |
| `llm.api_key_env` | `OPENAI_API_KEY` | 提供密钥的环境变量名称 |
| `llm.api_key` | 空 | 环境变量没有有效值时使用的密钥 |
| `common.chunk_size` | `3000` | 单个正文翻译分段的最大字符数，**不是 token 数**；普通表格不按此值预先拆分 |
| `common.max_output_tokens` | `4096` | 单次请求的输出 token 上限 |
| `common.timeout` | `120` | 传给模型 SDK 的请求超时设置，单位为秒 |
| `common.max_retries` | `3` | 可重试错误发生后最多重试的次数，不包含首次请求 |

参数优先级和路径规则：

- 命令行传入的值优先于配置文件；没有传入的字段继续使用配置值或程序默认值。
- 配置中的相对路径，以配置文件所在目录为基准。
- 命令行中的相对路径，以执行命令时的工作目录为基准。
- 兼容旧配置：`QianwenModel` 对应 `llm`，`common.file_format` 对应输出格式。新旧字段同时存在时，优先使用 `llm` 和 `common.output_format`；输入路径优先使用 `common.input`，其次使用 `common.book`。

## 输出文件

| 格式参数 | 文件后缀 | 特点 |
| --- | --- | --- |
| `markdown` / `md` | `.md` | 正文、Markdown 表格、相对路径引用的图片 |
| `pdf` | `.pdf` | 重新排版的中文 PDF，包含文字、表格和嵌入图片 |
| `word` / `docx` | `.docx` | 可编辑的正文、原生表格和嵌入图片 |

以 `book.pdf` 为例，输出目录可能包含：

```text
output/
├── book.zh.md                      # Markdown 译文
├── book.zh.pdf                     # PDF 译文
├── book.zh.docx                    # Word 译文
├── book.extracted.md               # 仅提取预览，后缀取决于所选格式
├── book_<文件指纹前12位>_assets/     # 本地导出的 PNG 图片
└── .checkpoints/                   # 翻译缓存
```

以上文件由各次运行分别生成。指定页码范围时，文件名会带页码，例如 `book_p1-5.zh.pdf`。

Markdown 图片为外部引用，移动 Markdown 时请同时移动对应的 `_assets` 目录。PDF 和 Word 已将图片嵌入文件，可以单独移动。

PDF 和 Word 按内容顺序重新排版，保留来源页之间的分页；译文较长时可能增加输出页数，不保证还原原 PDF 的精确版式。支持基础标题、粗体、斜体、列表和代码文字，不提供完整的 Markdown 或 LaTeX 排版支持。

### 中文字体

PDF 导出会尝试自动检测中文 TrueType 字体，也可以通过 `--pdf-font` 或 `common.pdf_font` 指定 TTF 或包含 TrueType 字形的 TTC 文件。不是所有 OTF/TTC 字体都受支持。

找不到可嵌入字体时，程序回退到 `STSong-Light` 并输出日志。为了改善跨设备显示，建议指定覆盖所需中文和特殊符号的字体。Word 会设置中文字体，最终显示效果仍受阅读设备的字体支持影响。

## 图片、表格与扫描页

- **图片**：按 PDF 图片对象的实际边界，在本地渲染为 150 DPI PNG。没有文字的页面也优先按图片区域导出，不再直接保存整页截图。重复区域会去重，多张图片按页面位置排序。
- **图片保真范围**：保留对象区域内的可见内容，不保证与原始图片文件的字节或分辨率一致。若留白本来就在图片对象内部，不会自动裁掉；图片内的文字暂不翻译。
- **表格**：每张可识别表格整体转换成 JSON，包含行列数、单元格编号、位置和原文，通常一次请求完成翻译。空白和纯数字单元格由本地保留，不发送。模型返回编号到译文的映射，经校验后由程序回填原位置。首行作为表头；合并单元格会展开，复杂或无边框表格可能提取为普通文字。
- **表格异常处理**：接口明确报告输入超限、译文被截断或 JSON 校验失败时，才拆小批次，优先按整行拆分。有效的部分结果先保存，只补译缺失或类型错误的单元格。单个格子仍超限时改用正文分段翻译；无效的单格 JSON 返回会报错，不作为译文写入。跨页表格仍按每页提取出的表格分别处理，不自动合并。
- **无文字页面**：保留其中的图片；只有既无文字、也无可导出图片对象时，才保存整页预览，避免遗漏纯矢量图等内容。
- **OCR**：目前未实现，扫描页和图片内文字不会被识别或翻译。真正覆盖整页的扫描图片，仍会以整页大小保留。

## 并发与 token 开销

正文默认最多同时处理 3 个模型请求，支持在小窗口内跨页调度。分段完成的顺序可以不同，最终文件仍按原文顺序组织。表格在正文批次完成后逐表请求，普通表格不再逐格发送。

并发只改变请求调度，不改变分段大小、提示词和模型参数。在没有重试的正常情况下，不会因并发本身增加输入 token；模型输出长度仍可能波动。超时重试、服务端限流或输出截断后的重新翻译，可能带来额外开销。

若日志频繁出现 HTTP `429`，可以降低并发数：

```bash
python main.py --concurrency 2
```

当前并发参数限制的是同时在途的请求数量，不是每分钟请求量或 token 用量。实际加速效果取决于模型服务的处理能力和额度限制。

整表翻译可以减少重复携带提示词的次数，但 JSON 编号和位置信息也占 token，不保证每张表都减少总 token。表格异常拆批、补译同样可能产生额外开销。

## 缓存与中断恢复

每个成功分段会立即保存到 `output/.checkpoints/`。重新运行相同任务时会重新解析 PDF，但已缓存的译文不会重复请求模型。

表格使用包含整表内容和表格提示词的独立缓存，避免与普通正文译文混用。兼容旧版本逐格翻译留下的缓存，只请求尚未命中的内容；新生成的表格译文不会写入正文分段缓存。有效的部分表格译文也会保存，后续失败重启时可以继续补全。

缓存根据输入文件内容、模型、接口地址、提示词、分段大小和输出 token 上限区分。更换输出格式或并发数不会使缓存失效：先生成 Markdown，再生成 PDF 或 Word，可以复用已有译文。

```bash
# 翻译并保存缓存
python main.py --output-format md

# 使用相同配置和输出目录，复用缓存导出 Word
python main.py --output-format word
```

缓存位于所选输出目录内；更换输出目录后，程序不会自动查找原目录的缓存。使用 `--no-resume` 会重新请求译文，通常不需要在重新导出图片或切换格式时使用。

Markdown 按页写入 `*.partial.md`，全部成功后替换正式文件。PDF 和 Word 在内容准备完成后统一排版保存。三种格式均在完整输出成功后才替换已有结果；翻译失败时已保存的分段缓存仍可复用。

## 日志与错误处理

日志同时输出到终端和 `log/translator.log`，记录配置加载、页码、分段字符数、缓存命中、模型返回的 token 用量、重试状态、耗时及输出路径。程序不主动记录密钥、正文或完整模型接口错误响应。

日志文件达到 10 MB 时轮转，保留 7 天。日志目录可以通过 `--log-dir` 修改。

| 现象 | 建议 |
| --- | --- |
| 找不到输入文件 | 检查路径及相对路径的基准目录 |
| HTTP `401` / `403` | 检查密钥及接口权限 |
| 模型不可用或请求参数错误 | 检查服务商支持的模型名称、接口地址和 Chat Completions 兼容性 |
| HTTP `429` | 降低并发数，检查服务端限额和额度 |
| 请求超时 | 检查网络，按需调整 `timeout` 或并发数 |
| PDF 中文缺字 | 通过 `--pdf-font` 指定包含相应字符的字体 |
| Word 依赖缺失 | 在运行程序的同一 Python 环境执行 `python -m pip install -r requirements.txt` |
| 页面只有图片，没有中文译文 | 该页可能没有可提取文字，目前不支持 OCR |

连接错误、超时、HTTP `408`、`409`、`429` 和服务端 `5xx` 错误会有限重试。输出因长度限制被截断时，程序会拆小分段重新翻译，不直接保存截断内容。

进程退出码：`0` 表示完成，`1` 表示运行失败，`2` 通常表示命令行参数错误，`130` 表示用户中断。

## 工程结构

```text
.
├── main.py                         # 命令行入口
├── config.example.yaml             # 不含真实密钥的配置示例
├── requirements.txt
├── book_translator/
│   ├── config.py                   # 配置合并与检查
│   ├── models.py                   # 内容与页面数据结构
│   ├── pdf_reader.py               # 本地 PDF 提取
│   ├── translation.py              # 分段、并发、模型请求与重试
│   ├── table_translation.py        # 整表 JSON 翻译、校验、回填与异常拆批
│   ├── checkpoint.py               # 缓存持久化
│   ├── pipeline.py                 # 流程协调
│   ├── output.py                   # 导出器选择
│   ├── markdown_writer.py          # Markdown 输出
│   ├── pdf_writer.py               # PDF 输出
│   ├── word_writer.py              # Word 输出
│   ├── document_content.py         # 文本格式、图片尺寸等共用逻辑
│   └── logging_setup.py            # 日志配置
├── utils/
│   └── argument_utils.py           # 命令行参数定义
└── test/
    ├── test.pdf                    # 本地测试样例
    ├── test_translation.py         # 提取、翻译、并发、缓存等测试
    ├── test_output.py              # 格式导出测试
    └── test_table_translation.py   # 整表请求、结构校验、拆批与缓存测试
```

## 测试

```bash
python -m unittest discover -s test -p 'test_*.py' -v
```

测试使用本地样例和模拟模型响应，不调用真实模型、不消耗 API 额度。覆盖配置覆盖、图片裁切、表格提取与整表翻译、返回编号校验、表格超限拆批、并发顺序、请求去重、错误重试、断点缓存、三种格式导出及导出失败保护等行为。

## 当前限制

- 只支持 PDF 输入；Word 输出仅支持 `.docx`，不支持旧式 `.doc`。
- 不做 OCR，不翻译图片内部文字，也不单独提取矢量插图。
- 复杂多栏、跨页段落、特殊字体和复杂表格可能需要人工检查。
- 术语一致性主要由提示词约束，目前没有全书术语库或跨分段校对流程。
- PDF、Word 导出需要在内存中保留待排版内容，超长书籍可按页码范围分批处理。

## 配置与版本管理

`config.yaml`、`.env`、日志目录、默认输出目录、临时目录和虚拟环境已加入 `.gitignore`。提交配置示例时使用 `config.example.yaml`，不要将真实 API Key 写入示例文件。

如果将输出或日志改到自定义目录，需要自行补充对应的忽略规则。缓存和输出文件可能包含书籍译文，请按自己的数据管理要求保管。
