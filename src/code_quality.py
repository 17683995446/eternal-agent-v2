"""
代码质量检查模块 — 项目收尾层

公理溯源：存续公理 - 高质量代码确保系统长期可维护

设计意图：
- 静态代码分析
- 编码规范检查
- 复杂度分析
- 依赖检查
- 零外部依赖
"""

import ast
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from logger import get_logger
from constants import ENCODING

logger = get_logger("CodeQuality")


class Severity(Enum):
    """严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Issue:
    """代码问题"""
    file: str
    line: int
    column: int
    severity: Severity
    rule: str
    message: str


@dataclass
class QualityReport:
    """质量报告"""
    files_checked: int = 0
    total_lines: int = 0
    issues: List[Issue] = field(default_factory=list)
    complexity: Dict[str, int] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
    
    @property
    def issue_count(self) -> int:
        return len(self.issues)
    
    @property
    def error_count(self) -> int:
        return len([i for i in self.issues if i.severity in (Severity.ERROR, Severity.CRITICAL)])
    
    @property
    def warning_count(self) -> int:
        return len([i for i in self.issues if i.severity == Severity.WARNING])


class CodeQualityChecker:
    """
    代码质量检查器
    
    静态分析Python源码
    """
    
    def __init__(self, src_dir: Path):
        self.src_dir = Path(src_dir)
        self.rules = {
            "naming": self._check_naming,
            "complexity": self._check_complexity,
            "docstring": self._check_docstrings,
            "imports": self._check_imports,
            "lines": self._check_line_length,
        }
    
    def check(self, file_patterns: List[str] = None) -> QualityReport:
        """
        执行代码质量检查
        
        Args:
            file_patterns: 文件匹配模式
            
        Returns:
            质量报告
        """
        report = QualityReport()
        
        if file_patterns is None:
            file_patterns = ["*.py"]
        
        # 收集文件
        files = []
        for pattern in file_patterns:
            files.extend(self.src_dir.glob(pattern))
        
        # 检查每个文件
        for file_path in sorted(files):
            file_issues = self._check_file(file_path)
            report.issues.extend(file_issues)
            report.files_checked += 1
            
            # 统计行数
            try:
                with open(file_path, 'r', encoding=ENCODING) as f:
                    lines = f.readlines()
                    report.total_lines += len(lines)
            except Exception:
                pass
        
        # 计算分数
        report.scores = self._calculate_scores(report)
        
        return report
    
    def _check_file(self, file_path: Path) -> List[Issue]:
        """检查单个文件"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding=ENCODING) as f:
                source = f.read()
                lines = source.split('\n')
        except Exception as e:
            issues.append(Issue(
                file=str(file_path.name),
                line=0, column=0,
                severity=Severity.ERROR,
                rule="readability",
                message=f"无法读取文件: {e}"
            ))
            return issues
        
        # 应用所有规则
        for rule_name, rule_func in self.rules.items():
            try:
                rule_issues = rule_func(file_path.name, source, lines)
                issues.extend(rule_issues)
            except Exception as e:
                logger.warning(f"规则 {rule_name} 执行失败: {e}")
        
        return issues
    
    def _check_naming(self, filename: str, source: str, lines: List[str]) -> List[Issue]:
        """检查命名规范"""
        issues = []
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        
        for node in ast.walk(tree):
            # 检查类名（PascalCase）
            if isinstance(node, ast.ClassDef):
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                    issues.append(Issue(
                        file=filename, line=node.lineno, column=0,
                        severity=Severity.WARNING,
                        rule="naming",
                        message=f"类名 '{node.name}' 应使用PascalCase"
                    ))
            
            # 检查函数名（snake_case）
            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_') and not re.match(r'^[a-z][a-z0-9_]*$', node.name):
                    issues.append(Issue(
                        file=filename, line=node.lineno, column=0,
                        severity=Severity.WARNING,
                        rule="naming",
                        message=f"函数名 '{node.name}' 应使用snake_case"
                    ))
        
        return issues
    
    def _check_complexity(self, filename: str, source: str, lines: List[str]) -> List[Issue]:
        """检查复杂度"""
        issues = []
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                
                if complexity > 15:
                    issues.append(Issue(
                        file=filename, line=node.lineno, column=0,
                        severity=Severity.ERROR,
                        rule="complexity",
                        message=f"函数 '{node.name}' 圈复杂度过高: {complexity} (建议<15)"
                    ))
                elif complexity > 10:
                    issues.append(Issue(
                        file=filename, line=node.lineno, column=0,
                        severity=Severity.WARNING,
                        rule="complexity",
                        message=f"函数 '{node.name}' 圈复杂度较高: {complexity}"
                    ))
        
        return issues
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """计算圈复杂度"""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                if child.ifs:
                    complexity += len(child.ifs)
        
        return complexity
    
    def _check_docstrings(self, filename: str, source: str, lines: List[str]) -> List[Issue]:
        """检查文档字符串"""
        issues = []
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node)
                if not docstring:
                    issues.append(Issue(
                        file=filename, line=node.lineno, column=0,
                        severity=Severity.INFO,
                        rule="docstring",
                        message=f"类 '{node.name}' 缺少文档字符串"
                    ))
            
            elif isinstance(node, ast.FunctionDef):
                # 跳过私有方法和特殊方法
                if node.name.startswith('_'):
                    continue
                
                docstring = ast.get_docstring(node)
                if not docstring:
                    issues.append(Issue(
                        file=filename, line=node.lineno, column=0,
                        severity=Severity.INFO,
                        rule="docstring",
                        message=f"函数 '{node.name}' 缺少文档字符串"
                    ))
        
        return issues
    
    def _check_imports(self, filename: str, source: str, lines: List[str]) -> List[Issue]:
        """检查导入"""
        issues = []
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return issues
        
        imported = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name in imported:
                        issues.append(Issue(
                            file=filename, line=node.lineno, column=0,
                            severity=Severity.WARNING,
                            rule="imports",
                            message=f"重复导入: {name}"
                        ))
                    imported.add(name)
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}"
                    if full_name in imported:
                        issues.append(Issue(
                            file=filename, line=node.lineno, column=0,
                            severity=Severity.WARNING,
                            rule="imports",
                            message=f"重复导入: {full_name}"
                        ))
                    imported.add(full_name)
        
        return issues
    
    def _check_line_length(self, filename: str, source: str, lines: List[str]) -> List[Issue]:
        """检查行长度"""
        issues = []
        max_length = 120
        
        for i, line in enumerate(lines, 1):
            # 跳过注释和文档字符串中的长行
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            
            if len(line) > max_length:
                issues.append(Issue(
                    file=filename, line=i, column=max_length,
                    severity=Severity.INFO,
                    rule="line_length",
                    message=f"行过长: {len(line)} 字符 (建议<{max_length})"
                ))
        
        return issues
    
    def _calculate_scores(self, report: QualityReport) -> Dict[str, float]:
        """计算质量分数"""
        if report.files_checked == 0:
            return {"overall": 0}
        
        # 基础分100，每个问题扣分
        deductions = {
            Severity.CRITICAL: 10,
            Severity.ERROR: 5,
            Severity.WARNING: 2,
            Severity.INFO: 0.5,
        }
        
        total_deduction = sum(
            deductions.get(issue.severity, 0) for issue in report.issues
        )
        
        # 按文件数归一化
        normalized_deduction = total_deduction / max(1, report.files_checked)
        
        overall = max(0, 100 - normalized_deduction)
        
        return {
            "overall": round(overall, 1),
            "files": report.files_checked,
            "lines": report.total_lines,
            "issues_per_file": round(len(report.issues) / max(1, report.files_checked), 1)
        }
    
    def generate_report_text(self, report: QualityReport) -> str:
        """生成文本报告"""
        lines = [
            "=" * 60,
            "代码质量报告",
            "=" * 60,
            "",
            f"检查文件: {report.files_checked}",
            f"总行数: {report.total_lines}",
            f"问题总数: {report.issue_count}",
            f"  错误: {report.error_count}",
            f"  警告: {report.warning_count}",
            f"质量分数: {report.scores.get('overall', 0)}/100",
            "",
        ]
        
        # 按文件分组
        by_file = defaultdict(list)
        for issue in report.issues:
            by_file[issue.file].append(issue)
        
        for filename, file_issues in sorted(by_file.items()):
            lines.append(f"--- {filename} ({len(file_issues)} 个问题) ---")
            for issue in file_issues[:10]:  # 每个文件最多显示10个
                icon = {"CRITICAL": "🔥", "ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}.get(
                    issue.severity.value, "•"
                )
                lines.append(f"  {icon} L{issue.line}: [{issue.rule}] {issue.message}")
            if len(file_issues) > 10:
                lines.append(f"  ... 还有 {len(file_issues) - 10} 个问题")
            lines.append("")
        
        return "\n".join(lines)


def check_code_quality(src_dir: str = "src") -> QualityReport:
    """检查代码质量（便捷函数）"""
    checker = CodeQualityChecker(Path(src_dir))
    return checker.check()
