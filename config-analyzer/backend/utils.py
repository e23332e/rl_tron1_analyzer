"""Utility functions."""

import re
import json
from typing import Any


def type_name(value: Any) -> str:
    """Get a string type name for a Python value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def infer_robot_type(experiment_name: str) -> str:
    """Infer robot type from experiment name."""
    name = experiment_name.lower()
    if name.startswith("sf_"):
        return "SF"
    elif name.startswith("pf_"):
        return "PF"
    elif name.startswith("wf_"):
        return "WF"
    return "Unknown"


def infer_task_variant(experiment_name: str) -> str:
    """Infer task variant from experiment name."""
    name = experiment_name.lower()
    if "walk" in name:
        return "Walk"
    elif "hop" in name:
        return "Hop"
    elif "jump" in name:
        return "Jump"
    elif "slow" in name:
        return "Slow"
    elif "stair" in name:
        return "Stair"
    elif "flat" in name:
        return "Flat"
    elif "stand" in name:
        return "Stand"
    return "Unknown"


def parse_evaluation_issues(text: str) -> list[str]:
    """Parse Chinese evaluation text and extract issue tags."""
    issues = []
    keywords = {
        "原地踏步": "marking_time",
        "倾斜": "tilting",
        "距离太短": "short_stride",
        "距离太大": "long_stride",
        "抖动": "trembling",
        "摔倒": "falling",
        "不稳定": "unstable",
        "偏离": "deviation",
        "震荡": "oscillation",
        "僵硬": "stiff_motion",
        "过高": "too_high",
        "过低": "too_low",
    }
    for kw, tag in keywords.items():
        if kw in text:
            issues.append(tag)
    return issues
