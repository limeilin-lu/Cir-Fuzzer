
from diagram import DiagramSymbol


class FlipPins:
    def flip_symmetric_pins(self, dsym):
        """检查引脚是否有对称性，并翻转对称引脚"""
        pins = dsym.pins
        flipped_pins = set()
        for i, pin1 in enumerate(pins):
            if pin1 in flipped_pins:
                continue
            flipped = False
            for j, pin2 in enumerate(pins):
                if i >= j or pin2 in flipped_pins:
                    continue
                # 检查是否对称（横坐标相同，纵坐标相反）
                if pin1.pos[0] == pin2.pos[0] and pin1.pos[1] == -pin2.pos[1]:
                    # 翻转两个引脚的位置
                    pin1.pos[1], pin2.pos[1] = pin2.pos[1], pin1.pos[1]
                    flipped_pins.update([pin1, pin2])
                    flipped = True
                    print(f"Flipped symmetric pins: {pin1.pin.name} and {pin2.pin.name} in {dsym.symbol.name}")
                    break

            # 如果没有找到对称的引脚，检查是否需要翻转到下方或上方
            if not flipped:
                if pin1.pos[1] < 0:  # 引脚在下方
                    pin1.pos[1] = -pin1.pos[1]  # 翻转到上方
                    print(f"Flipped single pin: {pin1.pin.name} to top in {dsym.symbol.name}")
                elif pin1.pos[1] > 0:  # 引脚在上方
                    pin1.pos[1] = -pin1.pos[1]  # 翻转到下方
                    print(f"Flipped single pin: {pin1.pin.name} to bottom in {dsym.symbol.name}")