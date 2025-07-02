#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import traceback
import uuid
import random
from typing import List, Dict
from kicad_sym import KicadSymbol, Pin, KicadLibrary


class DiagramSymbol(object):
    def __init__(self, symbol: KicadSymbol):
        self.full_name = '{}:{}'.format(symbol.libname, symbol.name)
        self.name = symbol.name
        self.symbol: KicadSymbol = symbol
        self.pins: List[DiagramPin] = []
        self.pos = [0, 0, 0]
        self.uuid = uuid.uuid4()
        self.index = getattr(symbol, 'index', -1)  # 为虚拟符号提供默认 index 值
        self.opts = {}
        self.is_parallel = False  # 标记是否在并联分支中
        self.parallel_level = 0  # 并联层级
        self.connection_type = None  # 新增属性，用于存储连接方式
        self.gen_pin()
        return

    def get_name(self):
        return self.name


    def gen_pin(self):
        for pin in self.symbol.pins:
            dpin = DiagramPin(self, pin)
            self.pins.append(dpin)
        return

    def calc_pos(self):
        for dpin in self.pins:
            dpin.input_pos(self.pos)
        return

    def get_prop(self, name: str):
        for prop in self.symbol.properties:
            if prop.name == name:
                return prop.value
        return ""


class DiagramPin(object):
    def __init__(self, sym: DiagramSymbol, pin: Pin):
        self.pos = [pin.posx, pin.posy, pin.rotation]
        self.pin: Pin = pin
        self.sym: DiagramSymbol = sym
        self.status: bool = False
        self.parallel_connections: List[DiagramWire] = []  # 存储并联连接
        return

    def type(self):
        return self.pin.etype

    def set_status(self, status=True):
        self.status = status
        return


    def input_pos(self, pos):
        self.pos[0] += pos[0]
        self.pos[1] += pos[1]
        self.pos[2] += pos[2]
        return

    def add_parallel_connection(self, wire):
        self.parallel_connections.append(wire)


class DiagramWire(object):
    def __init__(self, from_: DiagramPin, to_: DiagramPin, is_parallel: bool = False):
        self.uuid = str(uuid.uuid4())
        self.from_: DiagramPin = from_
        self.to_: DiagramPin = to_
        self.is_parallel = is_parallel
        self.from_.set_status()
        self.to_.set_status()
        return

    def get_pos(self):
        return (self.from_.pos, self.to_.pos)


class Diagram(object):
    def __init__(self):
        self.symbols = []
        self.wires = []
        self.parallel_branches: List[Dict] = []  # 存储并联分支信息
        return

    def add_symbol(self, symbol: KicadSymbol):
        dsym = DiagramSymbol(symbol)
        self.symbols.append(dsym)
        return dsym

    def add_wire(self, from_: DiagramPin, to_: DiagramPin, is_parallel: bool = False):
        wire = DiagramWire(from_, to_, is_parallel)
        self.wires.append(wire)
        if is_parallel:
            from_.add_parallel_connection(wire)
            to_.add_parallel_connection(wire)
        return wire

    def add_parallel_branch(self, start_sym: DiagramSymbol, end_sym: DiagramSymbol):
        branch = {
            'start': start_sym,
            'end': end_sym,
            'components': [],
            'level': len(self.parallel_branches)
        }
        self.parallel_branches.append(branch)
        return branch

    def complete_position(self):
        # 基本位置计算
        num = len(self.symbols)
        sym_nd = 0
        turning_point = num / 4 + 1
        line = 0
        ptx, pty = (34, 158)

        for idx, dsym in enumerate(self.symbols):
            if sym_nd >= turning_point:
                sym_nd = 0
                line += 1
            sym_nd += 1

            # 考虑并联元件的位置偏移
            offset_x = 0
            offset_y = 0
            if dsym.is_parallel:
                offset_x = dsym.parallel_level * 10
                offset_y = dsym.parallel_level * 10

            if idx == 0:
                pass
            elif line == 0:
                pty -= sym_nd * 5
                ptx += sym_nd * 1
            elif line == 1:
                ptx += sym_nd * 5
                pty += sym_nd * 1
            elif line == 2:
                pty += sym_nd * 5
                ptx -= sym_nd * 1
            else:
                ptx -= sym_nd * 5
                pty -= sym_nd * 1

            dsym.pos[0] = ptx + offset_x
            dsym.pos[1] = pty + offset_y

        # 计算所有元件的实际位置
        for dsym in self.symbols:
            dsym.calc_pos()

        # 调整并联分支的位置
        self.arrange_parallel_branches()
        return

    def arrange_parallel_branches(self):
        for branch in self.parallel_branches:
            level = branch['level']
            for component in branch['components']:
                # 根据并联层级调整位置
                component.pos[0] += level * 20
                component.pos[1] += level * 10
                component.calc_pos()


if __name__ == '__main__':
    pass