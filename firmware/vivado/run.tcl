
# -----------------------------------------------------------
# Copyright (c) SILAB , Physics Institute, University of Bonn
# -----------------------------------------------------------
#
#   This script creates Vivado projects and bitfiles for the supported hardware platforms
#
#   Start vivado in tcl mode by typing:
#       vivado -mode tcl -source run.tcl
#

# set basil_dir [exec python -c "import basil, os; print(os.path.dirname(basil.__file__))"]
# set firmware_dir [exec python -c "import os; print(os.path.dirname(os.getcwd()))"]
set vivado_dir [exec pwd]
set include_dirs [list $vivado_dir/../src $vivado_dir/../../SiTCP_Netlist_for_Kintex7 $vivado_dir/../../basil/basil/firmware/modules $vivado_dir/../../basil/basil/firmware/modules/utils]

file mkdir ../bit reports

proc run_bit { part board xdc_file size} {
    global include_dirs
    global vivado_dir

    create_project -force -part $part $board designs

    read_verilog $vivado_dir/../src/monopix2_$board.v
    read_edif $vivado_dir/../../SiTCP_Netlist_for_Kintex7/SiTCP_XC7K_32K_BBT_V110.ngc
    read_xdc $xdc_file
    generate_target -verbose -force all [get_ips]

    synth_design -top monopix2_mio3 -include_dirs $include_dirs -verilog_define "SYNTHESIS=1"
    opt_design
    place_design
    phys_opt_design
    route_design
    report_utilization
    report_timing -file "reports/report_timing.$board.log"
    write_bitstream -force -bin_file -file $vivado_dir/../bit/monopix2_$board

#   write_cfgmem -format mcs -size $size -interface SPIx4 -loadbit "up 0x0 $vivado_dir/../bit/monopix2_$board.bit" -force -file $vivado_dir/../bit/monopix2_$board
    close_project
}


#########
#
# Create projects and bitfiles
#

#       FPGA type           board name	    constraints file                flash size
run_bit xc7k160tfbg676-1    mio3          $vivado_dir/../src/monopix2_mio3.xdc    256

exit
