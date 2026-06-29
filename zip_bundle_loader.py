"""zip_bundle_loader.py - v3.11.0

解析 luogu-toolkit / luogu-report-generator 产出的 ZIP 数据包, 还原 export_data。

设计目标:
    - 完全独立于 pyLuogu / 洛谷登录态
    - 校验 schema_version, 不匹配直接报错
    - 既能从磁盘 ZIP 读, 也能从内存字节流读 (Web 上传用)
    - 与 run_generation() 内部用的 export_data dict 100% 兼容

ZIP schema (v1, 来自 luogu-toolkit.bundle / luogu-report-generator.bundle_loader):
    <uid>-<ts>.zip
    ├─ manifest.json          元信息 (schema_version, luogu_uid, username, ...)
    ├─ export_data.json       全部抓取的数据 + 行为/六维/性格/大纲对标
    ├─ items/passed/P1000.json    每道已通过的题目记录
    ├─ items/passed/P1001.json
    └─ items/failed/P2000.json

用法:
    from zip_bundle_loader import load_zip, load_zip_bytes
    bundle = load_zip_bytes(zfile.read(), "uploaded.zip")
    export_data = bundle.export_data
    # ... 喂给 _generate_ai_report_artifacts()
"""
from __future__ import annotations

import io
import json
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zip_bundle_loader")

# 与 luogu-toolkit.bundle.BUNDLE_SCHEMA_VERSION 保持一致
EXPECTED_SCHEMA_VERSION = 1
MAX_ZIP_BYTES = 200 * 1024 * 1024  # 200 MB, 上传大小上限


class BundleLoadError(Exception):
    """ZIP 解析失败 (格式不对 / schema 不匹配 / 文件缺失)"""


