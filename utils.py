import random

from parallel_diagram import ParallelDiagram
from diagram import DiagramPin


class UTILS:
    def __init__(self, dia, loop_generator):

        self.dia = dia
        self.loop_generator = loop_generator

    def add_parallel_connection(self, pin1: DiagramPin, pin2: DiagramPin):
        parallel_dia = ParallelDiagram(self.dia)
        parallel_dia.create_wire(pin1, pin2)
        pin1.set_status(True)
        pin2.set_status(True)
        print(f"Parallel connection created between {pin1.sym.name}:{pin1.pin.name} and {pin2.sym.name}:{pin2.pin.name}.")

    def process_delayed_connections(self):
        for pin1, _ in self.loop_generator.delayed_parallel_connections:
            available_pins = [
                dp for sym in self.dia.symbols for dp in sym.pins
                if dp != pin1
            ]
            if available_pins:
                target_pin = random.choice(available_pins)
                print(f"Available pins: {[f'{p.sym.name}:{p.pin.name}' for p in available_pins]}")
                print(f"Selected target pin: {target_pin.sym.name}:{target_pin.pin.name}")
                self.add_parallel_connection(pin1, target_pin)
            else:
                print(f"No available pins to connect for {pin1.sym.name}:{pin1.pin.name}. Skipping.")
        self.loop_generator.delayed_parallel_connections.clear()