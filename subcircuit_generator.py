
import re
from itertools import groupby
from utils import *
from diagram import *
from parallel_diagram import *
from kicad_writer import *
from flip_pins import FlipPins

class SubcircuitGenerator:
    def __init__(self, dia, selector, dground, loop_generator, writer):
        self.filp_pins = FlipPins()
        self.dia = dia
        self.selector = selector
        self.dground = dground
        self.utils = UTILS(self.dia, loop_generator)  # 传递 loop_generator
        self.writer = writer  # Store the KicadWriter instance

    def generate_subcircuit(self, target_pin: DiagramPin):
        """生成一个随机子电路，连接到指定引脚"""
        special_components = ["QNPN"]  # 针对 QNPN 的特殊处理

        # 重置目标引脚的状态为未使用
        target_pin.set_status(False)

        # 随机选择是否添加电源（最多一个电源）
        vsource = None
        if random.choice([True, False]):  # 随机决定是否添加电源
            vsource = self.selector.select("VSOURCE")
        # 元器件类型列表（包括电阻和新增元器件）
        component_types = ['R', 'R_Variable', 'R_Photo', 'CAP', "INDUCTOR",
                           "DIODE",  "LED",  "Q_PJFET_DGS", "Q_NIGBT_CEG"]
        # 轮盘赌算法生成元器件
        conf = []  # 分类文件
        with open("conf1.txt", "r") as file:
            for line in file:
                s = line.strip()
                conf.append(re.split(r" +", s))

        conf2 = []  # 概率文件
        with open("conf2.txt", "r") as file:
            for line in file:
                s = line.strip()
                conf2.append(re.split(r" +", s))

        # 分类统计
        category = [key for key, group in groupby(conf, key=lambda x: x[1])]
        subcircuit_components = []

        # 随机生成若干个元器件
        num_components = random.randint(1, 6)  # 随机生成 1 到 6 个元器件
        while len(subcircuit_components) < num_components:
            candidates_num = []
            candidates_name = []
            for cat in category:
                candidates_name.append(cat)
                for prob in conf2:
                    if cat == prob[0]:
                        candidates_num.append(float(prob[1]))
                        break

            weight_sum = sum(candidates_num)
            weight_true = random.random() * weight_sum

            selected_category = None
            for i, weight in enumerate(candidates_num):
                weight_sum -= weight
                if weight_sum <= weight_true:
                    selected_category = candidates_name[i]
                    break

            # 随机选择小类
            candidates = [c[0] for c in conf if c[1] == selected_category]
            selected = random.choice(candidates)

            # 如果选择的元器件在允许的类型中，添加到子电路
            if selected in component_types:
                component = self.selector.select(selected)
                if component:
                    subcircuit_components.append(component)

        if vsource:
            subcircuit_components.append(vsource)
        subcircuit_components.append(self.dground)

        # 创建 ParallelDiagram 实例
        parallel_dia = ParallelDiagram(self.dia)

        # 连接逻辑
        prev_pin = target_pin  # 从 ic 的目标引脚开始连接
        last_component = None  # 记录子电路的最后一个元器件
        ground_connected = False  # 标记地符号是否已连接

        for component in subcircuit_components:
            if component is None:
                print("Warning: Skipping invalid component.")
                continue
            try:
                dsym = self.dia.add_symbol(component)
            except AttributeError as e:
                print(f"Error adding symbol: {e}. Skipping component.")
                continue

            if not dsym.pins:  # 检查是否有引脚
                print(f"Warning: Symbol {dsym.name} has no pins. Skipping.")
                continue

            # 统一处理电阻和新增元器件的连接逻辑
            if dsym.symbol.name in component_types:
                if len(dsym.pins) >= 2:  # 确保至少有两个引脚
                    # 连接方式：第一个引脚连接前一个元件
                    self.dia.add_wire(prev_pin, dsym.pins[0])
                    print(f"Connected previous component to {dsym.name} pin 1.")

                    # 更新前一个引脚为当前元件的第二个引脚
                    prev_pin = dsym.pins[1]
                    last_component = dsym  # 更新最后一个元器件

                elif len(dsym.pins) == 1:  # 单引脚元件直接接地
                    self.dia.add_wire(dsym.pins[0], self.dground.pins[0])
                    print(f"Connected single-pin {dsym.name} to ground.")

            # 如果是电源，处理其特殊连接逻辑
            elif dsym.symbol.name == "VSOURCE":
                # 电源的引脚 2 接地
                self.dia.add_wire(dsym.pins[0], self.dground.pins[0])
                print(f"Connected VSOURCE pin 2 to ground.")

                # 电源的引脚 1 连接到当前子电路
                self.dia.add_wire(prev_pin, dsym.pins[1])
                print(f"Connected previous component to VSOURCE pin 1.")
                prev_pin = dsym.pins[0]  # 更新前一个引脚

            # 如果是地符号，直接连接到前一个元件
            elif dsym.symbol.name == "0":
                if not ground_connected:
                    self.dia.add_wire(prev_pin, self.dground.pins[0])
                    print("Connected the last component to ground.")
                    ground_connected = True

            # 调用 kicad_writer.py 中的 addSpiceProperty 方法设置值和模型
            self.writer.addSpiceProperty([], dsym)

        # 如果没有电源，但有其他元器件
        if not vsource and last_component:
            if random.choice([True, False]):  # 随机决定接地还是并联
                # 将最后一个元器件的一个引脚接地
                self.dia.add_wire(prev_pin, self.dground.pins[0])
                print(f"Connected last component {last_component.name} pin to ground.")
            else:
                # 随机并联到已经连成的电路中
                available_symbols = [sym for sym in self.dia.symbols if len(sym.pins) > 0]  # 确保元器件有引脚
                if available_symbols:
                    # 随机选择一个目标元器件
                    target_symbol = random.choice(available_symbols)
                    target_symbol.calc_pos()  # 更新目标元器件位置

                    # 随机选择目标元器件的一个引脚
                    target_pin = random.choice(target_symbol.pins)

                    # 创建并联连接
                    self.utils.add_parallel_connection(prev_pin, target_pin)
                    print(
                        f"Randomly connected last component {last_component.name} pin to {target_symbol.name} pin {target_pin.pin.number}.")

        # 如果没有任何元器件，直接将 ic 引脚接地
        if not subcircuit_components and not vsource:
            self.dia.add_wire(target_pin, self.dground.pins[0])

        # 设置目标引脚的状态为已使用
        target_pin.set_status(True)

        print(f"Subcircuit generation complete for OP07 pin {target_pin.pin.number}.")