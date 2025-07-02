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
### Our Works
In electronic design automation (EDA), the design of integrated circuit (IC) and printed circuit board relies heavily on the EDA tool chain. Errors within this tool chain can result in failures with substantial cost implications across both the design and manufacturing processes. Therefore, verifying the correctness of the tool chain is crucial. An effective strategy is to automatically generate diverse circuit schematics and submit them to the EDA tool chain to detect potential issues through behavioral differences. However, previous schematic-level defect detection approaches still face two key challenges: (1) simplistic circuit structures limit the effectiveness of automated bug detection, and (2) structural invariance obscures tool chain bugs hidden in semantic equivalence. To address these challenges, we propose ICSG, an automated IC schematic generator designed to detect errors in the EDA tool chain. Specifically, we compile a curated library of IC pin-connection constraints and simulation models to emulate the design workflow of electronic engineers. The framework automatically selects components, performs wiring based on connection rules, and assigns electrical parameters and simulation models, thereby generating schematics that satisfy simulation semantics. To enable differential testing based on equivalence modulo inputs (EMI), we design a circuit-level mutation strategy that injects functionally inert parallel branches into static and dynamic nodes. This strategy generates equivalent variants that preserve circuit functionality while enabling the detection of behavioral discrepancies. Experimental results confirm that the inclusion of IC components and complex circuit topologies enables ICSG to trigger more tool chain bugs in differential testing than existing baseline methods. Furthermore, the introduction of the EMI strategy further enhances error exposure, particularly by revealing behavioral discrepancies across different simulation modes. Through three months of empirical testing, ICSG successfully uncovered 11 real defects in mainstream EDA tool chain, 2 of which have been officially confirmed or fixed by the tool vendors. 

***
### Experiment
Configure the required component types in conf1.txt and set the selection probabilities for each component type in conf2.txt. Then, run loop_generator.py to generate schematics and their variant schematics. Next, execute SchematicToNetlist.py to convert the schematics into netlists. Select an appropriate simulation mode and perform the simulation in the corresponding XTesting.py. Finally, review the simulation results in the aoutput folder.
***

### Reported bugs
Our reported bugs is in [Bugs](https://github.com/limeilin-lu/ICSG/blob/main/reported-bugs.md).You can visit the websites of NGspice, KiCad, and LTspice to reproduce these errors.
