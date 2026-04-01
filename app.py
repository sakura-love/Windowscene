import sys


def main():
    try:
        from qt_app import main as qt_main
    except ImportError as exc:
        missing = getattr(exc, "name", "") or "PySide6"
        message = (
            f"缺少运行依赖：{missing}\n"
            "请先安装 PySide6：\n"
            "pip install -r requirements.txt"
        )
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Windows 情景模式", message)
            root.destroy()
        except Exception:
            print(message)
        raise SystemExit(1) from exc

    qt_main("--boot" in sys.argv)


if __name__ == "__main__":
    main()
