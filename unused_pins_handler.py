import random
import importlib
random = importlib.import_module("random")
from subcircuit_generator import *
from utils import *
from flip_pins import FlipPins  # 确保正确导入 FlipPins 类

class UnusedPinsHandler:
    def __init__(self, dia, ic_module, dground, selector, loop_generator, writer):
        self.dia = dia
        self.ic_module = ic_module
        self.dground = dground
        self.selector = selector
        self.utils = UTILS(self.dia, loop_generator)  # 传递 loop_generator
        self.writer = writer  # Store the KicadWriter instance
        self.subcircuit_generator = SubcircuitGenerator(dia, selector, dground, self, self.writer)
        self.flip_pins = FlipPins()  # 添加 FlipPins 实例

    def handle_unused_pins(self):
        """处理 IC 模块中未连接的引脚"""
        # 定义模拟 IC 模块的类型
        analog_ic_modules = ["OP07"]
        # 定义所有 IC 模块类型（包含模拟和数字）
        ic_module = analog_ic_modules + ["STM32F103C8Tx"]  # 数字 IC 示例

        special_components = ["QNPN"]  # 针对 QNPN 的特殊处理

        # 排除特殊引脚
        excluded_pins = {"RG", "Rg", "CKEN",  "Cout"}

        for dsym in self.dia.symbols:
            # 仅处理 IC 元器件
            if dsym.symbol.name not in ic_module:
                continue

            # 跳过来自 ic_pins_model 的元器件
            if hasattr(dsym, "is_ic_pins_model") and dsym.is_ic_pins_model:
                continue

            for pin in dsym.pins:
                # 跳过已连接的引脚或特殊引脚
                if pin.status or pin.pin.name in excluded_pins:
                    continue

                # 随机决定是否连接
                if random.choice([True, False]):
                    # 寻找目标引脚（允许目标引脚已连接或未连接）
                    available_symbols = [sym for sym in self.dia.symbols if any(sym.pins)]  # 所有有引脚的元器件
                    if not available_symbols:
                        pin.set_status(True)  # 如果没有可用符号，直接标记为已使用
                        continue

                    # 随机选择一个目标元器件
                    target_symbol = random.choice(available_symbols)
                    target_pins = target_symbol.pins  # 获取目标元器件的所有引脚
                    if not target_pins:
                        pin.set_status(True)  # 如果目标元器件没有引脚，直接标记为已使用
                        continue

                    # 随机选择一个目标引脚
                    target_pin = random.choice(target_pins)
                    # 如果目标引脚属于 QNPN 元器件，则对 QNPN 进行对称翻转
                    if target_pin.sym.symbol.name in special_components:
                        self.flip_pins.flip_symmetric_pins(target_pin.sym)

                    # 判断引脚类型并处理连接逻辑
                    pin_name = pin.pin.name
                    target_pin_name = target_pin.pin.name
                    pin_is_output = pin.pin.etype == "output"  # 假设 pin.pin.etype 表示引脚类型
                    target_is_input = target_pin.pin.etype == "input"
                    pin_is_input = pin.pin.etype == "input"
                    target_is_output = target_pin.pin.etype == "output"
                    is_analog_ic = dsym.symbol.name in analog_ic_modules  # 判断是否为模拟 IC

                    # 仅对模拟 IC 的输出和输入引脚应用特殊逻辑
                    if is_analog_ic and pin_is_output and target_is_input and target_pin.sym == dsym:  # 输出连接到同一元器件的输入
                        if pin_name == "-" and target_pin_name == "+":
                            # 条件1：输出-到输入+，串联电阻
                            res = self.selector.select("R")  # 添加电阻
                            resistor = self.dia.add_symbol(res)
                            self.dia.add_wire(pin, resistor.pins[0])
                            if not target_pin.status:
                                self.dia.add_wire(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (output) to {target_pin_name} (input) via resistor in series.")
                            else:
                                self.utils.add_parallel_connection(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (output) to {target_pin_name} (input, connected) via resistor in parallel.")
                        elif pin_name == "-" and target_pin_name == "-":
                            # 条件2：输出-到输入-，取消连接
                            print(f"Skipped connection from {pin_name} (output) to {target_pin_name} (input).")
                            continue
                        elif pin_name == "+" and target_pin_name == "+":
                            # 条件3：输出+到输入+，取消连接
                            print(f"Skipped connection from {pin_name} (output) to {target_pin_name} (input).")
                            continue
                        elif pin_name == "+" and target_pin_name == "-":
                            # 条件4：输出+到输入-，串联电阻
                            res = self.selector.select("R")  # 添加电阻
                            resistor = self.dia.add_symbol(res)
                            self.dia.add_wire(pin, resistor.pins[0])
                            if not target_pin.status:
                                self.dia.add_wire(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (output) to {target_pin_name} (input) via resistor in series.")
                            else:
                                self.utils.add_parallel_connection(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (output) to {target_pin_name} (input, connected) via resistor in parallel.")
                        elif pin_name == "~" and target_pin_name == "-":
                            # 条件5：输出~到输入-，串联电阻
                            res = self.selector.select("R")  # 添加电阻
                            resistor = self.dia.add_symbol(res)
                            self.dia.add_wire(pin, resistor.pins[0])
                            if not target_pin.status:
                                self.dia.add_wire(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (output) to {target_pin_name} (input) via resistor in series.")
                            else:
                                self.utils.add_parallel_connection(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (output) to {target_pin_name} (input, connected) via resistor in parallel.")
                        elif pin_name == "~" and target_pin_name == "+":
                            # 条件6：输出~到输入+，取消连接
                            print(f"Skipped connection from {pin_name} (output) to {target_pin_name} (input).")
                            continue
                        elif pin_name == "FB" and target_pin_name == "+":
                            # 条件7：输出FB到输入+，取消连接
                            print(f"Skipped connection from {pin_name} (output) to {target_pin_name} (input).")
                            continue
                        elif pin_name == "FB" and target_pin_name == "-":
                            # 条件8：输出FB到输入-，串联电阻
                            res = self.selector.select("R")  # 添加电阻
                            resistor = self.dia.add_symbol(res)
                            self.dia.add_wire(pin, resistor.pins[0])
                            if not target_pin.status:
                                self.dia.add_wire(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (output) to {target_pin_name} (input) via resistor in series.")
                            else:
                                self.utils.add_parallel_connection(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (output) to {target_pin_name} (input, connected) via resistor in parallel.")
                        else:
                            self._default_connection(pin, target_pin)
                    # 处理模拟 IC 输入引脚的情况（反向条件）
                    elif is_analog_ic and pin_is_input and target_is_output and target_pin.sym == dsym:
                        if pin_name == "+" and target_pin_name == "-":
                            # 输入+到输出-，串联电阻
                            res = self.selector.select("R")  # 添加电阻
                            resistor = self.dia.add_symbol(res)
                            self.dia.add_wire(pin, resistor.pins[0])
                            if not target_pin.status:
                                self.dia.add_wire(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (input) to {target_pin_name} (output) via resistor in series.")
                            else:
                                self.utils.add_parallel_connection(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (input) to {target_pin_name} (output, connected) via resistor in parallel.")
                        elif pin_name == "-" and target_pin_name == "-":
                            # 输入-到输出-，取消连接
                            print(f"Skipped connection from {pin_name} (input) to {target_pin_name} (output).")
                            continue
                        elif pin_name == "+" and target_pin_name == "+":
                            # 输入+到输出+，取消连接
                            print(f"Skipped connection from {pin_name} (input) to {target_pin_name} (output).")
                            continue
                        elif pin_name == "-" and target_pin_name == "+":
                            # 输入-到输出+，串联电阻
                            res = self.selector.select("R")  # 添加电阻
                            resistor = self.dia.add_symbol(res)
                            self.dia.add_wire(pin, resistor.pins[0])
                            if not target_pin.status:
                                self.dia.add_wire(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (input) to {target_pin_name} (output) via resistor in series.")
                            else:
                                self.utils.add_parallel_connection(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (input) to {target_pin_name} (output, connected) via resistor in parallel.")
                        elif pin_name == "-" and target_pin_name == "~":
                            # 输入-到输出~，串联电阻
                            res = self.selector.select("R")  # 添加电阻
                            resistor = self.dia.add_symbol(res)
                            self.dia.add_wire(pin, resistor.pins[0])
                            if not target_pin.status:
                                self.dia.add_wire(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (input) to {target_pin_name} (output) via resistor in series.")
                            else:
                                self.utils.add_parallel_connection(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (input) to {target_pin_name} (output, connected) via resistor in parallel.")
                        elif pin_name == "+" and target_pin_name == "~":
                            # 输入+到输出~，取消连接
                            print(f"Skipped connection from {pin_name} (input) to {target_pin_name} (output).")
                            continue
                        elif pin_name == "+" and target_pin_name == "FB":
                            # 输入+到输出FB，取消连接
                            print(f"Skipped connection from {pin_name} (input) to {target_pin_name} (output).")
                            continue
                        elif pin_name == "-" and target_pin_name == "FB":
                            # 输入-到输出FB，串联电阻
                            res = self.selector.select("R")  # 添加电阻
                            resistor = self.dia.add_symbol(res)
                            self.dia.add_wire(pin, resistor.pins[0])
                            if not target_pin.status:
                                self.dia.add_wire(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (input) to {target_pin_name} (output) via resistor in series.")
                            else:
                                self.utils.add_parallel_connection(resistor.pins[1], target_pin)
                                print(f"Connected {pin_name} (input) to {target_pin_name} (output, connected) via resistor in parallel.")
                        else:
                            self._default_connection(pin, target_pin)
                    else:
                        # 默认连接方式（非模拟 IC 或非输入/输出引脚）
                        self._default_connection(pin, target_pin)
                else:
                    # 随机选择是否生成子电路
                    if random.choice([True, False]):
                        self.subcircuit_generator.generate_subcircuit(pin)
                    else:
                        pin.set_status(True)

    def _default_connection(self, pin, target_pin):
        """默认的连接处理逻辑"""
        if not target_pin.status:
            # 如果目标引脚未连接，则与其串联
            self.dia.add_wire(pin, target_pin)
            print(f"Connected {pin.pin.name} (unconnected) to {target_pin.pin.name} (unconnected) in series.")
        else:
            # 如果目标引脚已连接，则与其并联
            self.utils.add_parallel_connection(pin, target_pin)
            print(f"Connected {pin.pin.name} (unconnected) to {target_pin.pin.name} (connected) in parallel.")