import subprocess
from pathlib import Path


def run_script(script_name, script_type="python", cwd=None, check=False):
    """通用脚本运行函数"""
    if script_type == "python":
        cmd = ["python", script_name]  # Windows 可能用 "python"
    elif script_type == "go":
        cmd = ["go", "run", script_name]
    else:
        cmd = [script_name]  # 直接执行

    print(f"运行: {' '.join(cmd)} 在目录: {cwd}")

    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    print(f"=== {script_name} 标准输出 ===")
    print(result.stdout if result.stdout else "None")
    print(f"=== {script_name} 错误输出 ===")
    print(result.stderr if result.stderr else "None")
    print(f"=== {script_name} 退出码: {result.returncode} ===")

    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)

    return result


def main():
    # 确定项目目录
    project_dir = Path(__file__).parent / "Deadpool-proxypool1.5"

    try:
        # 1. 先运行 fir.py
        py_result = run_script("fir.py", "python", project_dir)

        # 2. 再运行 Go 程序
        go_result = run_script("main_modify.go", "go", project_dir)

        print("\n所有脚本执行完成！")

    except Exception as e:
        print(f"执行过程中出错: {e}")


if __name__ == "__main__":
    main()