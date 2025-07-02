#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
from typing import List
from diagram import DiagramSymbol, DiagramPin, DiagramWire
from kicad_sym import KicadSymbol, Pin

class ParallelDiagramSymbol(DiagramSymbol):
    def __init__(self, symbol: KicadSymbol):
        super().__init__(symbol)
        self.branch_level = 0
        self.branch_position = 0
        self.is_parallel = True

class ParallelDiagram:
    def __init__(self, main_diagram):
        self.main_diagram = main_diagram
        self.symbols = []
        self.wires = []
        self.branches = []
        self.branch_count = 0
        return

    def create_symbol(self, symbol: KicadSymbol):
        dsym = ParallelDiagramSymbol(symbol)
        self.symbols.append(dsym)
        self.main_diagram.symbols.append(dsym)
        dsym.calc_pos()  # 计算符号和引脚的位置
        return dsym

    def create_wire(self, from_: DiagramPin, to_: DiagramPin):
        wire = DiagramWire(from_, to_, is_parallel=True)
        self.wires.append(wire)
        self.main_diagram.wires.append(wire)
        return wire

    def create_branch(self, start_sym: ParallelDiagramSymbol, end_sym: ParallelDiagramSymbol):
        branch = {
            'start': start_sym,
            'end': end_sym,
            'components': [],
            'level': self.branch_count
        }
        self.branches.append(branch)
        self.main_diagram.parallel_branches.append(branch)
        self.branch_count += 1

        # 更新分支中所有元件的位置
        start_sym.calc_pos()
        end_sym.calc_pos()
        for comp in branch['components']:
            comp.calc_pos()

        return branch

    def add_to_branch(self, branch, symbol: ParallelDiagramSymbol):
        symbol.branch_level = branch['level']
        symbol.branch_position = len(branch['components'])
        symbol.is_parallel = True
        branch['components'].append(symbol)

    def connect_parallel_components(self, branch, start_pin: DiagramPin, end_pin: DiagramPin):
        """连接并联分支内的组件"""
        for component in branch['components']:
            # 找到组件的输入和输出引脚
            input_pin = None
            output_pin = None
            for pin in component.pins:
                if not pin.status:
                    if pin.type() == "input":
                        input_pin = pin
                    elif pin.type() in ["aoutput", "passive"]:
                        output_pin = pin

            if input_pin and output_pin:
                # 创建并联连接
                self.create_wire(start_pin, input_pin)
                self.create_wire(output_pin, end_pin)

                # 更新引脚状态
                input_pin.status = True
                output_pin.status = True

                # 输出调试信息
                print(f"Connected parallel component: {component.name} (input -> output)")

    def add_parallel_connection(self, pin1: DiagramPin, pin2: DiagramPin):
        """
        添加并联连接，直接连接两个引脚（不生成虚拟符号）。
        """
        # 创建并联连接的两条导线
        self.create_wire(pin1, pin2)

        # 更新引脚状态
        pin1.status = True
        pin2.status = True

        # 输出调试信息
        print(f"Parallel connection created directly between {pin1.sym.name} and {pin2.sym.name}.")


if __name__ == '__main__':
    pass