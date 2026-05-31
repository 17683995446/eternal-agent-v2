"""
数据管道模块

公理溯源：记忆公理 - ETL管道将外部数据转化为结构化知识

设计意图：
- Extract-Transform-Load 框架
- 支持多种数据源（文件、字典列表、API）
- 支持多种数据转换（过滤、映射、聚合、排序）
- 管道可组合
- 零外部依赖
"""

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from exceptions import EternalAgentError


class PipelineError(EternalAgentError):
    """数据管道异常"""
    pass


class ExtractError(PipelineError):
    """数据提取异常"""
    pass


class TransformError(PipelineError):
    """数据转换异常"""
    pass


class LoadError(PipelineError):
    """数据加载异常"""
    pass


# ============================================================
# 数据源
# ============================================================

class DataSource:
    """数据源基类"""
    def extract(self) -> List[Dict[str, Any]]:
        """提取数据
        
        Returns:
            List[Dict[str, Any]]: 提取的数据记录列表
        """
        raise NotImplementedError


class DictListSource(DataSource):
    """字典列表数据源"""
    def __init__(self, data: List[Dict[str, Any]]):
        self._data = data

    def extract(self) -> List[Dict[str, Any]]:
        """提取数据
        
        Returns:
            List[Dict[str, Any]]: 数据的副本
        """
        return list(self._data)


class JSONFileSource(DataSource):
    """JSON文件数据源"""
    def __init__(self, file_path: Path):
        self._file_path = Path(file_path)

    def extract(self) -> List[Dict[str, Any]]:
        """从JSON文件提取数据
        
        Returns:
            List[Dict[str, Any]]: JSON数据作为记录列表
            
        Raises:
            ExtractError: 文件不存在或JSON解析失败
        """
        if not self._file_path.exists():
            raise ExtractError(f"文件不存在: {self._file_path}")
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            return []
        except json.JSONDecodeError as e:
            raise ExtractError(f"JSON解析失败: {e}", cause=e)


class CSVFileSource(DataSource):
    """CSV文件数据源"""
    def __init__(self, file_path: Path, encoding: str = "utf-8", delimiter: str = ","):
        self._file_path = Path(file_path)
        self._encoding = encoding
        self._delimiter = delimiter

    def extract(self) -> List[Dict[str, Any]]:
        """从CSV文件提取数据
        
        Returns:
            List[Dict[str, Any]]: CSV行作为字典列表
            
        Raises:
            ExtractError: 文件不存在或读取失败
        """
        if not self._file_path.exists():
            raise ExtractError(f"文件不存在: {self._file_path}")
        try:
            with open(self._file_path, 'r', encoding=self._encoding) as f:
                reader = csv.DictReader(f, delimiter=self._delimiter)
                return list(reader)
        except Exception as e:
            raise ExtractError(f"CSV读取失败: {e}", cause=e)


class TextFileSource(DataSource):
    """文本文件数据源（按行提取）"""
    def __init__(self, file_path: Path, line_parser: Optional[Callable[[str], Dict[str, Any]]] = None):
        self._file_path = Path(file_path)
        self._line_parser = line_parser or (lambda line: {"line": line, "line_number": 0})

    def extract(self) -> List[Dict[str, Any]]:
        """从文本文件按行提取数据
        
        Returns:
            List[Dict[str, Any]]: 每行作为一个记录
        """
        if not self._file_path.exists():
            raise ExtractError(f"文件不存在: {self._file_path}")
        results = []
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        parsed = self._line_parser(line)
                        parsed["line_number"] = i
                        results.append(parsed)
            return results
        except Exception as e:
            raise ExtractError(f"文本读取失败: {e}", cause=e)


# ============================================================
# 数据转换器
# ============================================================

class Transformer:
    """转换器基类"""
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换数据
        
        Args:
            data: 输入数据记录列表
            
        Returns:
            List[Dict[str, Any]]: 转换后的数据记录列表
        """
        raise NotImplementedError


class FilterTransformer(Transformer):
    """过滤转换器"""
    def __init__(self, predicate: Callable[[Dict[str, Any]], bool]):
        self._predicate = predicate

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤数据
        
        Args:
            data: 输入数据
            
        Returns:
            List[Dict[str, Any]]: 满足predicate条件的记录
        """
        return [item for item in data if self._predicate(item)]