@dataclass
class ReportBundle:
    """一个解析好的 ZIP 数据包"""

    export_data: Dict[str, Any]
    manifest: Dict[str, Any]
    passed_items: List[Dict[str, Any]] = field(default_factory=list)
    failed_items: List[Dict[str, Any]] = field(default_factory=list)
    source_path: Optional[Path] = None

    @property
    def schema_version(self) -> int:
        try:
            return int(self.manifest.get("schema_version") or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def luogu_uid(self) -> str:
        return str(self.manifest.get("luogu_uid") or "")

    @property
    def username(self) -> str:
        return str(self.manifest.get("username") or "")

    @property
    def name(self) -> str:
        # 优先 manifest.name (toolkit 写入), 退回 username
        return str(self.manifest.get("name") or self.manifest.get("username") or "")

    @property
    def solved_count(self) -> int:
        try:
            return int(self.manifest.get("solved_count") or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def failed_count(self) -> int:
        try:
            return int(self.manifest.get("failed_count") or 0)
        except (TypeError, ValueError):
            return 0

    def summary_line(self) -> str:
        return (
            f"uid={self.luogu_uid} username={self.username} name={self.name} "
            f"passed={self.solved_count} failed={self.failed_count} "
            f"schema=v{self.schema_version}"
        )


def _read_json(zf: zipfile.ZipFile, name: str) -> Dict[str, Any]:
    """从 ZIP 里读一个 JSON 文件, 报错时包成 BundleLoadError"""
    try:
        with zf.open(name) as f:
            raw = f.read().decode("utf-8")
    except KeyError as e:
        raise BundleLoadError(f"ZIP 缺少必需文件: {name}") from e
    except UnicodeDecodeError as e:
        raise BundleLoadError(f"ZIP 中 {name} 不是 UTF-8 编码: {e}") from e
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BundleLoadError(f"ZIP 中 {name} 不是合法 JSON: {e}") from e
    if not isinstance(data, dict):
        raise BundleLoadError(f"ZIP 中 {name} 必须是 dict, 实际 {type(data).__name__}")
    return data


def _scan_items(
    zf: zipfile.ZipFile, names: List[str]
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """扫一遍 items/passed/*.json 和 items/failed/*.json"""
    passed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with zf.open(name) as f:
                raw = f.read().decode("utf-8")
            obj = json.loads(raw)
        except Exception as e:
            # 单个 item 损坏不影响整体 (与原项目保持一致: 容错)
            logger.warning("[zip_bundle_loader] 跳过损坏的 item 文件 %s: %s", name, e)
            continue
        if not isinstance(obj, dict):
            continue
        if name.startswith("items/passed/") or name.startswith("items\\passed\\"):
            passed.append(obj)
        elif name.startswith("items/failed/") or name.startswith("items\\failed\\"):
            failed.append(obj)
    return passed, failed


def _validate(bundle: ReportBundle) -> None:
    """schema 校验 (统一出口)"""
    if bundle.schema_version != EXPECTED_SCHEMA_VERSION:
        raise BundleLoadError(
            f"schema_version 不匹配: 期望 {EXPECTED_SCHEMA_VERSION}, "
            f"实际 {bundle.schema_version}。"
            f"请用匹配的 luogu-toolkit 版本重新打 ZIP"
        )
    if not isinstance(bundle.export_data, dict):
        raise BundleLoadError("export_data.json 必须是 dict")
    # export_data 必须至少有 student_info 键 (与 _generate_ai_report_artifacts 对齐)
    if "student_info" not in bundle.export_data:
        # 不直接报错, 而是注入一个空 student_info, 后面 _generate_ai_report_artifacts 会兜底
        bundle.export_data.setdefault("student_info", {})


def load_zip(zip_path: str | Path) -> ReportBundle:
    """从磁盘 ZIP 文件解析出 ReportBundle。"""
    p = Path(zip_path)
    if not p.exists():
        raise BundleLoadError(f"ZIP 文件不存在: {p}")
    if not p.is_file():
        raise BundleLoadError(f"不是文件: {p}")
    if p.stat().st_size == 0:
        raise BundleLoadError(f"ZIP 文件是空的: {p}")
    if p.stat().st_size > MAX_ZIP_BYTES:
        raise BundleLoadError(
            f"ZIP 文件过大: {p.stat().st_size / 1024 / 1024:.1f} MB, "
            f"上限 {MAX_ZIP_BYTES / 1024 / 1024:.0f} MB"
        )
    if not zipfile.is_zipfile(str(p)):
        raise BundleLoadError(f"不是合法 ZIP: {p}")
    with zipfile.ZipFile(str(p), "r") as zf:
        names = zf.namelist()
        manifest = _read_json(zf, "manifest.json")
        export_data = _read_json(zf, "export_data.json")
        passed, failed = _scan_items(zf, names)
    bundle = ReportBundle(
        export_data=export_data,
        manifest=manifest,
        passed_items=passed,
        failed_items=failed,
        source_path=p.resolve(),
    )
    _validate(bundle)
    return bundle


def load_zip_bytes(data: bytes, source_name: str = "<memory>") -> ReportBundle:
    """从内存中的 ZIP 字节流解析 (供 Web 上传场景用)。"""
    if not data:
        raise BundleLoadError("上传内容为空")
    if len(data) > MAX_ZIP_BYTES:
        raise BundleLoadError(
            f"ZIP 字节流过大: {len(data) / 1024 / 1024:.1f} MB, "
            f"上限 {MAX_ZIP_BYTES / 1024 / 1024:.0f} MB"
        )
    try:
        bio = io.BytesIO(data)
        with zipfile.ZipFile(bio, "r") as zf:
            names = zf.namelist()
            manifest = _read_json(zf, "manifest.json")
            export_data = _read_json(zf, "export_data.json")
            passed, failed = _scan_items(zf, names)
    except BundleLoadError:
        raise
    except zipfile.BadZipFile as e:
        raise BundleLoadError(f"上传内容不是合法 ZIP: {e}") from e
    except Exception as e:
        raise BundleLoadError(f"ZIP 解析失败: {e}") from e
    bundle = ReportBundle(
        export_data=export_data,
        manifest=manifest,
        passed_items=passed,
        failed_items=failed,
        source_path=Path(source_name) if source_name else None,
    )
    _validate(bundle)
    return bundle


__all__ = [
    "BundleLoadError",
    "EXPECTED_SCHEMA_VERSION",
    "MAX_ZIP_BYTES",
    "ReportBundle",
    "load_zip",
    "load_zip_bytes",
]
