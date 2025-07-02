import random
import re
from itertools import groupby
from msilib.schema import Property
import os  # Added for directory creation

from diagram import Diagram
from kicad_selector import KicadSelector
from kicad_writer import KicadWriter
from ic_constraints import ICConstraints
from parallel_diagram import *
from unused_pins_handler import UnusedPinsHandler
from flip_pins import FlipPins
from subcircuit_generator import SubcircuitGenerator
from utils import UTILS


class LoopGenerator:
    def __init__(self, selector):
        self.dia = Diagram()
        self.selector = selector
        self.ic_count = 0
        self.max_ic_count = 20
        self.utils = UTILS(self.dia, self)
        self.delayed_parallel_connections = []
        self.ground = self.selector.select("0")
        if not self.ground:
            raise Exception("Ground symbol (0) not found in libraries.")
        self.dground = self.dia.add_symbol(self.ground)
        self.main_vsource = None
        self.ic_pins_model = ['R', 'CAP', 'VSOURCE']

        # 分离模拟和数字 IC
        self.analog_ic_module = [
            "OP07"
        ]
        self.digital_ic_module = [
            "STM32F103C8Tx"
        ]
        self.ic_module = self.analog_ic_module + self.digital_ic_module
        self.basic_module = [
            'R', 'R_Variable', 'R_Photo', 'CAP', "INDUCTOR",
            "DIODE",  "LED",  "Q_PJFET_DGS",
             "Q_NIGBT_CEG"
        ]
        # Create a KicadWriter instance (use a dummy filename for now)
        self.writer = KicadWriter("temp.kicad_sch")

        # 子模块实例化
        self.ic_constraints = ICConstraints(self.dia, self.selector, self.dground, self.ic_pins_model, self.utils)
        self.parallel_diagram = ParallelDiagram(self.dia)
        self.unused_pins_handler = UnusedPinsHandler(self.dia, self.ic_module, self.dground, self.selector, self, self.writer)
        self.flip_pins = FlipPins()
        self.subcircuit_generator = SubcircuitGenerator(self.dia, self.selector, self.dground, self, self.writer)

    def gen(self, index):
        # Ensure directories exist

        # Generate the base schematic
        base_dia = self._gen_base_schematic()

        # Write base schematic and capture SPICE data
        base_writer = KicadWriter(f"./gendir/base_{index}.kicad_sch")
        base_writer.write(base_dia)
        base_spice_data = {
            "spice_assignments": base_writer.spice_assignments,
            "spice_command": base_writer.spice_command
        }

        # Generate the variant schematic based on the base
        variant_dia = self._gen_variant_schematic(base_dia)

        # Write variant schematic with reused SPICE data
        variant_writer = KicadWriter(f"./EMIgendir/variant_{index}.kicad_sch", reuse_data=base_spice_data)
        variant_writer.write(variant_dia)

        return base_dia, variant_dia

    def _gen_base_schematic(self):
    #def gen(self):
        if not self.main_vsource:
            self.main_vsource = self.selector.select("VSOURCE")
            main_vsource_dsym = self.dia.add_symbol(self.main_vsource)
            self.dia.add_wire(main_vsource_dsym.pins[0], self.dground.pins[0])

        params = {"min-component": 10, "max-component": 20}
        component_num = random.randint(params['min-component'], params['max-component'])

        components = self.select_components(component_num)
        # 确保至少包含一个 IC 元器件
        ic_included = any(comp in self.ic_module for comp in components)
        if not ic_included:
            ic_to_add = random.choice(self.ic_module)  # 随机选择一个 IC 元器件
            components.append(ic_to_add)
            print(f"Added mandatory IC component: {ic_to_add}")  # 调试信息
        self.add_components(components)

        self.connect()

        for dsym in self.dia.symbols:
            # 判断是否为基础元器件（symbol 名称是否在 basic_module 中）
            if dsym.symbol.name not in self.basic_module:
                continue

        for dsym in self.dia.symbols:
            if str(dsym.name).endswith("SOURCE"):
                self.dia.add_wire(dsym.pins[0], self.dground.pins[0])

        print("Delayed parallel connections before processing:")
        for pin1, _ in self.utils.loop_generator.delayed_parallel_connections:
            print(f"- {pin1.sym.name}:{pin1.pin.name}")

        self.utils.process_delayed_connections()

        self.unused_pins_handler.handle_unused_pins()
        self.dia.complete_position()
        return self.dia


    def _gen_variant_schematic(self, base_dia):
        variant_dia = Diagram()
        symbol_map = {}

        # Copy symbols and wires from base schematic
        for base_sym in base_dia.symbols:
            variant_sym = variant_dia.add_symbol(base_sym.symbol)
            variant_sym.pos = base_sym.pos[:]
            variant_sym.opts = base_sym.opts.copy()
            symbol_map[base_sym] = variant_sym

        for base_wire in base_dia.wires:
            from_sym = symbol_map[base_wire.from_.sym]
            to_sym = symbol_map[base_wire.to_.sym]
            from_pin = next(p for p in from_sym.pins if p.pin.number == base_wire.from_.pin.number)
            to_pin = next(p for p in to_sym.pins if p.pin.number == base_wire.to_.pin.number)
            variant_dia.add_wire(from_pin, to_pin, base_wire.is_parallel)

        # Apply flip_symmetric_pins to IC components in the variant schematic
        ic_symbols = [sym for sym in variant_dia.symbols if sym.name in self.ic_module]
        for dsym in ic_symbols:
            self.flip_pins.flip_symmetric_pins(dsym)

        # Define two mutation strategies
        def apply_static_pin_mutation():
            # Define power pin categories
            power_pins = ["V+", "Vs+", "VCC", "VDD", "VBAT", "VDDA"]
            neg_power_pins = ["V-", "Vs-", "VEE"]
            ground_pins = ["GND", "VSSA"]

            # Identify power pins after flipping
            target_pins = []
            for dsym in ic_symbols:
                for pin in dsym.pins:
                    if pin.pin.etype == "power_in":
                        if pin.pin.name in power_pins:
                            target_pins.append((dsym, pin, "pos"))
                        elif pin.pin.name in neg_power_pins or (
                                pin.pin.name == "VSS" ):
                            target_pins.append((dsym, pin, "neg"))
                        elif pin.pin.name in ground_pins or (
                                pin.pin.name == "VSS" ):
                            target_pins.append((dsym, pin, "gnd"))

            num_to_select = min(random.randint(1, 3), len(target_pins))
            selected_pins = random.sample(target_pins, num_to_select)

            offset_index = 0
            for dsym, pin, pin_type in selected_pins:
                cap_sym = self.selector.select("CAP")
                cap_dsym = variant_dia.add_symbol(cap_sym)
                cap_dsym.pos = [dsym.pos[0] + 10 + offset_index * 20, dsym.pos[1] + 10, 0]
                cap_dsym.opts["spice_value"] = "1pF"
                variant_dia.add_wire(pin, cap_dsym.pins[0])

                vsource_sym = self.selector.select("VSOURCE")
                vsource_dsym = variant_dia.add_symbol(vsource_sym)
                vsource_dsym.pos = [cap_dsym.pos[0] + 20, cap_dsym.pos[1] + 10, 0]
                if pin_type == "pos":
                    vsource_dsym.opts["spice_value"] = "dc 15"
                elif pin_type == "neg":
                    vsource_dsym.opts["spice_value"] = "dc -15"
                else:
                    vsource_dsym.opts["spice_value"] = "dc 0"
                variant_dia.add_wire(cap_dsym.pins[1], vsource_dsym.pins[1])
                variant_dia.add_wire(vsource_dsym.pins[0], variant_dia.symbols[0].pins[0])

                offset_index += 1

        def apply_non_static_pin_mutation():
            # Select a random symbol (excluding ground symbol)
            eligible_symbols = [sym for sym in variant_dia.symbols if sym.symbol.name != "0"]
            if not eligible_symbols:
                print("No eligible symbols found for non static pin mutation.")
                return

            selected_dsym = random.choice(eligible_symbols)
            # Select a random pin from the symbol
            selected_pin = random.choice(selected_dsym.pins)

            # Add a 0.1pF capacitor in parallel to the selected pin
            cap_sym = self.selector.select("CAP")
            cap_dsym = variant_dia.add_symbol(cap_sym)
            cap_dsym.pos = [selected_dsym.pos[0] + 10, selected_dsym.pos[1] + 10, 0]
            cap_dsym.opts["spice_value"] = "0.1pF"

            # Connect one end of the capacitor to the selected pin
            variant_dia.add_wire(selected_pin, cap_dsym.pins[0])
            # Connect the other end of the capacitor to ground
            variant_dia.add_wire(cap_dsym.pins[1], variant_dia.symbols[0].pins[0])

        # Randomly choose between the two mutation strategies
        mutation_strategy = random.choice(["static_pin_mutation", "non_static_pin_mutation"])
        print(f"Selected mutation strategy: {mutation_strategy}")

        if mutation_strategy == "static_pin_mutation":
            apply_static_pin_mutation()
        else:
            apply_non_static_pin_mutation()

        variant_dia.complete_position()
        return variant_dia

    def select_components(self, component_num):
        # 读取分类文件
        conf = []  # 分类文件
        with open("conf1.txt", "r") as file:
            for line in file:
                s = line.strip()
                conf.append(re.split(r" +", s))

        # 读取概率文件
        conf2 = []  # 概率文件
        with open("conf2.txt", "r") as file:
            for line in file:
                s = line.strip()
                conf2.append(re.split(r" +", s))

        # 统计分类
        category = [key for key, group in groupby(conf, key=lambda x: x[1])]
        components = []

        # 循环选择元器件
        while len(components) < component_num:
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

            if len(components) < self.max_ic_count and selected in self.ic_module:
                components.append(selected)
            elif selected in self.basic_module:
                components.append(selected)

        return components

    def add_components(self, components):
        for selected in components:
            sym = self.selector.select(selected)
            if sym:
                dsym = self.dia.add_symbol(sym)
                if selected in self.ic_module:
                    self.flip_pins.flip_symmetric_pins(dsym)
                    self.ic_constraints.connect_ic(dsym)

    def connect(self):
        # 将元器件按顺序串联形成主回路，满足电源引脚和连接顺序要求
        # 找到主电源元器件
        vsource = next((sym for sym in self.dia.symbols if sym.symbol.name == "VSOURCE"), None)
        if not vsource:
            raise Exception("Main power source not found in the circuit.")

        # 从电源的 pins[1] 开始连接
        from_pin = vsource.pins[1]  # 电源的输出引脚
        prev_dsym = vsource

        # 筛选出参与回路连接的元器件
        # 仅包含 IC 和基础元器件，排除 ic_pins_model 中的元器件
        symbols_to_connect = [
            sym for sym in self.dia.symbols
            if (
                       sym.symbol.name in [ "OP07", "STM32F103C8Tx"]  # IC 模块
                       or sym.symbol.name in [
                           'R', 'R_Variable', 'R_Photo', 'CAP', 
                           "INDUCTOR", "DIODE", "LED", "Q_PJFET_DGS",
                            "Q_NIGBT_CEG"
                       ]  # 基础元器件
               )
               and not (hasattr(sym, "is_ic_pins_model") and sym.is_ic_pins_model)  # 排除来自 ic_pins_model 的元器件
        ]

        if not symbols_to_connect:
            raise Exception("No valid components to connect in the circuit.")

        # 打乱元器件顺序以模拟随机连接
        random.shuffle(symbols_to_connect)
        print("Symbols to connect:", [sym.name for sym in symbols_to_connect])  # 调试信息

        # 找到第一个元器件的输入或被动引脚
        first_dsym = symbols_to_connect.pop(0)
        to_pin = self.find_input_or_passive_pin(first_dsym)
        if not to_pin:
            raise Exception(f"No input or passive pin found on the first component {first_dsym.name}.")
        self.dia.add_wire(from_pin, to_pin)  # 连接电源 pins[1] 到第一个元器件的引脚

        # 更新下一个起始引脚
        from_pin = self.find_alternate_pin(to_pin, first_dsym)
        prev_dsym = first_dsym

        # 遍历剩余的元器件
        for dsym in symbols_to_connect:
            # 查找当前元器件的输入或被动引脚
            to_pin = self.find_input_or_passive_pin(dsym)
            if not to_pin:
                print(f"Warning: No compatible pin on {dsym.name}. Skipping.")
                continue

            # 连接 from_pin 到 to_pin
            self.dia.add_wire(from_pin, to_pin)

            # 更新下一个起始引脚为当前元器件的另一个输出/被动引脚或输入引脚
            from_pin = self.find_alternate_pin(to_pin, dsym)
            if not from_pin:
                print(f"Warning: No alternate pin on {dsym.name}. Connection may be incomplete.")
                break
            prev_dsym = dsym

        # 将最后一个元器件直接连接到电源的 pins[0]
        self.dia.add_wire(from_pin, vsource.pins[0])

        # 将电源的 pins[0] 接地
        self.dia.add_wire(vsource.pins[0], self.dground.pins[0])

    def find_input_or_passive_pin(self, dsym: DiagramSymbol):
        """
        在目标元器件中查找输入引脚或被动引脚，优先选择输入引脚。
        - 如果没有输入引脚和被动引脚，则选择双向引脚 (bidirectional)。
        """
        # 如果是地符号，直接返回 None
        if dsym.symbol.name == "0":
            print(f"Skipping ground symbol {dsym.name}.")
            return None

        # 优先选择输入引脚，但排除 STM32F103C8Tx 的输入引脚
        for pin in dsym.pins:
            if (not pin.status and
                    pin.pin.etype == "input" ):
                return pin

        # 如果没有符合条件的输入引脚，则选择被动引脚
        for pin in dsym.pins:
            if not pin.status and pin.pin.etype == "passive":
                return pin

        # 如果没有输入引脚和被动引脚，则选择双向引脚
        for pin in dsym.pins:
            if not pin.status and pin.pin.etype == "bidirectional":
                return pin

        return None

    def find_alternate_pin(self, to_pin: DiagramPin, dsym: DiagramSymbol):
        """
        查找当前元器件的另一个未使用的输出或被动引脚：
        - 优先选择输出引脚。
        - 如果没有输出引脚，则选择被动引脚。
        - 如果没有输出或被动引脚，则选择输入引脚。
        - 如果都没有，则选择双向引脚 (bidirectional)。
        """
        # 优先选择输出引脚
        for pin in dsym.pins:
            if not pin.status and pin != to_pin and pin.pin.etype == "output":
                return pin

        # 如果没有输出引脚，则选择被动引脚
        for pin in dsym.pins:
            if not pin.status and pin != to_pin and pin.pin.etype == "passive":
                return pin

        # 如果没有输出或被动引脚，则选择输入引脚（排除 STM32F103C8Tx 的输入引脚）
        for pin in dsym.pins:
            if (not pin.status and
                    pin != to_pin and
                    pin.pin.etype == "input"):
                return pin

        # 如果没有输出、被动或符合条件的输入引脚，则选择双向引脚
        for pin in dsym.pins:
            if not pin.status and pin != to_pin and pin.pin.etype == "bidirectional":
                return pin

        return None



if __name__ == '__main__':
    selector = KicadSelector()
    selector.import_library("kicad_sym/Device.kicad_sym")
    selector.import_library("kicad_sym/Amplifier_Operational.kicad_sym")
    selector.import_library("kicad_sym/MCU_ST_STM32F1.kicad_sym")
    generator_num = 10
    for i in range(1, generator_num + 1):  # Start from 1 instead of 0
        generator = LoopGenerator(selector)
        base_dia, variant_dia = generator.gen(i)  # Pass the index i to gen