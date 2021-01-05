# lf-monopix2-daq
LF Monopix2 DAQ

## How to install

Install miniconda-python3
conda install matplotlib pyyaml numpy jupyter notebook
git clone --resuce-submodule https://github.com/Silab-Bonn/lf-monopix2-daq.git
cd lf-monopix2-daq
python setup.py develop

## How to compile FPGA firmware

Install vivado (Web version works)
cd lf-monopix2-daq/firmware
vivado -mode tcl -source run.tcl

## How to run

cd examples
jupyter notebook
Open a notebook file and run each cell



