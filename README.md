# ICSG
## [ICSG: Automated IC Schematic Generator for Error Detection in EDA Tool Chain](https://github.com/limeilin-lu/ICSG/edit/main/README.md)
**Project Structure:**
1. **sexpr.py**:S-expression.
2. **kicad_sym.py**:Express KiCad symbol library files in the form of S-expressions.
3. **kicad_selector.py**:Select component symbols.
4. **diagram.py**:Schematic Layout.
5. **kicad_writer.py**:Write to the schematic file, extract symbol information via S-expressions, configure simulation commands, parameters, and models, and generate a simulation-ready circuit diagram.
6. **loop_generator.py**:Generate circuit schematics and variant schematics.
7. **SchematicToNetlist.py**:Convert the schematic into a netlist using KiCad.
8. **flip_pins.py**:Address the issue of pin symmetry.
9. **ic_constraints.py**:Pin constraints.
10. **parallel_diagram.py**:Parallel operation.
11. **subcircuit_generator.py**:Series subcircuit function.
12. **unused_pins_handler.py**:Handle unconnected pins.
13. **utils.py**:Common function.
14. **spcie.rc**:Configure simulation mode.
15. **kicad_sym**:This folder contains the official KiCad symbol library.
16. **aoutput**:This folder stores the simulation results of the schematic.
17. **Simulation**:All source code files (.py) in this folder are for simulation operations of various NGspice modes.
18. **conf1.txt and conf2.txt**:Configuration file.
***
### Environment Setup:
Configure the paths in each source code file (.py) to enable execution.
***
***
### Experiment
Configure the required component types in conf1.txt and set the selection probabilities for each component type in conf2.txt. Then, run loop_generator.py to generate schematics and their variant schematics. Next, execute SchematicToNetlist.py to convert the schematics into netlists. Select an appropriate simulation mode and perform the simulation in the corresponding XTesting.py. Finally, review the simulation results in the aoutput folder.
***

### Reported bugs
Our reported bugs is in [Bugs](https://github.com/limeilin-lu/ICSG/blob/main/reported-bugs.md).You can visit the websites of NGspice, KiCad, and LTspice to reproduce these errors.
