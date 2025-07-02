import random  # 修改为标准模块导入方式
from utils import UTILS
from diagram import DiagramSymbol  # 根据需要导入定义

class ICConstraints:
    def __init__(self, dia, selector, dground, ic_pins_model, utils):
        self.dia = dia
        self.selector = selector
        self.dground = dground
        self.ic_pins_model = ic_pins_model
        self.utils = utils  # 使用传入的 UTILS 实例


    def connect_ic(self, dsym):
        """针对 IC 元器件的特殊引脚约束处理"""
        # 检查是否需要正电源和负电源
        global dsym_pos, dsym_neg
        # 正电源引脚列表
        positive_power_pins = ["V+", "Vs+", "VCC", "VDD", "VBAT", "VDDA"]
        # 负电源引脚列表
        negative_power_pins = ["V-", "Vs-", "VEE", "VSS"]
        # 接地引脚列表
        ground_pins = ["GND", "VSSA"]

        # 检测正电源引脚
        pos_power_count = sum(
            1 for pin in dsym.pins
            if pin.pin.etype == "power_in" and pin.pin.name in positive_power_pins
        )
        has_positive_power = pos_power_count > 0
        multiple_positive_power = pos_power_count >= 2

        # 检测负电源引脚（排除 STM32F103C8Tx 的 VSS）
        neg_power_count = sum(
            1 for pin in dsym.pins
            if pin.pin.etype == "power_in" and
            (pin.pin.name in ["V-", "Vs-", "VEE"] or
             (pin.pin.name == "VSS" and dsym.symbol.name != "STM32F103C8Tx"))
        )
        has_negative_power = neg_power_count > 0
        multiple_negative_power = neg_power_count >= 2

        # 检测接地引脚（包括 STM32F103C8Tx 的 VSS）
        ground_count = sum(
            1 for pin in dsym.pins
            if pin.pin.etype == "power_in" and
            (pin.pin.name in ground_pins or
             (pin.pin.name == "VSS" and dsym.symbol.name == "STM32F103C8Tx"))
        )
        multiple_ground = ground_count >= 2

        # 如果既没有正电源也没有负电源，则直接返回
        if not has_positive_power and not has_negative_power:
            print(f"No power pins found for {dsym.symbol.name}. Skipping power source addition.")
            return

        # 为每个 IC 创建独立的正电源符号（仅在需要时添加）
        if has_positive_power:
            vsource_pos = self.selector.select("VSOURCE")
            if not vsource_pos:
                raise Exception("Error: Unable to find VSOURCE for positive power connections.")
            dsym_pos = self.dia.add_symbol(vsource_pos)
            dsym_pos.opts["type"] = "pos"
            self.dia.add_wire(dsym_pos.pins[0], self.dground.pins[0])  # 正电源接地

        # 为每个 IC 创建独立的负电源符号（仅在需要时添加）
        if has_negative_power:
            vsource_neg = self.selector.select("VSOURCE")
            if not vsource_neg:
                raise Exception("Error: Unable to find VSOURCE for negative power connections.")
            dsym_neg = self.dia.add_symbol(vsource_neg)
            dsym_neg.opts["type"] = "neg"
            self.dia.add_wire(dsym_neg.pins[0], self.dground.pins[0])  # 负电源接地
        # 遍历元器件的所有引脚，根据引脚类型和名称进行处理
        for pin in dsym.pins:
            print(f"Processing pin: {pin.pin.name}, type: {pin.pin.etype}, symbol: {dsym.symbol.name}")

            # 根据引脚类型调用对应的处理逻辑
            if pin.pin.etype == "input":
                elif pin.pin.name == "CKEN":
                    self.handle_cken_pins(dsym, pin)

            elif pin.pin.etype == "passive":
                if pin.pin.name in ["RG", "Rg"]:
                    self.handle_rg_pin(dsym, pin)

            elif pin.pin.etype == "output":
                if pin.pin.name == "Cout":
                    self.handle_cout_pin(dsym, pin)

            elif pin.pin.etype == "power_in":
                # 处理正电源引脚
                if pin.pin.name in positive_power_pins:
                    if multiple_positive_power:
                        self.dia.add_wire(pin, dsym_pos.pins[1])  # 连接到同一个正电源
                    else:
                        self.dia.add_wire(pin, dsym_pos.pins[1])  # 单个引脚也连接正电源

                # 处理负电源引脚
                elif (pin.pin.name in ["V-", "Vs-", "VEE"] or
                      (pin.pin.name == "VSS" and dsym.symbol.name != "STM32F103C8Tx")):
                    if multiple_negative_power:
                        self.dia.add_wire(pin, dsym_neg.pins[1])  # 连接到同一个负电源
                    else:
                        self.dia.add_wire(pin, dsym_neg.pins[1])  # 单个引脚也连接负电源

                # 处理接地引脚
                elif (pin.pin.name in ground_pins or
                      (pin.pin.name == "VSS" and dsym.symbol.name == "STM32F103C8Tx")):
                    if multiple_ground:
                        self.dia.add_wire(pin, self.dground.pins[0])  # 连接到同一个接地
                    else:
                        self.dia.add_wire(pin, self.dground.pins[0])  # 单个引脚也接地

            elif pin.pin.etype == "no_connect":
                pin.set_status(True)  # 设置为不连接


    def handle_rg_pin(self, dsym, pin):
        # 获取所有 RG/Rg 引脚
        rg_pins = [p for p in dsym.pins if p.pin.name in ["RG", "Rg"]]

        # 确保只处理一次 RG 引脚对
        if len(rg_pins) == 2 and not hasattr(dsym, "rg_connected"):  # 增加标记，防止重复处理
            # 添加电阻 R 串联两个 RG 引脚
            resistor = self.selector.select("R")
            if resistor:
                res_dsym = self.dia.add_symbol(resistor)
                res_dsym.is_ic_pins_model = True  # 标记为 ic_pins_model 的元器件
                self.dia.add_wire(rg_pins[0], res_dsym.pins[0])  # 串联第一个 RG/Rg 引脚
                self.dia.add_wire(res_dsym.pins[1], rg_pins[1])  # 串联第二个 RG/Rg 引脚
                dsym.rg_connected = True  # 设置标记，表示已经处理过 RG 引脚
        elif len(rg_pins) == 1:  # 如果只有一个 RG/Rg 引脚
            # 添加电阻 R 串联
            resistor = self.selector.select("R")
            if resistor:
                res_dsym = self.dia.add_symbol(resistor)
                res_dsym.is_ic_pins_model = True  # 标记为 ic_pins_model 的元器件
                self.dia.add_wire(rg_pins[0], res_dsym.pins[0])  # 串联 RG/Rg 引脚
                # 电阻的另一个引脚随机选择接地或并联到电路中的其他引脚
                if random.choice([True, False]):
                    self.dia.add_wire(res_dsym.pins[1], self.dground.pins[0])  # 接地
                else:
                    # 将并联操作记录到队列中
                    self.utils.loop_generator.delayed_parallel_connections.append((res_dsym.pins[1], "parallel"))


    def handle_cout_pin(self, dsym, pin):
        print(f"Setting Cout pin of {dsym.symbol.name} to no connection.")
        pin.set_status(True)  # Cout 引脚设置为不连接


    def handle_cken_pins(self, dsym, pin):
        print(f"Connecting CKEN pin of {dsym.symbol.name} to ground.")
        self.dia.add_wire(pin, self.dground.pins[0])  # CKEN 引脚接地

