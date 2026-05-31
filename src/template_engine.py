"""
模板引擎模块

公理溯源：记忆公理 - 将知识图谱数据渲染为可读报告

设计意图：
- 简单的模板渲染（变量替换 + 条件 + 循环）
- 零外部依赖
- 支持自定义过滤器
- 支持模板继承
- 支持报告生成
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class TemplateError(Exception):
    """模板引擎异常"""
    pass


class TemplateSyntaxError(TemplateError):
    """模板语法异常"""
    pass


class Template:
    """
    模板类

    语法：
    - {{ variable }} — 变量替换
    - {{ variable|filter }} — 带过滤器的变量
    - {% if condition %}...{% endif %} — 条件
    - {% for item in list %}...{% endfor %} — 循环
    - {% include "path" %} — 包含子模板
    - {# comment #} — 注释
    """

    # 正则模式
    VAR_PATTERN = re.compile(r'\{\{\s*(.+?)\s*\}\}')
    BLOCK_PATTERN = re.compile(r'\{%\s*(.+?)\s*%\}')
    COMMENT_PATTERN = re.compile(r'\{#.+?#\}', re.DOTALL)

    def __init__(self, template_str: str, template_dir: Optional[Path] = None):
        self._template = template_str
        self._template_dir = template_dir
        self._filters: Dict[str, Callable] = {
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "strip": lambda x: str(x).strip(),
            "length": lambda x: len(x) if hasattr(x, '__len__') else 0,
            "default": lambda x, d="": x if x else d,
            "first": lambda x: x[0] if x and hasattr(x, '__getitem__') else "",
            "last": lambda x: x[-1] if x and hasattr(x, '__getitem__') else "",
            "join": lambda x, sep=",": sep.join(str(i) for i in x) if x else "",
            "round": lambda x, n=2: round(float(x), int(n)) if x else 0,
            "date": lambda x, fmt="%Y-%m-%d": datetime.fromisoformat(str(x)).strftime(fmt) if x else "",
            "count": lambda x: len(x) if hasattr(x, '__len__') else 0,
            "yesno": lambda x: "是" if x else "否",
            "truncate": lambda x, n=50: str(x)[:int(n)] + "..." if len(str(x)) > int(n) else str(x),
        }

    def render(self, context: Dict[str, Any]) -> str:
        """
        渲染模板

        Args:
            context: 变量上下文

        Returns:
            渲染后的字符串
        """
        result = self._template

        # 移除注释
        result = self.COMMENT_PATTERN.sub('', result)

        # 处理包含
        result = self._process_includes(result)

        # 处理循环
        result = self._process_loops(result, context)

        # 处理条件
        result = self._process_conditions(result, context)

        # 处理变量
        result = self._process_variables(result, context)

        return result

    def add_filter(self, name: str, fn: Callable) -> None:
        """添加自定义过滤器"""
        self._filters[name] = fn

    def _process_includes(self, template: str) -> str:
        """处理包含指令"""
        def replace_include(match):
            path_str = match.group(1).strip().strip('"').strip("'")
            if self._template_dir:
                include_path = self._template_dir / path_str
                if include_path.exists():
                    return include_path.read_text(encoding='utf-8')
            return ""

        return self.BLOCK_PATTERN.sub(
            lambda m: replace_include(m) if m.group(1).strip().startswith('include') else m.group(0),
            template
        )

    def _process_loops(self, template: str, context: Dict[str, Any]) -> str:
        """处理for循环"""
        # 找到 {% for ... %} ... {% endfor %} 块
        pattern = re.compile(
            r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}',
            re.DOTALL
        )

        def replace_loop(match):
            var_name = match.group(1)
            list_name = match.group(2)
            body = match.group(3)

            items = context.get(list_name, [])
            if not items:
                return ""

            parts = []
            for i, item in enumerate(items):
                loop_context = dict(context)
                loop_context[var_name] = item
                loop_context['loop'] = {
                    'index': i,
                    'index1': i + 1,
                    'first': i == 0,
                    'last': i == len(items) - 1,
                    'length': len(items),
                }
                # 递归处理循环体中的变量
                rendered = self._process_variables(body, loop_context)
                rendered = self._process_conditions(rendered, loop_context)
                parts.append(rendered)

            return ''.join(parts)

        # 多层循环支持：反复处理直到没有for块
        prev = None
        while prev != template:
            prev = template
            template = pattern.sub(replace_loop, template)

        return template

    def _process_conditions(self, template: str, context: Dict[str, Any]) -> str:
        """处理if条件"""
        pattern = re.compile(
            r'\{%\s*if\s+(.+?)\s*%\}(.*?)(?:\{%\s*else\s*%\}(.*?))?\{%\s*endif\s*%\}',
            re.DOTALL
        )

        def replace_condition(match):
            condition = match.group(1).strip()
            true_body = match.group(2)
            false_body = match.group(3) or ""

            if self._evaluate_condition(condition, context):
                return true_body
            return false_body

        # 多层条件支持
        prev = None
        while prev != template:
            prev = template
            template = pattern.sub(replace_condition, template)

        return template

    def _evaluate_comparison(self, condition: str, context: Dict[str, Any]) -> Optional[bool]:
        """评估比较表达式（辅助方法）"""
        for op in ["==", "!=", ">=", "<=", ">", "<"]:
            if op in condition:
                parts = condition.split(op, 1)
                left = self._resolve_value(parts[0].strip(), context)
                right = self._resolve_value(parts[1].strip(), context)
                if op == "==":
                    return left == right
                elif op == "!=":
                    return left != right
                elif op == ">":
                    return left > right
                elif op == "<":
                    return left < right
                elif op == ">=":
                    return left >= right
                elif op == "<=":
                    return left <= right
        return None

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        condition = condition.strip()

        # not
        if condition.startswith("not "):
            return not self._evaluate_condition(condition[4:], context)

        # and / or
        for op in [" and ", " or "]:
            if op in condition:
                parts = condition.split(op, 1)
                left = self._evaluate_condition(parts[0], context)
                right = self._evaluate_condition(parts[1], context)
                if op == " and ":
                    return left and right
                return left or right

        # 比较运算符
        result = self._evaluate_comparison(condition, context)
        if result is not None:
            return result

        # 简单变量真值
        value = self._resolve_value(condition, context)
        return bool(value)

    def _resolve_value(self, expr: str, context: Dict[str, Any]) -> Any:
        """解析值表达式"""
        expr = expr.strip()

        # 字符串字面量
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # 数字
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # 布尔
        if expr == "True":
            return True
        if expr == "False":
            return False
        if expr == "None":
            return None

        # 变量（支持点号访问）
        return self._resolve_variable(expr, context)

    def _resolve_variable(self, var_path: str, context: Dict[str, Any]) -> Any:
        """解析变量路径（支持 a.b.c）"""
        parts = var_path.split('.')
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
            if value is None:
                return None
        return value

    def _process_variables(self, template: str, context: Dict[str, Any]) -> str:
        """处理变量替换"""
        def replace_var(match):
            expr = match.group(1).strip()

            # 检查是否有过滤器
            if '|' in expr:
                var_part, filter_part = expr.split('|', 1)
                var_name = var_part.strip()
                filter_expr = filter_part.strip()

                value = self._resolve_variable(var_name, context)
                return str(self._apply_filter(value, filter_expr))
            else:
                value = self._resolve_variable(expr, context)
                if value is None:
                    return ""
                return str(value)

        return self.VAR_PATTERN.sub(replace_var, template)

    def _apply_filter(self, value: Any, filter_expr: str) -> Any:
        """应用过滤器"""
        # 解析过滤器参数
        parts = filter_expr.split(':')
        filter_name = parts[0].strip()
        args = [p.strip().strip('"').strip("'") for p in parts[1:]] if len(parts) > 1 else []

        if filter_name not in self._filters:
            return value

        fn = self._filters[filter_name]
        try:
            if args:
                return fn(value, *args)
            return fn(value)
        except Exception:
            return value


class TemplateEngine:
    """
    模板引擎

    职责：
    - 管理模板目录
    - 加载和缓存模板
    - 渲染报告
    """

    def __init__(self, template_dir: Optional[Path] = None):
        self._template_dir = Path(template_dir) if template_dir else None
        self._cache: Dict[str, Template] = {}
        self._global_context: Dict[str, Any] = {}
        self._reports: List[Dict[str, Any]] = []

    def add_global(self, name: str, value: Any) -> None:
        """添加全局变量"""
        self._global_context[name] = value

    def load_template(self, name: str) -> Template:
        """加载模板"""
        if name in self._cache:
            return self._cache[name]

        if self._template_dir:
            template_path = self._template_dir / name
            if template_path.exists():
                content = template_path.read_text(encoding='utf-8')
                template = Template(content, self._template_dir)
                self._cache[name] = template
                return template

        raise TemplateError(f"模板 '{name}' 未找到")

    def render_string(self, template_str: str, context: Optional[Dict[str, Any]] = None) -> str:
        """渲染字符串模板"""
        full_context = dict(self._global_context)
        full_context.update(context or {})
        template = Template(template_str, self._template_dir)
        return template.render(full_context)

    def render(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """渲染命名模板"""
        template = self.load_template(template_name)
        full_context = dict(self._global_context)
        full_context.update(context or {})
        return template.render(full_context)

    def render_report(
        self,
        title: str,
        sections: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        渲染报告

        Args:
            title: 报告标题
            sections: 报告章节 [{"title": "...", "content": "..."}]
            context: 模板上下文
        """
        full_context = dict(self._global_context)
        full_context.update(context or {})
        full_context["title"] = title
        full_context["sections"] = sections
        full_context["generated_at"] = datetime.now().isoformat()

        report_template = """# {{ title }}

> 生成时间: {{ generated_at }}

{% for section in sections %}
## {{ section.title }}

{{ section.content }}

{% endfor %}
---
*由永动知识图谱Agent自动生成*
"""
        template = Template(report_template, self._template_dir)
        result = template.render(full_context)

        self._reports.append({
            "title": title,
            "generated_at": full_context["generated_at"],
            "sections_count": len(sections),
        })

        return result

    def clear_cache(self) -> None:
        """清空模板缓存"""
        self._cache.clear()
