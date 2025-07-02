# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import time
import shutil

def change_file(file):
    old_str = "Date:"
    file_data = ""
    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            if old_str in line:
                s = "" + line
                line = line.replace(s, old_str + "\n")
            file_data += line
    with open(file, "w", encoding="utf-8") as f:
        f.write(file_data)

os.environ["PYTHONIOENCODING"] = "utf-8"

# 可调整参数
inputPath = "D:\\Code\\Simulation\\LTPSdir\\"
outputPath = "D:\\Code\\aoutput\\ltps.txt"
spicePath = "D:\\Code\\genschema\\spice.rc"
maxTime = 30


# 初始化计数器
diffNum = 0
both_yes_count = 0
both_no_count = 0
both_diff_count = 0

start_time = time.time()
files = os.listdir(inputPath)

for file in files:
    if file.endswith(".cir"):
        filePath = file.split('.')[0]
        first_sim_success = False
        second_sim_success = False
        target_spice = os.path.join(inputPath, "spice.rc")  # 在循环开始时定义

        try:
            # 第一次仿真（不使用 spice.rc）
            cmd = "ngspice -b -r " + filePath + ".raw -o " + filePath + ".log " + file
            print(f"Running first simulation: {cmd}")
            result = subprocess.run(cmd, cwd=inputPath, timeout=maxTime, shell=True)
            first_sim_success = (result.returncode == 0)

            # 复制 spice.rc
            print(f"Copying {spicePath} to {target_spice}")
            shutil.copy(spicePath, target_spice)
            time.sleep(0.1)
            if not os.path.exists(target_spice):
                raise FileNotFoundError(f"Failed to copy {spicePath} to {target_spice}")

            # 第二次仿真
            cmd = "ngspice -b -i " + target_spice + " -r " + filePath + "s.raw -o " + filePath + "s.log " + file
            print(f"Running second simulation: {cmd}")
            resultn = subprocess.run(cmd, cwd=inputPath, timeout=maxTime, shell=True, encoding='utf-8')
            second_sim_success = (resultn.returncode == 0)

            # 清理spice.rc
            if os.path.exists(target_spice):
                cmd = "del " + target_spice
                subprocess.run(cmd, shell=True)

            # 原始输出逻辑
            if first_sim_success and second_sim_success:
                change_file(inputPath + filePath + ".raw")
                change_file(inputPath + filePath + "s.raw")
                cmd = "fc /b " + filePath + ".raw " + filePath + "s.raw"
                print(f"Comparing files: {cmd}")
                output = subprocess.run(cmd, cwd=inputPath, shell=True, encoding='utf-8')
                with open(outputPath, "a", encoding='utf-8') as outputFile:
                    if output.returncode == 1:
                        outputFile.write(file + "\t\tdiff\n")
                        diffNum += 1
                    else:
                        outputFile.write(file + "\t\tsame\n")
                with open(both_yes_file, "a", encoding='utf-8') as f:
                    f.write(file + "\n")
                both_yes_count += 1
            elif not first_sim_success and second_sim_success:
                with open(outputPath, "a", encoding='utf-8') as outputFile:
                    outputFile.write(file + "\t\tdiff\n")
                diffNum += 1
                with open(both_diff_file, "a", encoding='utf-8') as f:
                    f.write(file + "\n")
                both_diff_count += 1
            elif first_sim_success and not second_sim_success:
                with open(outputPath, "a", encoding='utf-8') as outputFile:
                    outputFile.write(file + "\t\tdiff\n")
                diffNum += 1
                with open(both_diff_file, "a", encoding='utf-8') as f:
                    f.write(file + "\n")
                both_diff_count += 1
            else:  # 两次都失败
                print(f"{file}.cir simulation failed and {file}.cir ltps simulation failed")
                with open(outputPath, "a", encoding='utf-8') as outputFile:
                    outputFile.write(file + "\t\tcrash\n")
                with open(both_no_file, "a", encoding='utf-8') as f:
                    f.write(file + "\n")
                both_no_count += 1

        except subprocess.TimeoutExpired:
            cmd = "TASKKILL /F /IM ngspice.exe /T"
            subprocess.run(cmd, shell=True)
            with open(outputPath, "a", encoding='utf-8') as outputFile:
                outputFile.write(file + "\t\ttimeout\n")
            with open(both_no_file, "a", encoding='utf-8') as f:
                f.write(file + "\t\ttimeout\n")
            both_no_count += 1
            if os.path.exists(target_spice):
                cmd = "del " + target_spice
                subprocess.run(cmd, shell=True)
            continue
        except FileNotFoundError as e:
            print(f"Error: {e}")
            with open(outputPath, "a", encoding='utf-8') as outputFile:
                outputFile.write(file + "\t\tcopy_error\n")
            with open(both_no_file, "a", encoding='utf-8') as f:
                f.write(file + "\t\tcopy_error\n")
            both_no_count += 1
            continue

print("共发现" + str(diffNum) + "个不同！！！")
print(f"Both successful: {both_yes_count}")
print(f"Both failed: {both_no_count}")
print(f"Different results: {both_diff_count}")
end_time = time.time()
run_time = end_time - start_time
print(f"run time = {run_time}s")