class MapTransformer(Transformer):
    """映射转换器"""
    def __init__(self, mapper: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self._mapper = mapper

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """映射数据
        
        Args:
            data: 输入数据
            
        Returns:
            List[Dict[str, Any]]: mapper转换后的记录
        """
        results = []
        for item in data:
            try:
                results.append(self._mapper(item))
            except Exception:
                results.append(item)  # 映射失败保留原数据
        return results


class SelectFieldsTransformer(Transformer):
    """字段选择转换器"""
    def __init__(self, fields: List[str], rename: Optional[Dict[str, str]] = None):
        self._fields = fields
        self._rename = rename or {}

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """选择并重命名字段
        
        Args:
            data: 输入数据
            
        Returns:
            List[Dict[str, Any]]: 只包含选定字段的记录
        """
        results = []
        for item in data:
            new_item = {}
            for f in self._fields:
                if f in item:
                    key = self._rename.get(f, f)
                    new_item[key] = item[f]
            results.append(new_item)
        return results


class AddFieldTransformer(Transformer):
    """添加字段转换器"""
    def __init__(self, field_name: str, value_fn: Callable[[Dict[str, Any]], Any]):
        self._field_name = field_name
        self._value_fn = value_fn

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """添加计算字段
        
        Args:
            data: 输入数据
            
        Returns:
            List[Dict[str, Any]]: 添加了新字段的记录
        """
        for item in data:
            try:
                item[self._field_name] = self._value_fn(item)
            except Exception:
                item[self._field_name] = None
        return data


class SortTransformer(Transformer):
    """排序转换器"""
    def __init__(self, key: str, reverse: bool = False):
        self._key = key
        self._reverse = reverse

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按字段排序
        
        Args:
            data: 输入数据
            
        Returns:
            List[Dict[str, Any]]: 排序后的记录
        """
        return sorted(data, key=lambda x: x.get(self._key, ""), reverse=self._reverse)


class LimitTransformer(Transformer):
    """限制数量转换器"""
    def __init__(self, limit: int):
        self._limit = limit

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """限制返回数量
        
        Args:
            data: 输入数据
            
        Returns:
            List[Dict[str, Any]]: 前limit条记录
        """
        return data[:self._limit]


class DeduplicateTransformer(Transformer):
    """去重转换器"""
    def __init__(self, key: Optional[str] = None):
        self._key = key

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复记录
        
        Args:
            data: 输入数据
            
        Returns:
            List[Dict[str, Any]]: 去重后的记录
        """
        seen = set()
        results = []
        for item in data:
            if self._key:
                identifier = item.get(self._key)
            else:
                identifier = json.dumps(item, sort_keys=True, default=str)
            if identifier not in seen:
                seen.add(identifier)
                results.append(item)
        return results


class AggregateTransformer(Transformer):
    """聚合转换器"""
    def __init__(
        self,
        group_by: str,
        aggregations: Dict[str, str],  # field_name: agg_type (sum/avg/count/min/max)
    ):
        self._group_by = group_by
        self._aggregations = aggregations

    def _compute_aggregation(self, items: List[Dict], field_name: str, agg_type: str) -> Any:
        """计算单个聚合值（辅助方法）"""
        values = [item.get(field_name) for item in items if item.get(field_name) is not None]
        if not values:
            return None
        
        numeric_values = []
        for v in values:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                pass
        
        if agg_type == "count":
            return len(values)
        elif agg_type == "sum" and numeric_values:
            return sum(numeric_values)
        elif agg_type == "avg" and numeric_values:
            return sum(numeric_values) / len(numeric_values)
        elif agg_type == "min" and numeric_values:
            return min(numeric_values)
        elif agg_type == "max" and numeric_values:
            return max(numeric_values)
        return None

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分组聚合变换
        
        Args:
            data: 输入数据
            
        Returns:
            List[Dict[str, Any]]: 聚合结果，每组一条记录
        """
        groups: Dict[Any, List[Dict[str, Any]]] = {}
        for item in data:
            key = item.get(self._group_by, "__none__")
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        results = []
        for group_key, items in groups.items():
            result = {self._group_by: group_key, "_count": len(items)}
            for field_name, agg_type in self._aggregations.items():
                agg_value = self._compute_aggregation(items, field_name, agg_type)
                result[f"{field_name}_{agg_type}"] = agg_value
            results.append(result)
        return results


# ============================================================
# 数据目标
# ============================================================

class DataSink:
    """数据目标基类"""
    def load(self, data: List[Dict[str, Any]]) -> int:
        """加载数据
        
        Args:
            data: 要加载的数据记录列表
            
        Returns:
            int: 成功加载的记录数
        """
        raise NotImplementedError


class MemorySink(DataSink):
    """内存数据目标"""
    def __init__(self):
        self.data: List[Dict[str, Any]] = []

    def load(self, data: List[Dict[str, Any]]) -> int:
        """将数据存储在内存中
        
        Args:
            data: 要加载的数据
            
        Returns:
            int: 加载的记录数
        """
        self.data.extend(data)
        return len(data)

    def clear(self) -> None:
        """清空存储的数据"""
        self.data.clear()


class JSONFileSink(DataSink):
    """JSON文件数据目标"""
    def __init__(self, file_path: Path, indent: int = 2):
        self._file_path = Path(file_path)
        self._indent = indent

    def load(self, data: List[Dict[str, Any]]) -> int:
        """将数据写入JSON文件
        
        Args:
            data: 要加载的数据
            
        Returns:
            int: 写入的记录数
            
        Raises:
            LoadError: 写入失败
        """
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=self._indent, default=str)
            return len(data)
        except Exception as e:
            raise LoadError(f"JSON写入失败: {e}", cause=e)


class CSVFileSink(DataSink):
    """CSV文件数据目标"""
    def __init__(self, file_path: Path, encoding: str = "utf-8"):
        self._file_path = Path(file_path)
        self._encoding = encoding

    def load(self, data: List[Dict[str, Any]]) -> int:
        """将数据写入CSV文件
        
        Args:
            data: 要加载的数据
            
        Returns:
            int: 写入的记录数
            
        Raises:
            LoadError: 写入失败
        """
        if not data:
            return 0
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            fieldnames = list(data[0].keys())
            with open(self._file_path, 'w', encoding=self._encoding, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            return len(data)
        except Exception as e:
            raise LoadError(f"CSV写入失败: {e}", cause=e)


# ============================================================
# 管道
# ============================================================

@dataclass
class PipelineStep:
    """管道步骤"""
    name: str
    processor: Any  # DataSource, Transformer, or DataSink
    step_type: str  # "extract", "transform", "load"


@dataclass
class PipelineResult:
    """管道执行结果"""
    success: bool
    records_processed: int = 0
    records_output: int = 0
    steps_completed: int = 0
    total_steps: int = 0
    error: Optional[str] = None
    duration_ms: float = 0.0
    data_sample: List[Dict[str, Any]] = field(default_factory=list)


class DataPipeline:
    """
    数据管道

    职责：
    - 编排 Extract → Transform → Load 流程
    - 支持链式调用
    - 记录执行统计
    - 错误处理与恢复
    """

    def __init__(self, name: str = "pipeline"):
        self.name = name
        self._steps: List[PipelineStep] = []
        self._data: List[Dict[str, Any]] = []
        self._history: List[PipelineResult] = []

    @property
    def steps(self) -> List[str]:
        """获取管道步骤名称列表
        
        Returns:
            List[str]: 步骤名称列表
        """
        return [s.name for s in self._steps]

    def extract(self, source: DataSource, name: str = "extract") -> 'DataPipeline':
        """添加数据提取步骤"""
        self._steps.append(PipelineStep(name=name, processor=source, step_type="extract"))
        return self

    def transform(self, transformer: Transformer, name: str = "transform") -> 'DataPipeline':
        """添加数据转换步骤"""
        self._steps.append(PipelineStep(name=name, processor=transformer, step_type="transform"))
        return self

    def load(self, sink: DataSink, name: str = "load") -> 'DataPipeline':
        """添加数据加载步骤"""
        self._steps.append(PipelineStep(name=name, processor=sink, step_type="load"))
        return self

    def run(self) -> PipelineResult:
        """
        执行管道

        Returns:
            PipelineResult
        """
        import time
        start_time = time.time()
        records_processed = 0
        steps_completed = 0
        error = None

        try:
            for step in self._steps:
                try:
                    if step.step_type == "extract":
                        self._data = step.processor.extract()
                        records_processed = len(self._data)
                    elif step.step_type == "transform":
                        self._data = step.processor.transform(self._data)
                        records_processed = len(self._data)
                    elif step.step_type == "load":
                        records_processed = step.processor.load(self._data)
                    steps_completed += 1
                except Exception as e:
                    error = f"步骤 '{step.name}' 失败: {e}"
                    break

            elapsed_ms = (time.time() - start_time) * 1000
            success = error is None and steps_completed == len(self._steps)

            result = PipelineResult(
                success=success,
                records_processed=records_processed,
                records_output=len(self._data),
                steps_completed=steps_completed,
                total_steps=len(self._steps),
                error=error,
                duration_ms=round(elapsed_ms, 2),
                data_sample=self._data[:5],
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            result = PipelineResult(
                success=False,
                error=str(e),
                duration_ms=round(elapsed_ms, 2),
                total_steps=len(self._steps),
            )

        self._history.append(result)
        return result

    def get_data(self) -> List[Dict[str, Any]]:
        """获取当前管道数据"""
        return list(self._data)

    def reset(self) -> None:
        """重置管道"""
        self._data.clear()
        self._steps.clear()

    def get_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return [
            {
                "success": r.success,
                "records_processed": r.records_processed,
                "records_output": r.records_output,
                "steps_completed": r.steps_completed,
                "total_steps": r.total_steps,
                "error": r.error,
                "duration_ms": r.duration_ms,
            }
            for r in self._history
        ]
