#!/usr/bin/env python3
"""CI 构建时从 git tag 读取版本号，生成 version_info.txt 供 PyInstaller 使用。

用法：
  python scripts/generate_version_info.py          # 写入 version_info.txt
  python scripts/generate_version_info.py --print  # 只打印不写入
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "version_info.txt"


def get_version_from_git() -> str:
    """优先从 GITHUB_REF 环境变量读，否则从 git describe 读取。"""
    import os

    # CI 环境：GITHUB_REF = refs/tags/v1.2.3
    ref = os.environ.get("GITHUB_REF", "")
    if ref.startswith("refs/tags/"):
        tag = ref[len("refs/tags/"):]
        return tag.lstrip("v")

    # 本地开发：从 git describe 读
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, cwd=ROOT,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().lstrip("v")
    except FileNotFoundError:
        pass

    return "0.0.0"


def parse_version(version: str):
    """'1.2.1' → (1, 2, 1, 0)"""
    parts = version.split(".")
    nums = []
    for p in parts[:4]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums)


def generate(version: str) -> str:
    v = parse_version(version)
    return f"""# 此文件由 scripts/generate_version_info.py 自动生成，请勿手动编辑。
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={v},
    prodvers={v},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '080404B0',
        [
          StringStruct('CompanyName', 'sakura-love'),
          StringStruct('FileDescription', 'Windowscene'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'Windowscene'),
          StringStruct('OriginalFilename', 'Windowscene.exe'),
          StringStruct('ProductName', 'Windowscene'),
          StringStruct('ProductVersion', '{version}'),
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""


def main():
    parser = argparse.ArgumentParser(description="生成 version_info.txt")
    parser.add_argument("--print", action="store_true", help="仅打印，不写入文件")
    args = parser.parse_args()

    version = get_version_from_git()
    content = generate(version)

    if getattr(args, "print"):
        print(content)
        return

    OUTPUT.write_text(content, encoding="utf-8")
    print(f"✅ version_info.txt 已生成 (v{version})")


if __name__ == "__main__":
    main()