"""
# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import time
import shutil

# 仿真 NGspice44
def change_file(file):
    old_str = "Date:"
    file_data = ""
    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            if old_str in line:
                s = "" + line
                line = line.replace(s, old_str+"\n")
            file_data += line
    with open(file, "w", encoding="utf-8") as f:
        f.write(file_data)

os.environ["PYTHONIOENCODING"] = "utf-8"

# 可调整参数
inputPath = "D:\\Code\\PCBSmith+\\PCBSmith+\\genschema\\LTPSdir\\"
outputPath = "D:\\Code\\PCBSmith+\\PCBSmith+\\genschema\\aoutput\\20250316_2.txt"
spicePath = "D:\\Code\\PCBSmith+\\PCBSmith+\\genschema\\spice.rc"
maxTime = 30

start_time = time.time()
diffNum = 0
files = os.listdir(inputPath)

for file in files:
    if file.endswith(".cir"):
        filePath = file.split('.')[0]
        try:
            # 第一次仿真（不使用 spice.rc）
            cmd = "ngspice -b -r " + filePath + ".raw -o " + filePath + ".log " + file
            print(f"Running first simulation: {cmd}")
            result = subprocess.run(cmd, cwd=inputPath, timeout=maxTime, shell=True)
            if result.returncode == 0:
                # 复制 spice.rc
                target_spice = os.path.join(inputPath, "spice.rc")
                print(f"Copying {spicePath} to {target_spice}")
                shutil.copy(spicePath, target_spice)
                time.sleep(0.1)  # 短暂延迟，确保复制完成
                if not os.path.exists(target_spice):
                    raise FileNotFoundError(f"Failed to copy {spicePath} to {target_spice}")

                # 第二次仿真，使用 -i 加载 spice.rc
                cmd = "ngspice -b -i " + target_spice + " -r " + filePath + "s.raw -o " + filePath + "s.log " + file
                print(f"Running second simulation: {cmd}")
                resultn = subprocess.run(cmd, cwd=inputPath, timeout=maxTime, shell=True, encoding='utf-8')
                if resultn.returncode == 0:
                    cmd = "del " + target_spice
                    subprocess.run(cmd, shell=True)
                    change_file(inputPath + filePath + ".raw")
                    change_file(inputPath + filePath + "s.raw")
                    cmd = "fc /b " + filePath + ".raw " + filePath + "s.raw"
                    print(f"Comparing files: {cmd}")
                    output = subprocess.run(cmd, cwd=inputPath, shell=True, encoding='utf-8')
                    if output.returncode == 1:
                        with open(outputPath, "a") as outputFile:
                            outputFile.write(file + "\t\tdiff\n")
                            diffNum += 1
                    else:
                        with open(outputPath, "a") as outputFile:
                            outputFile.write(file + "\t\tsame\n")
                else:
                    with open(outputPath, "a") as outputFile:
                        outputFile.write(file + "\t\tdiff\n")
                        diffNum += 1
                    cmd = "del " + target_spice
                    subprocess.run(cmd, shell=True)
            else:
                # 复制 spice.rc
                target_spice = os.path.join(inputPath, "spice.rc")
                print(f"Copying {spicePath} to {target_spice}")
                shutil.copy(spicePath, target_spice)
                time.sleep(0.1)  # 短暂延迟，确保复制完成
                if not os.path.exists(target_spice):
                    raise FileNotFoundError(f"Failed to copy {spicePath} to {target_spice}")

                # 第二次仿真
                cmd = "ngspice -b -i " + target_spice + " -r " + filePath + "s.raw -o " + filePath + "s.log " + file
                print(f"Running second simulation: {cmd}")
                resultn = subprocess.run(cmd, cwd=inputPath, timeout=maxTime, shell=True, encoding='utf-8')
                if resultn.returncode == 0:
                    cmd = "del " + target_spice
                    subprocess.run(cmd, shell=True)
                    with open(outputPath, "a") as outputFile:
                        outputFile.write(file + "\t\tdiff\n")
                        diffNum += 1
                else:
                    cmd = "del " + target_spice
                    subprocess.run(cmd, shell=True)
                    print(f"{file}.cir simulation failed and {file}.cir ltps simulation failed")
                    with open(outputPath, "a") as outputFile:
                        outputFile.write(file + "\t\tcrash\n")
        except subprocess.TimeoutExpired:
            cmd = "TASKKILL /F /IM ngspice.exe /T"
            subprocess.run(cmd, shell=True)
            with open(outputPath, "a") as outputFile:
                outputFile.write(file + "\t\ttimeout\n")
            if os.path.exists(os.path.join(inputPath, "spice.rc")):
                cmd = "del " + os.path.join(inputPath, "spice.rc")
                subprocess.run(cmd, shell=True)
            continue
        except FileNotFoundError as e:
            print(f"Error: {e}")
            with open(outputPath, "a") as outputFile:
                outputFile.write(file + "\t\tcopy_error\n")
            continue

print("共发现" + str(diffNum) + "个不同！！！")
end_time = time.time()
run_time = end_time - start_time
print(f"run time = {run_time}s")
"""