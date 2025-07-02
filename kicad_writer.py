#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path
import os
import traceback
import uuid
import random
import re
import sexpr
from diagram import Diagram, DiagramSymbol, DiagramWire


class KicadWriter(object):

    def __init__(self, filename: str, reuse_data=None):
        self.filename = filename
        self.spice_primitive_cache = None  # Legacy cache (optional now)
        self.assignment_count = 0  # Counter for assignments
        self.spice_assignments = {}  # Store spice_primitive per symbol UUID
        self.spice_command = None  # Store the selected SPICE command
        self.reuse_data = reuse_data  # Data from base schematic to reuse (optional)
        return


    def write(self, dia: Diagram):
        with open(self.filename, "w") as f:
            sch = self.gen(dia)
            content = sexpr.format_sexp(
                sexpr.build_sexp(sch),
                max_nesting=4
            )
            f.write(content)
        return

    def gen(self, dia: Diagram):
        sch = [
            "kicad_sch",
            ["version", "20231120"],
        ]
        sch.append(["generator", "eeschema"])
        uid = uuid.uuid4()
        muuid = ["uuid", uid]
        sch.append(muuid)
        sch.append(["paper", "\"A4\""])

        # 将符号库写入电路图文件
        sx = [
            "lib_symbols",
        ]
        for dsym in dia.symbols:
            sx.append(self.get_symbol_sexpr(dsym))
        sch.append(sx)

        # 对元器件进行连线
        for wire in dia.wires:
            ws = self.get_wire_sexpr(wire)
            sch.append(ws)

        # 添加仿真命令，比如瞬态、AC等
        sch.append(self.get_spice_order(dia))

        for dsym in dia.symbols:
            if dsym.name == "SW_Push":
                sch.append(self.add_sw_model(dsym))

        # 添加接地引脚

        # sheet
        sheet = [
            "sheet_instances",
            ["path \"/\"",
             ["page", "\"1\""]
             ],
        ]
        sch.append(sheet)

        # 生成元器件实例
        for dsym in dia.symbols:
            ds = self.get_instance_sexpr(dsym)
            sch.append(ds)

        # 写符号实例（电路图文件结尾）
        symbolinstance = [
            "symbol_instances",
        ]
        for dsym in dia.symbols:
            symbolins = []
            symbolins.append('path "/{}"'.format(dsym.uuid))
            symbolins.append([
                "reference",
                '"{}"'.format(dsym.get_prop("Reference"))
            ])
            symbolins.append(["unit", "1"])
            symbolins.append([
                "value",
                '"{}"'.format(dsym.get_prop("Value"))
            ])
            symbolins.append([
                "footprint",
                '"{}"'.format(dsym.get_prop("Footprint"))
            ])
            symbolinstance.append(symbolins)
        sch.append(symbolinstance)
        return sch

    def get_spice_order(self, dia: Diagram):
        if self.reuse_data and "spice_command" in self.reuse_data:
            spiceOrderStr = self.reuse_data["spice_command"]
        else:
            voltage_sources = [
                dsym.get_prop("Reference")
                for dsym in dia.symbols
                if dsym.symbol.name == "VSOURCE"
            ]
            if not voltage_sources:
                voltage_sources = ["V1"]

            spice_commands = [
                ".TRAN 1m 10m",
                ".AC DEC 20 1 10Meg",
                ".DC {} 0 5 0.1",
                ".OP"
            ]
            selected_command = random.choice(spice_commands)
            if selected_command.startswith(".DC"):
                selected_voltage = random.choice(voltage_sources)
                spiceOrderStr = selected_command.format(selected_voltage)
            else:
                spiceOrderStr = selected_command
            self.spice_command = spiceOrderStr  # Store for reuse

        spiceOrder = ["text"]
        spiceOrder.append("\"" + spiceOrderStr + "\"")
        spiceOrder.append(["at", "170 115 0"])
        spiceOrder.append(["effects", ["font", ["size 1.27 1.27"]], ["justify left bottom"]])
        spiceOrder.append(["uuid", uuid.uuid4()])
        return spiceOrder


    def add_sw_model(self, dsym: DiagramSymbol):
        assert dsym.name == "SW_Push"
        # 临时添加开关的spice模型
        spiceOrdernew = ["text"]
        vt = 10
        if "vt" in dsym.opts:
            vt = dsym.opts["vt"]
        spiceOrderStrnew = ".model sw_push{} sw(vt={} vh=0.2 ron=1 roff=10k)".format(
            # 开关名称
            dsym.index,
            # dsym.symbol.properties[0].value,
            # vt 电压值
            vt
        )
        spiceOrdernew.append("\"" + spiceOrderStrnew + "\"")
        TextPositionnew = "67.31 38.1 0"
        # 文本的位置，以后看情况在确定是否需要改动
        spiceOrdernew.append(["at", TextPositionnew])
        spiceOrdernew.append(["effects",
                              ["font",
                               ["size 1.27 1.27"]],
                              ["justify left bottom"],
                              ])
        UUIDnew = uuid.uuid4()
        spiceOrdernew.append(["uuid", UUIDnew])
        return spiceOrdernew

    def get_symbol_sexpr(self, dsym: DiagramSymbol):
        symbol = dsym.symbol
        # add header
        full_name = symbol.quoted_string("{}".format(
            symbol.libname + ":" + symbol.name
        ))
        sx = ["symbol", full_name]
        if symbol.extends:
            sx.append(["extends", symbol.quoted_string(symbol.extends)])

        pn = ["pin_names"]
        if symbol.pin_names_offset != 0.508:
            pn.append(["offset", symbol.pin_names_offset])
        if symbol.hide_pin_names:
            pn.append("hide")
        if len(pn) > 1:
            sx.append(pn)

        sx.append(["in_bom", "yes" if symbol.in_bom else "no"])
        sx.append(["on_board", "yes" if symbol.on_board else "no"])
        if symbol.is_power:
            sx.append(["power"])
        if symbol.hide_pin_numbers:
            sx.append(["pin_numbers", "hide"])

        # add properties
        for prop in symbol.properties:
            sx.append(prop.get_sexpr())

        # add units
        for d in range(0, symbol.demorgan_count + 1):
            for u in range(0, symbol.unit_count + 1):
                hdr = symbol.quoted_string("{}_{}_{}".format(symbol.name, u, d))
                sx_i = ["symbol", hdr]
                for pin in (
                        symbol.arcs
                        + symbol.circles
                        + symbol.texts
                        + symbol.rectangles
                        + symbol.polylines
                        + symbol.pins
                ):
                    if pin.is_unit(u, d):
                        sx_i.append(pin.get_sexpr())

                if len(sx_i) > 2:
                    sx.append(sx_i)
        return sx

    def get_wire_sexpr(self, wire: DiagramWire):
        ssx = [
            "wire",
        ]
        temp = [
            "pts",
            # ["xy", str(PIN[0][0]) + " " + str(PIN[0][1])],
            # ["xy", str(PIN[1][0]) + " " + str(PIN[1][1])],
            ["xy", wire.from_.pos[0], wire.from_.pos[1]],
            ["xy", wire.to_.pos[0], wire.to_.pos[1]],
        ]
        ssx.append(temp)
        stk = [
            "stroke",
            ["width", "0"],
            ["type", "default"],
            ["color", "0 0 0 0"],
        ]
        ssx.append(stk)
        ssx.append(["uuid", str(uuid.uuid4())])
        return ssx

    def get_property_sexpr(self, prop, sympos, effects: bool = False):
        sx = ["property",
              prop.quoted_string(prop.name),
              prop.quoted_string(prop.value),
              ["id", prop.idd],
              ["at",
               prop.posx + sympos[0],
               prop.posy + sympos[1],
               prop.rotation + sympos[2]],
              ]
        # Footprint和Datasheet需要effects
        if effects:
            sx.append(prop.effects.get_sexpr())
        return sx

    def get_instance_sexpr(self, dsym: DiagramSymbol):
        symbol: DiagramSymbol = dsym.symbol
        full_name = symbol.quoted_string(
            "{}:{}".format(symbol.libname, symbol.name)
        )
        sx = ["symbol", ["lib_id", full_name]]
        sx.append(["at", *dsym.pos])
        sx.append(["unit", 1])

        sx.append(["in_bom", "yes" if symbol.in_bom else "no"])
        sx.append(["on_board", "yes" if symbol.on_board else "no"])
        sx.append(["fields_autoplaced"])
        # 给元器件唯一标识
        sx.append(["uuid", dsym.uuid])

        # properties
        for prop in symbol.properties:
            effect = False
            if prop.name == "Footprint" and prop.name == "Footprint":
                effect = True
            if prop.name == "Reference" or prop.name == "Value" or prop.name == "Footprint" or prop.name == "Datasheet":
                sx.append(self.get_property_sexpr(prop, dsym.pos, effect))

        ## 如果元器件不是接地，则需要添加相关仿真属性
        if symbol.name != "0":
            self.addSpiceProperty(sx, dsym)

        # add pins 并添加uuid
        for pin in symbol.pins:
            pinuuid = uuid.uuid4()
            ssx = ["pin", '"{}"'.format(pin.number),
                   ["uuid", pinuuid],
                   ]
            sx.append(ssx)

        return sx


    def addSpiceProperty(self,sx, dsym: DiagramSymbol):
        symbol = dsym.symbol
        SymbolPosition = dsym.pos
        # 排除虚拟符号
        if hasattr(symbol, "is_virtual") and symbol.is_virtual:
            print(f"Skipping virtual symbol: {symbol.name}")
            return
        # 每两次调用为一组，组内使用相同值
        self.assignment_count += 1
        # 如果有 reuse_data，则从中提取 Spice_Primitive 和 Spice_Model
        if self.reuse_data and dsym.uuid in self.reuse_data.get("spice_assignments", {}):
            spice_primitive = self.reuse_data["spice_assignments"][dsym.uuid]["spice_primitive"]
            spice_model = self.reuse_data["spice_assignments"][dsym.uuid]["spice_model"]
        else:
            if symbol.properties:
                spice_primitive = symbol.properties[0].value[0]
            else:
                spice_primitive = symbol.name[0] if symbol.name else "X"

            # 处理 Spice_Model
            if "spice_value" in dsym.opts:
                spice_model = dsym.opts["spice_value"]
            else:
                if symbol.name in ["R", "R_Variable", "R_Photo"]:
                    spice_model = str(random.randint(1, 1000))  # 设置电阻值
                elif symbol.name in ["CAP"]:
                    spice_model = str(random.randint(1, 10))  # 设置电容值
                elif symbol.name in ["INDUCTOR"]:
                    spice_model = str(random.randint(1, 100))  # 设置电感值
                elif symbol.name in ["VSOURCE"]:
                    if "type" in dsym.opts and dsym.opts["type"] == "pos":  # 正电源
                        spice_model = "dc 15"  # 设置 +15V
                    elif "type" in dsym.opts and dsym.opts["type"] == "neg":  # 负电源
                        spice_model = "dc -15"  # 设置 -15V
                    else:
                        # 主电路电源，随机设置 1~10V
                        spice_model = "dc " + str(random.randint(1, 10))
                elif symbol.name == "DIODE":
                    spice_model = "1N3491"
                elif symbol.name == "LED":
                    spice_model = "A1SS-O612_VFBIN_D"
                elif symbol.name == "Q_PJFET_DGS":
                    spice_model = "DMG4435SSS"
                elif symbol.name == "Q_NIGBT_CEG":
                    spice_model = "APT100G2"
                elif symbol.name == "OP07":
                    spice_model = "OP07"
                elif symbol.name == "STM32F103C8Tx":
                    spice_model = "STM32F103C8Tx"

            # 存储 Spice_Primitive 和 Spice_Model
            self.spice_assignments[dsym.uuid] = {
                "spice_primitive": spice_primitive,
                "spice_model": spice_model
            }

        print(
            f"spice_primitive={spice_primitive}, spice_model={spice_model} (assignment_count={self.assignment_count}, uuid={dsym.uuid})")


        if symbol.name == "Q_PJFET_DGS":
            ## 目前除了GND的reference的值是“#GND‘,其它元器件的Reference的值与spice_Pcirmitive的值是一样的，都用单个字符表示
            spiceSex1 = [
                "property",
                "\"" + "Spice_Primitive" + "\"",
                "\"" + "X" + "\"",  ## 获取Reference的值，不要后面的顺序号,这就可以做为Spice_Primitive的值
            ]
        else:
            spiceSex1 = [
                "property",
                "\"" + "Spice_Primitive" + "\"",
                "\"" + symbol.properties[0].value[0] + "\"",  ## 获取Reference的值，不要后面的顺序号,这就可以做为Spice_Primitive的值
            ]

        spiceSex1.append(["id", "4"], )
        spiceSex1.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
        spiceSex1.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了

        sx.append(spiceSex1)

        # 添加 "Spice_Model"
        spiceSex2 = [
            "property",
            "\"Spice_Model\"",
            f"\"{spice_model}\""
        ]
        spiceSex2.append(["id", "5"])
        spiceSex2.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]])
        spiceSex2.append(symbol.properties[3].effects.get_sexpr())
        sx.append(spiceSex2)

        ## 添加"Spice_Netlist_Enabled"
        spiceSex3 = [
            "property",
            "\"" + "Spice_Netlist_Enabled" + "\"",
            "\"" + "Y" + "\"",
        ]
        spiceSex3.append(["id", "6"], )
        spiceSex3.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
        spiceSex3.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了

        sx.append(spiceSex3)

        ## 有源器件需要给模型添加spice模型
        if symbol.name == "DIODE":
            ## 添加"Spice_Lib_File"属性
            spiceSex4 = [
                "property",
                "\"" + "Spice_Lib_File" + "\"",
            ]
            ## 这个是给元器件选择实际模型的时候所在库的位置，目前先根据元器件都写死，之后再看如何动态选择等
            spiceLib = "D:\spice_lib\diode.lib"
            spiceSex4.append("\"" + spiceLib + "\"")
            spiceSex4.append(["id", "7"], )
            spiceSex4.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
            spiceSex4.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了
            sx.append(spiceSex4)
        if symbol.name == "LED":
            ## 添加"Spice_Lib_File"属性
            spiceSex4 = [
                "property",
                "\"" + "Spice_Lib_File" + "\"",
            ]
            spiceLib = "D:\spice_lib\LED.mod"
            # spiceLib = os.path.join('D:','spice_lib','basic_models','LED','SnapLED150.mod')
            spiceSex4.append("\"" + spiceLib + "\"")
            spiceSex4.append(["id", "7"], )
            spiceSex4.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
            spiceSex4.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了
            sx.append(spiceSex4)
        if symbol.name == "Q_PJFET_DGS":
            ## 添加"Spice_Lib_File"属性
            spiceSex5 = [
                "property",
                "\"" + "Spice_Lib_File" + "\"",
            ]
            ## 这个是给元器件选择实际模型的时候所在库的位置，目前先根据元器件都写死，之后再看如何动态选择等
            spiceLib = "D:\spice_lib\Diodes.lib"
            spiceSex5.append("\"" + spiceLib + "\"")
            spiceSex5.append(["id", "7"], )
            spiceSex5.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
            spiceSex5.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了
            sx.append(spiceSex5)
        if symbol.name == "Q_NIGBT_CEG":
            ## 添加"Spice_Lib_File"属性
            spiceSex5 = [
                "property",
                "\"" + "Spice_Lib_File" + "\"",
            ]
            ## 这个是给元器件选择实际模型的时候所在库的位置，目前先根据元器件都写死，之后再看如何动态选择等
            spiceLib = r"D:\spice_lib\NIGBT.LIB"
            spiceSex5.append("\"" + spiceLib + "\"")
            spiceSex5.append(["id", "7"], )
            spiceSex5.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
            spiceSex5.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了
            sx.append(spiceSex5)
        if symbol.name == "OP07":
            ## 添加"Spice_Lib_File"属性
            spiceSex5 = [
                "property",
                "\"" + "Spice_Lib_File" + "\"",
            ]
            ## 这个是给元器件选择实际模型的时候所在库的位置，目前先根据元器件都写死，之后再看如何动态选择等
            spiceLib = r"D:\spice_lib\Op07.mod"
            spiceSex5.append("\"" + spiceLib + "\"")
            spiceSex5.append(["id", "7"], )
            spiceSex5.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
            spiceSex5.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了
            sx.append(spiceSex5)
            spiceSex7 = [
                "property",
                "\"" + "Spice_Node_Sequence" + "\"",
            ]
            NodeSequence = "1,2,3,4,5,6,7"  # 目前固定的这个模型引脚顺序为1,2,3,4,5,6,7
            spiceSex7.append("\"" + NodeSequence + "\"")
            spiceSex7.append(["id", "9"], )
            spiceSex7.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
            spiceSex7.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了
            sx.append(spiceSex7)
        if symbol.name == "STM32F103C8Tx":
            ## 添加"Spice_Lib_File"属性
            spiceSex5 = [
                "property",
                "\"" + "Spice_Lib_File" + "\"",
            ]
            ## 这个是给元器件选择实际模型的时候所在库的位置，目前先根据元器件都写死，之后再看如何动态选择等
            spiceLib = r"D:\spice_lib\STM32F103C8Tx.mod"
            spiceSex5.append("\"" + spiceLib + "\"")
            spiceSex5.append(["id", "7"], )
            spiceSex5.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
            spiceSex5.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了
            sx.append(spiceSex5)
            spiceSex25 = [
                "property",
                "\"" + "Spice_Node_Sequence" + "\"",
            ]
            NodeSequence = "1,2,3,4,5,6,7,8,9,10"  # 目前固定的这个模型引脚顺序
            spiceSex25.append("\"" + NodeSequence + "\"")
            spiceSex25.append(["id", "27"], )
            spiceSex25.append(["at", SymbolPosition[0], SymbolPosition[1], SymbolPosition[2]], )
            spiceSex25.append(symbol.properties[3].effects.get_sexpr())  # 与Datasheet属性的effects值一样，我们就直接用，就不进行拼接了
            sx.append(spiceSex25)


if __name__ == '__main__':
    writer = KicadWriter("test.kicad_sch")
    dia = Diagram()
    writer.write(dia)