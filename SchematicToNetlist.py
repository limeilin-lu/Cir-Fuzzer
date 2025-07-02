import subprocess
import os
import shutil  # 用于文件复制

# 转网表

kicad_cli_path = r"D:\KiCad\bin"
input_path = r"D:\Code\genschema\gendir"
output_base_path = r"D:\Code\genschema\Simulation"  

# 定义所有输出路径
output_paths = {
    "KIdir": os.path.join(output_base_path, "KIdir"),
    "LTdir": os.path.join(output_base_path, "LTdir"),
    "HSdir": os.path.join(output_base_path, "HSdir"),
    "PSdir": os.path.join(output_base_path, "PSdir"),
    "LTPSdir": os.path.join(output_base_path, "LTPSdir"),
    "SPEdir": os.path.join(output_base_path, "SPEdir")
}

# 确保所有输出目录存在
for path in output_paths.values():
    os.makedirs(path, exist_ok=True)

# 遍历输入文件夹中的文件
files = os.listdir(input_path)
for file in files:
    if file.endswith(".kicad_sch"):
        print(f"{file} is being converted to netlist!")
        # 生成主输出文件路径（仍以 KIdir 为主要输出目录）
        output_file = os.path.join(output_paths["KIdir"], file[:-10] + ".cir")

        # 构造命令
        command = (
            f"cd {kicad_cli_path} ; ./kicad-cli sch export netlist "
            f"{os.path.join(input_path, file)} -o {output_file} --format spice"
        )

        # 执行命令
        result = subprocess.run(['powershell', '-Command', command], capture_output=True)
        if result.returncode == 0:
            print(f"Conversion successful for {file}.")
        else:
            print(f"Conversion failed for {file}, but copying the file as planned.")

        # 如果转换成功生成了 output_file，将其复制到所有其他路径
        if os.path.exists(output_file):
            for dir_name, dir_path in output_paths.items():
                if dir_name != "KIdir":  # 跳过 KIdir，因为已经是原始输出路径
                    target_file = os.path.join(dir_path, file[:-10] + ".cir")
                    shutil.copy(output_file, target_file)
                    print(f"{file[:-10]}.cir is copied to {dir_name} folder.")
        else:
            print(f"Output file {output_file} not found, skipping copy step.")


