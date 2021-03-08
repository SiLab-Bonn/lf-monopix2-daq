
LF-Monopix2 DAQ
=====

This repository contains a firmware and Python3-based DAQ software required to operate the LF-Monopix2 chip.  

**A note on these instructions:** These software and its installation instrucions have been mainly developed and tested for operation in a Linux-based OS. Therefore, some instructions might look different or require additional work to get the software running in different operational systems.

## Installation
------

-	**Install ANACONDA / MINICONDA**

    In order to run this software, we recommend to have a functional ANACONDA or MINICONDA installation with a Python 3 environment. The installation steps for different OS can be found here: https://docs.anaconda.com/anaconda/install/. 

     **Optional:** It is possible to create an independent conda environment with all the software required for the operation of the chip (to avoid collisions with previously installed software or Python versions, for example). Instructions on how to create and deal with conda environments can be found in https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html. If you decide to use an environment, you can either: **1**. Run the commands for package installation in the following subsection within the **active environment**, or **2**. Follow the optional method with a yaml file **before** creating the environment.

    **Package installation:** 
    
    - **If you want to add the packages to your default installation or an environment you already created**, install the suggested packages by running the following commands:

        ``$ conda install numpy pyyaml bitarray six cython scipy numba matplotlib future numexpr dill numpydoc tqdm mock nose pyqtgraph pyserial pyzmq contextlib2 psutil testfixtures qtpy zeromq pyqtgraph pyqt jupyter notebook``
        
        ``$ pip install tables progressbar-latest pyvisa-py pyvisa``

    - **If you have not created a dedicated environment**, you can do so -under the name "lfmonopix2"- while simultaneously installing the suggested packages by running the following command on your **base** environment:

        ``$ conda env create -f PATH_TO_LF2DAQ/lfmonopix2_environment.yml``
    
-   **Install Lf-Monopix2 DAQ** (https://github.com/Silab-Bonn/lf-monopix2-daq)

    Go to the folder where you want to clone your lf-monopix2-daq, and there do:

    ``$ git clone --recurse-submodules 	https://github.com/Silab-Bonn/lf-monopix2-daq.git``

    ``$ cd lf-monopix2-daq``

    ``$ python setup.py develop``

-   **Additional (optional) installations**:

    Even though tested branches of BASIL and the SiTCP library have already been cloned together with this repository to make the current firmware compilation reliable, it might be useful to have a full independent installation of BASIL on your conda environment to control additional devices or future custom firmware development.

    -	**BASIL** (https://github.com/SiLab-Bonn/basil)

        ``$ git clone https://github.com/SiLab-Bonn/basil.git``

        ``$ cd basil``
        
        ``$ pip install -e .``
## FPGA Firmware compilation
------

-   For **compatibility of the SiTCP** module with the LF-Monopix2 firmware and BASIL, it is necessary to add the line `` `default_nettype wire`` before the first module declaration in these two files:

    `` PATH_TO_LF2DAQ/lf-monopix2-daq/SiTCP_Netlist_for_Kintex7/SiTCP_XC7K_32K_BBT_V110.V``

    `` PATH_TO_LF2DAQ/lf-monopix2-daq/SiTCP_Netlist_for_Kintex7/WRAP_SiTCP_GMII_XC7K_32K.V``

-   **To compile the firmware**: 

    Make sure that your Xilinx Vivado software is properly installed -including cable drivers- (The license-free "WebPack" version works) and it can be run by the “vivado” command on your terminal (i.e. either you have sourced the “settings***.sh” file manually, or added the commands to the bash file). 

    ``$ cd PATH_TO_LF2DAQ/lf-monopix2-daq/firmware/vivado/`` 

    ``$ vivado -mode tcl -source run.tcl`` 

    If the compilation finished without errors after running this script, the bin and bit files will be placed under: ``PATH_TO_LF2DAQ/lf-monopix2-daq/firmware/vivado/bit/`` 

## Repository structure
------

- ``/lf-monopix2-daq/`` Main folder including DAQ firmware, software and installation files.

    -  ``/SiTCP_Netlist_for_Kintex7/`` SiTCP module required for firmware compilation.

    -  ``/basil/`` A stable basil tag tested for a successful compilation of the current firmware version.

    - ``/firmware/`` Firmware-related material.

        - ``/src/`` Verilog sources and constraint files for the LF-Monopix2 firmware.

        - ``/vivado/`` run.tcl script to produce a Vivado project and run its bitstream generation from source files.

    - ``/monopix2_daq/`` Software package including the main DUT class, custom modules, configuration files and test scripts.

    - ``/tests/`` Verification tests developed (in Python 2.7) for cocotb during the chip development stage. For further instructions on how to run these tests, look at the readme.md file **inside** this folder.


