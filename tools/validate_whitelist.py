#!/usr/bin/env python3
"""whitelist.json 入库校验（CI 与本地共用，无第三方依赖）。

校验项：
  1. 合法 JSON 对象
  2. "hwids" 必须存在且是数组（缺失 = 所有客户端全被拒，属于重大事故，直接 fail）
  3. 每项是 64 位十六进制小写 sha256，或 {"id": ..., "enabled": bool} 对象
  4. 无重复 id
  5. 可选 "_expires_at" 必须是 ISO8601
  6. 提示性检查：空名单 / 数量骤降会让所有客户端失效
退出码 0=通过, 1=失败
"""
import json
import re
import sys
import pathlib

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}:\d{2}Z?)?$")


def fail(msg):
    print(f"ERROR: {msg}")
    return 1


def main(path):
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    try:
        doc = json.loads(raw)
    except Exception as e:
        return fail(f"{path} 不是合法 JSON: {e}")
    if not isinstance(doc, dict):
        return fail("顶层必须是 JSON 对象")

    if "hwids" not in doc:
        return fail('缺少 "hwids" 字段（客户端会 fail-closed 全员被拒）')
    arr = doc["hwids"]
    if not isinstance(arr, list):
        return fail('"hwids" 必须是数组')

    errs, seen, disabled = [], {}, 0
    for i, item in enumerate(arr):
        if isinstance(item, str):
            hid, enabled = item, True
        elif isinstance(item, dict):
            hid, enabled = item.get("id"), item.get("enabled", True)
            if not isinstance(enabled, bool):
                errs.append(f'#{i}: "enabled" 必须是布尔')
        else:
            errs.append(f"#{i}: 只能是字符串或对象，得到 {type(item).__name__}")
            continue
        if not isinstance(hid, str) or not HEX64.match(hid.strip().lower()):
            errs.append(f"#{i}: id 不是 64 位十六进制 sha256: {hid!r}")
            continue
        hid = hid.strip().lower()
        if hid in seen:
            errs.append(f"#{i}: 重复 id {hid[:16]}…")
        seen[hid] = enabled
        if enabled is False:
            disabled += 1

    exp = doc.get("_expires_at")
    if exp is not None and not (isinstance(exp, str) and ISO.match(exp.strip())):
        errs.append(f'_expires_at 格式非法（要 ISO8601）: {exp!r}')

    for e in errs:
        print(f"ERROR: {e}")
    if errs:
        return 1

    print(f"OK  {len(seen)} 条（启用 {len(seen) - disabled} / 禁用 {disabled}）")
    if not seen:
        print("WARN: 白名单为空 —— 当前所有客户端都会被拒绝")
    elif len(seen) <= 2:
        print(f"WARN: 名单只有 {len(seen)} 条，确认不是误删")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "whitelist.json"))
