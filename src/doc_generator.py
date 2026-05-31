"""
文档生成器模块 — 文档与示例层

公理溯源：记忆公理 - 知识需要被记录、传播和复用

设计意图：
- 自动生成Markdown/HTML格式的项目文档
- 从代码中提取文档字符串生成API文档
- 生成架构图和模块依赖图
- 零外部依赖，仅使用Python标准库

大事做于细，难事成于易：
- 模块化设计，每种文档类型独立生成器
- 模板驱动，易于定制和扩展
- 渐进式生成，支持增量更新
"""

import ast
import inspect
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from logger import get_logger
from utils import now_iso, ensure_dir
from constants import PROJECT_ROOT, ENCODING

logger = get_logger("DocGenerator")


class DocFormat(Enum):
    """文档格式"""
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


@dataclass
class ModuleDoc:
    """模块文档信息"""
    name: str
    docstring: str
    classes: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    constants: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ClassDoc:
    """类文档信息"""
    name: str
    docstring: str
    methods: List[Dict[str, Any]] = field(default_factory=list)
    attributes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FunctionDoc:
    """函数文档信息"""
    name: str
    docstring: str
    signature: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    returns: Optional[str] = None


class DocGenerator:
    """
    文档生成器
    
    核心能力：
    - 解析Python源码提取文档
    - 生成多种格式文档（Markdown/HTML/JSON）
    - 生成模块依赖图
    - 生成API参考文档
    """
    
    def __init__(self, src_dir: Path, output_dir: Path):
        self.src_dir = Path(src_dir)
        self.output_dir = Path(output_dir)
        self.modules: List[ModuleDoc] = []
        
    def scan_modules(self) -> List[ModuleDoc]:
        """
        扫描所有模块并提取文档信息
        
        Returns:
            模块文档列表
        """
        self.modules = []
        
        for py_file in self.src_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
                
            try:
                module_doc = self._parse_module(py_file)
                if module_doc:
                    self.modules.append(module_doc)
                    logger.debug(f"已解析模块: {module_doc.name}")
            except Exception as e:
                logger.warning(f"解析模块失败 {py_file}: {e}")
                
        logger.info(f"共扫描 {len(self.modules)} 个模块")
        return self.modules
    
    def _parse_module(self, file_path: Path) -> Optional[ModuleDoc]:
        """解析单个模块文件"""
        try:
            with open(file_path, 'r', encoding=ENCODING) as f:
                source = f.read()
                
            tree = ast.parse(source)
            
            module_name = file_path.stem
            module_docstring = ast.get_docstring(tree) or ""
            
            module_doc = ModuleDoc(
                name=module_name,
                docstring=module_docstring
            )
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = self._parse_class(node)
                    module_doc.classes.append(class_info)
                elif isinstance(node, ast.FunctionDef):
                    func_info = self._parse_function(node)
                    module_doc.functions.append(func_info)
                elif isinstance(node, ast.Assign):
                    const_info = self._parse_constant(node)
                    if const_info:
                        module_doc.constants.append(const_info)
                        
            return module_doc
            
        except SyntaxError as e:
            logger.warning(f"语法错误 {file_path}: {e}")
            return None
    
    def _parse_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        """解析类定义"""
        docstring = ast.get_docstring(node) or ""
        
        methods = []
        attributes = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if not item.name.startswith('_') or item.name == '__init__':
                    methods.append(self._parse_function(item))
            elif isinstance(item, ast.AnnAssign):
                attr_name = item.target.id if isinstance(item.target, ast.Name) else str(item.target)
                attributes.append({
                    "name": attr_name,
                    "annotation": ast.unparse(item.annotation) if item.annotation else None
                })
        
        bases = [ast.unparse(base) for base in node.bases]
        
        return {
            "name": node.name,
            "docstring": docstring,
            "methods": methods,
            "attributes": attributes,
            "bases": bases,
            "line_number": node.lineno
        }
    
    def _parse_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """解析函数定义"""
        docstring = ast.get_docstring(node) or ""
        
        # 构建签名
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        
        # 处理默认参数
        defaults_start = len(args) - len(node.args.defaults)
        for i, default in enumerate(node.args.defaults):
            args[defaults_start + i] += f" = {ast.unparse(default)}"
        
        signature = f"{node.name}({', '.join(args)})"
        
        # 返回值
        returns = ast.unparse(node.returns) if node.returns else None
        if returns:
            signature += f" -> {returns}"
        
        # 参数详细信息
        parameters = []
        for arg in node.args.args:
            if arg.arg != 'self':
                param_info = {
                    "name": arg.arg,
                    "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
                    "default": None
                }
                parameters.append(param_info)
        
        return {
            "name": node.name,
            "docstring": docstring,
            "signature": signature,
            "parameters": parameters,
            "returns": returns,
            "line_number": node.lineno
        }
    
    def _parse_constant(self, node: ast.Assign) -> Optional[Dict[str, Any]]:
        """解析常量定义"""
        if len(node.targets) != 1:
            return None
            
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return None
            
        # 只处理全大写的常量
        if not target.id.isupper():
            return None
            
        try:
            value = ast.literal_eval(node.value)
            return {
                "name": target.id,
                "value": value,
                "line_number": node.lineno
            }
        except (ValueError, SyntaxError):
            return None
    
    def generate_api_docs(self, format: DocFormat = DocFormat.MARKDOWN) -> Path:
        """
        生成API参考文档
        
        Args:
            format: 文档格式
            
        Returns:
            生成的文档路径
        """
        if not self.modules:
            self.scan_modules()
            
        output_file = self.output_dir / f"api_reference.{format.value}"
        ensure_dir(self.output_dir)
        
        if format == DocFormat.MARKDOWN:
            content = self._generate_markdown_api()
        elif format == DocFormat.HTML:
            content = self._generate_html_api()
        else:
            content = self._generate_json_api()
            
        with open(output_file, 'w', encoding=ENCODING) as f:
            f.write(content)
            
        logger.info(f"API文档已生成: {output_file}")
        return output_file
    
    def _generate_markdown_api(self) -> str:
        """生成Markdown格式的API文档"""
        lines = [
            "# API 参考文档",
            "",
            f"> 自动生成于 {now_iso()}",
            "",
            "## 目录",
            "",
        ]
        
        # 生成目录
        for module in self.modules:
            lines.append(f"- [{module.name}](#{module.name})")
        
        lines.append("")
        
        # 生成详细内容
        for module in self.modules:
            lines.extend(self._generate_module_markdown(module))
            
        return "\n".join(lines)
    
    def _generate_module_markdown(self, module: ModuleDoc) -> List[str]:
        """生成单个模块的Markdown文档"""
        lines = [
            f"## {module.name}",
            "",
        ]
        
        if module.docstring:
            lines.append(module.docstring)
            lines.append("")
        
        # 常量
        if module.constants:
            lines.append("### 常量")
            lines.append("")
            for const in module.constants:
                value_str = json.dumps(const['value'], ensure_ascii=False)
                lines.append(f"- **{const['name']}**: `{value_str}`")
            lines.append("")
        
        # 类
        if module.classes:
            lines.append("### 类")
            lines.append("")
            for cls in module.classes:
                lines.extend(self._generate_class_markdown(cls))
        
        # 函数
        if module.functions:
            lines.append("### 函数")
            lines.append("")
            for func in module.functions:
                lines.extend(self._generate_function_markdown(func))
                
        return lines
    
    def _generate_class_markdown(self, cls: Dict[str, Any]) -> List[str]:
        """生成类的Markdown文档"""
        lines = [
            f"#### {cls['name']}",
            "",
        ]
        
        if cls['docstring']:
            lines.append(cls['docstring'])
            lines.append("")
        
        if cls['bases']:
            lines.append(f"**继承**: {', '.join(cls['bases'])}")
            lines.append("")
        
        # 方法
        if cls['methods']:
            lines.append("**方法**:")
            lines.append("")
            for method in cls['methods']:
                lines.append(f"- `{method['signature']}`")
                if method['docstring']:
                    # 提取第一行作为简介
                    brief = method['docstring'].split('\n')[0]
                    lines.append(f"  - {brief}")
            lines.append("")
        
        return lines
    
    def _generate_function_markdown(self, func: Dict[str, Any]) -> List[str]:
        """生成函数的Markdown文档"""
        lines = [
            f"#### {func['name']}",
            "",
            f"```python\n{func['signature']}\n```",
            "",
        ]
        
        if func['docstring']:
            lines.append(func['docstring'])
            lines.append("")
        
        return lines
    
    def _generate_html_api(self) -> str:
        """生成HTML格式的API文档"""
        lines = [
            "<!DOCTYPE html>",
            "<html lang=\"zh-CN\">",
            "<head>",
            "    <meta charset=\"UTF-8\">",
            "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
            "    <title>API 参考文档</title>",
            "    <style>",
            "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; line-height: 1.6; }",
            "        h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }",
            "        h2 { color: #444; margin-top: 30px; }",
            "        h3 { color: #555; }",
            "        h4 { color: #666; }",
            "        pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }",
            "        code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: 'Consolas', monospace; }",
            "        .docstring { color: #666; font-style: italic; }",
            "        .toc { background: #f9f9f9; padding: 15px; border-radius: 5px; }",
            "        .toc a { text-decoration: none; color: #0066cc; }",
            "        .toc a:hover { text-decoration: underline; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>API 参考文档</h1>",
            f"    <p class=\"docstring\">自动生成于 {now_iso()}</p>",
            "    <div class=\"toc\">",
            "        <h2>目录</h2>",
            "        <ul>",
        ]
        
        for module in self.modules:
            lines.append(f'            <li><a href="#{module.name}">{module.name}</a></li>')
        
        lines.extend([
            "        </ul>",
            "    </div>",
        ])
        
        for module in self.modules:
            lines.extend(self._generate_module_html(module))
        
        lines.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(lines)
    
    def _generate_module_html(self, module: ModuleDoc) -> List[str]:
        """生成单个模块的HTML文档"""
        lines = [
            f'    <h2 id="{module.name}">{module.name}</h2>',
        ]
        
        if module.docstring:
            lines.append(f'    <p class="docstring">{module.docstring.replace(chr(10), "<br>")}</p>')
        
        if module.classes:
            lines.append("    <h3>类</h3>")
            for cls in module.classes:
                lines.append(f'    <h4>{cls["name"]}</h4>')
                if cls['docstring']:
                    lines.append(f'    <p class="docstring">{cls["docstring"].replace(chr(10), "<br>")}</p>')
        
        if module.functions:
            lines.append("    <h3>函数</h3>")
            for func in module.functions:
                lines.append(f'    <h4>{func["name"]}</h4>')
                lines.append(f'    <pre><code>{func["signature"]}</code></pre>')
                if func['docstring']:
                    lines.append(f'    <p class="docstring">{func["docstring"].replace(chr(10), "<br>")}</p>')
        
        return lines
    
    def _generate_json_api(self) -> str:
        """生成JSON格式的API文档"""
        data = {
            "generated_at": now_iso(),
            "modules": [
                {
                    "name": m.name,
                    "docstring": m.docstring,
                    "classes": m.classes,
                    "functions": m.functions,
                    "constants": m.constants
                }
                for m in self.modules
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def generate_architecture_doc(self) -> Path:
        """
        生成架构文档
        
        Returns:
            生成的文档路径
        """
        output_file = self.output_dir / "architecture.md"
        ensure_dir(self.output_dir)
        
        lines = [
            "# 系统架构文档",
            "",
            f"> 自动生成于 {now_iso()}",
            "",
            "## 概述",
            "",
            "永动知识图谱Agent采用分层架构设计，遵循三个核心公理：",
            "",
            "1. **存续公理 (Alive)** - 系统永不终止，具备自修复能力",
            "2. **记忆公理 (Memory)** - 知识图谱是唯一长期记忆载体",
            "3. **自驱公理 (Self-Drive)** - 从知识自动衍生任务",
            "",
            "## 架构层次",
            "",
            "```",
            "┌─────────────────────────────────────────────────────────────┐",
            "│                    集成层 (Integration)                      │",
            "│     Boot │ Visualization │ Query │ Benchmark │ Upgrader      │",
            "├─────────────────────────────────────────────────────────────┤",
            "│                    生产层 (Production)                       │",
            "│  Config │ Secrets │ Access │ Audit │ Encryption │ Backup     │",
            "├─────────────────────────────────────────────────────────────┤",
            "│                    生态层 (Ecosystem)                        │",
            "│  Plugin │ EventBus │ Watcher │ Scheduler │ HTTP │ Pipeline  │",
            "├─────────────────────────────────────────────────────────────┤",
            "│                    交互层 (Interaction)                      │",
            "│                    API │ CLI │ Protocol                      │",
            "├─────────────────────────────────────────────────────────────┤",
            "│                    推理层 (Reasoning)                        │",
            "│        Rules │ Patterns │ Causal │ Similarity │ Inference   │",
            "├─────────────────────────────────────────────────────────────┤",
            "│                    自驱层 (Self-Drive)                       │",
            "│                    EternalAgent (智能体核心)                  │",
            "├─────────────────────────────────────────────────────────────┤",
            "│                    记忆层 (Memory)                           │",
            "│                    KnowledgeGraph (知识图谱)                  │",
            "├─────────────────────────────────────────────────────────────┤",
            "│                    存续层 (Survival)                         │",
            "│                    TaskQueue │ EternalLoop                   │",
            "├─────────────────────────────────────────────────────────────┤",
            "│                    基础层 (Base)                             │",
            "│  Constants │ Logger │ Config │ Models │ Utils │ Exceptions   │",
            "└─────────────────────────────────────────────────────────────┘",
            "```",
            "",
            "## 模块统计",
            "",
        ]
        
        if not self.modules:
            self.scan_modules()
        
        total_classes = sum(len(m.classes) for m in self.modules)
        total_functions = sum(len(m.functions) for m in self.modules)
        total_constants = sum(len(m.constants) for m in self.modules)
        
        lines.extend([
            f"- **模块数**: {len(self.modules)}",
            f"- **类数**: {total_classes}",
            f"- **函数数**: {total_functions}",
            f"- **常数数**: {total_constants}",
            "",
            "## 模块列表",
            "",
        ])
        
        for module in sorted(self.modules, key=lambda m: m.name):
            lines.append(f"### {module.name}")
            lines.append("")
            if module.docstring:
                # 只取第一行
                brief = module.docstring.split('\n')[0]
                lines.append(brief)
                lines.append("")
            lines.append(f"- 类: {len(module.classes)} | 函数: {len(module.functions)} | 常量: {len(module.constants)}")
            lines.append("")
        
        content = "\n".join(lines)
        
        with open(output_file, 'w', encoding=ENCODING) as f:
            f.write(content)
            
        logger.info(f"架构文档已生成: {output_file}")
        return output_file
    
    def generate_all(self) -> Dict[str, Path]:
        """
        生成所有文档
        
        Returns:
            生成的文档路径字典
        """
        results = {}
        
        results['api_markdown'] = self.generate_api_docs(DocFormat.MARKDOWN)
        results['api_html'] = self.generate_api_docs(DocFormat.HTML)
        results['architecture'] = self.generate_architecture_doc()
        
        logger.info(f"所有文档生成完成，共 {len(results)} 个文件")
        return results


class QuickStartGenerator:
    """快速开始指南生成器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
    
    def generate(self) -> Path:
        """生成快速开始指南"""
        output_file = self.output_dir / "quickstart.md"
        ensure_dir(self.output_dir)
        
        content = """# 快速开始指南

## 安装

无需安装，永动知识图谱Agent是纯Python实现，零外部依赖。

```bash
# 克隆或下载项目
cd eternal_agent/src

# 直接运行
python eternal_agent.py
```

## 基础用法

### 1. 创建知识图谱

```python
from knowledge_graph import KnowledgeGraph

# 创建实例
kg = KnowledgeGraph()

# 添加节点
kg.add_node("Python", "technology")
kg.add_node("AI", "concept")

# 添加关系
kg.add_edge("Python", "AI", "powers", 0.9)

# 保存
kg.save()
```

### 2. 启动永动循环

```python
from eternal_agent import EternalAgent

# 创建智能体
agent = EternalAgent()

# 定义任务处理器
def my_task_handler(task):
    print(f"处理任务: {task.name}")
    return True

# 启动
agent.start(on_task=my_task_handler)
```

### 3. 使用查询语言

```python
from query_language import QueryEngine
from knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()
engine = QueryEngine(kg)

# 查询节点
result = engine.execute("FIND nodes WHERE type = 'technology'")
print(result.data)

# 统计
result = engine.execute("COUNT edges")
print(f"边数: {result.data}")
```

## 下一步

- 查看 [API参考文档](api_reference.md)
- 阅读 [架构文档](architecture.md)
- 探索 [示例项目](../examples/)
"""
        
        with open(output_file, 'w', encoding=ENCODING) as f:
            f.write(content)
            
        logger.info(f"快速开始指南已生成: {output_file}")
        return output_file


# 全局生成器实例
_default_generator: Optional[DocGenerator] = None


def get_doc_generator(src_dir: Optional[Path] = None, 
                      output_dir: Optional[Path] = None) -> DocGenerator:
    """获取文档生成器实例"""
    global _default_generator
    
    if _default_generator is None:
        if src_dir is None:
            src_dir = PROJECT_ROOT / "src"
        if output_dir is None:
            output_dir = PROJECT_ROOT / "docs"
        _default_generator = DocGenerator(src_dir, output_dir)
        
    return _default_generator
