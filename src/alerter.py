"""
告警系统模块 — 部署与运维层

公理溯源：存续公理 - 系统需要及时告警以保持稳定

设计意图：
- 阈值告警
- 告警规则配置
- 通知渠道管理
- 告警历史记录
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

from logger import get_logger
from utils import now_iso

logger = get_logger("Alerter")


class AlertSeverity(Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """告警"""
    name: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    status: AlertStatus = AlertStatus.FIRING
    timestamp: str = field(default_factory=now_iso)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric: str
    operator: str  # >, <, >=, <=, ==, !=
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    duration: int = 0  # 持续时间（秒）
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


class Alerter:
    """
    告警器
    
    管理告警规则和通知
    """
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notifiers: List[Callable[[Alert], None]] = []
        self._lock = threading.Lock()
        
        # 指标值缓存
        self._metric_values: Dict[str, List[float]] = defaultdict(list)
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.name] = rule
        logger.info(f"添加告警规则: {rule.name}")
    
    def remove_rule(self, name: str):
        """移除告警规则"""
        if name in self.rules:
            del self.rules[name]
            logger.info(f"移除告警规则: {name}")
    
    def add_notifier(self, notifier: Callable[[Alert], None]):
        """添加通知器"""
        self.notifiers.append(notifier)
    
    def evaluate(self, metric_name: str, value: float):
        """
        评估指标值
        
        Args:
            metric_name: 指标名称
            value: 指标值
        """
        with self._lock:
            self._metric_values[metric_name].append((time.time(), value))
            # 限制历史长度
            if len(self._metric_values[metric_name]) > 100:
                self._metric_values[metric_name] = self._metric_values[metric_name][-100:]
        
        for rule_name, rule in self.rules.items():
            if rule.metric == metric_name:
                self._evaluate_rule(rule, value)
    
    def _evaluate_rule(self, rule: AlertRule, value: float):
        """评估规则"""
        triggered = self._check_threshold(value, rule.operator, rule.threshold)
        
        alert_key = f"{rule.name}:{rule.metric}"
        
        with self._lock:
            if triggered:
                if alert_key not in self.active_alerts:
                    # 创建新告警
                    alert = Alert(
                        name=rule.name,
                        severity=rule.severity,
                        message=f"指标 {rule.metric} {rule.operator} {rule.threshold}, 当前值: {value}",
                        value=value,
                        threshold=rule.threshold,
                        labels=rule.labels,
                        annotations=rule.annotations
                    )
                    
                    self.active_alerts[alert_key] = alert
                    self.alert_history.append(alert)
                    
                    # 发送通知
                    self._notify(alert)
                    
                    logger.warning(f"告警触发: {rule.name} - {alert.message}")
            else:
                if alert_key in self.active_alerts:
                    # 告警恢复
                    alert = self.active_alerts[alert_key]
                    alert.status = AlertStatus.RESOLVED
                    
                    self.alert_history.append(alert)
                    del self.active_alerts[alert_key]
                    
                    # 发送恢复通知
                    self._notify(alert)
                    
                    logger.info(f"告警恢复: {rule.name}")
    
    def _check_threshold(self, value: float, operator: str, threshold: float) -> bool:
        """检查阈值"""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        return False
    
    def _notify(self, alert: Alert):
        """发送通知"""
        for notifier in self.notifiers:
            try:
                notifier(alert)
            except Exception as e:
                logger.error(f"通知发送失败: {e}")
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:]
    
    def get_alert_summary(self) -> Dict:
        """获取告警摘要"""
        severity_counts = defaultdict(int)
        for alert in self.active_alerts.values():
            severity_counts[alert.severity.value] += 1
        
        return {
            "active_count": len(self.active_alerts),
            "history_count": len(self.alert_history),
            "by_severity": dict(severity_counts),
        }


class ConsoleNotifier:
    """控制台通知器"""
    
    def __call__(self, alert: Alert):
        status_str = "🔴" if alert.status == AlertStatus.FIRING else "🟢"
        severity_str = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🔥",
        }.get(alert.severity, "")
        
        print(f"\n{status_str} {severity_str} [{alert.severity.value.upper()}] {alert.name}")
        print(f"   {alert.message}")
        print(f"   时间: {alert.timestamp}")


class LogNotifier:
    """日志通知器"""
    
    def __call__(self, alert: Alert):
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(f"告警: {alert.name} - {alert.message}")
        elif alert.severity == AlertSeverity.ERROR:
            logger.error(f"告警: {alert.name} - {alert.message}")
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(f"告警: {alert.name} - {alert.message}")
        else:
            logger.info(f"告警: {alert.name} - {alert.message}")


def create_alerter_with_defaults() -> Alerter:
    """创建带默认配置的告警器"""
    alerter = Alerter()
    
    # 添加默认通知器
    alerter.add_notifier(ConsoleNotifier())
    alerter.add_notifier(LogNotifier())
    
    # 添加默认规则
    alerter.add_rule(AlertRule(
        name="high_error_rate",
        metric="error_rate",
        operator=">",
        threshold=0.1,
        severity=AlertSeverity.WARNING,
        annotations={"summary": "错误率过高"}
    ))
    
    alerter.add_rule(AlertRule(
        name="high_memory_usage",
        metric="memory_usage_percent",
        operator=">",
        threshold=80,
        severity=AlertSeverity.WARNING,
        annotations={"summary": "内存使用率过高"}
    ))
    
    alerter.add_rule(AlertRule(
        name="critical_memory",
        metric="memory_usage_percent",
        operator=">",
        threshold=95,
        severity=AlertSeverity.CRITICAL,
        annotations={"summary": "内存使用率严重过高"}
    ))
    
    return alerter
