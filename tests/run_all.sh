#!/bin/bash
make clean

if [ "$1" = "rtl" ] || [ $# -eq 0 ]
then
echo "test_FPGA.py" > /tmp/FPGA.log
echo "test_ReadCol.py" > /tmp/ReadCol.log
echo "test_Rst.py" > /tmp/Rst.log
echo "test_TrimLd.py" > /tmp/TrimLd.log
echo "test_BcidCol.py" > /tmp/BcidCol.log
echo "test_DAC.py" > /tmp/DAC.log
echo "test_DAC.py" > /tmp/DataOut.log
echo "test_DO.py" > /tmp/DO.log
echo "test_EnDataCMOS.py" > /tmp/EnDataCMOS.log
echo "test_EnInjLd.py" > /tmp/EnInjLd.log
echo "test_EnMonitorCol.py" > /tmp/EnMonitorCol.log
echo "test_EnMonitorLd.py" > /tmp/EnMonitorLd.log
echo "test_EnPreLd.py" > /tmp/EnPreLd.log
echo "test_Freeze.py" > /tmp/Freeze.log
echo "test_InjectionCol.py" > /tmp/InjectionCol.log
echo "test_TokenOut.py" > /tmp/TokenOut.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_FPGA.py  2>&1 | tee -a  /tmp/FPGA.log 
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_ReadCol.py  2>&1 | tee -a  /tmp/ReadCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_Rst.py  2>&1 | tee -a /tmp/Rst.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_TrimLd.py  2>&1 | tee -a /tmp/TrimLd.log 
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_BcidCol.py  2>&1 | tee -a /tmp/BcidCol.log 
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DAC.py  2>&1 | tee -a /tmp/DAC.log 
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DataOut.py  2>&1 | tee -a /tmp/DataOut.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DO.py  2>&1 | tee -a /tmp/DO.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnDataCMOS.py 2>&1 | tee -a /tmp/EnDataCMOS.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnInjLd.py 2>&1 | tee -a /tmp/EnInjLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnMonitorCol.py  2>&1 | tee -a /tmp/EnMonitorCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnMonitorLd.py  2>&1 | tee -a /tmp/EnMonitorLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnPreLd.py  2>&1 | tee -a /tmp/EnPreLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_Freeze.py  2>&1 | tee -a /tmp/Freeze.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_InjectionCol.py  2>&1 | tee -a /tmp/InjectionCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_TokenOut.py  2>&1 | tee -a /tmp/TokenOut.log
elif [ "$1" = "gate" ] || [ $# -eq 0 ]
then
echo "test_FPGA.py" > /tmp/FPGA.log
echo "test_ReadCol.py" > /tmp/ReadCol.log
echo "test_Rst.py" > /tmp/Rst.log
echo "test_TrimLd.py" > /tmp/TrimLd.log
echo "test_BcidCol.py" > /tmp/BcidCol.log
echo "test_DAC.py" > /tmp/DAC.log
echo "test_DAC.py" > /tmp/DataOut.log
echo "test_DO.py" > /tmp/DO.log
echo "test_EnDataCMOS.py" > /tmp/EnDataCMOS.log
echo "test_EnInjLd.py" > /tmp/EnInjLd.log
echo "test_EnMonitorCol.py" > /tmp/EnMonitorCol.log
echo "test_EnMonitorLd.py" > /tmp/EnMonitorLd.log
echo "test_EnPreLd.py" > /tmp/EnPreLd.log
echo "test_Freeze.py" > /tmp/Freeze.log
echo "test_InjectionCol.py" > /tmp/InjectionCol.log
echo "test_TokenOut.py" > /tmp/TokenOut.log
echo "_GATE_LEVEL_NETLIST_" >> /tmp/Rst.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_Rst.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/Rst.log
echo "_GATE_LEVEL_NETLIST_" >> /tmp/TrimLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_TrimLd.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/TrimLd.log 
echo "_GATE_LEVEL_NETLIST_" >> /tmp/BcidCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_BcidCol.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/BcidCol.log 
echo "_GATE_LEVEL_NETLIST_" >> /tmp/DAC.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DAC.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/DAC.log
echo "_GATE_LEVEL_NETLIST_" >> /tmp/DataOut.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DataOut.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a /tmp/DataOut.log
echo "_GATE_LEVEL_NETLIST_" >> /tmp/DO.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DO.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/DO.log
echo "test_gate_EnDataCMOS.py" >> /tmp/EnDataCMOS.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnDataCMOS.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a /tmp/EnDataCMOS.log
echo "test_gate_EnMonitorCol.py" >> /tmp/EnMonitorCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnMonitorCol.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/EnMonitorCol.log
echo "Gate_level_netlist" >> /tmp/EnMonitorLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnMonitorLd.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/EnMonitorLd.log
echo "Gate_level_netlist" >> /tmp/EnPreLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnPreLd.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/EnPreLd.log
echo "Gate_level_netlist" >> /tmp/TokenOut.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_TokeOut.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/InjectionCol.log
echo "_GATE_LEVEL_NETLIST_" >> /tmp/ReadCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_ReadCol.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/ReadCol.log
echo "Gate_level_netlist" >> /tmp/Freeze.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_Freeze.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/Freeze.log
echo "Gate_level_netlist" >> /tmp/InjectionCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_InjectionCol.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/InjectionCol.log
echo "test_gate_EnInjLd.py" >> /tmp/EnInjLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnInjLd.py _GATE_LEVEL_NETLIST_ 2>&1 | tee -a  /tmp/EnInjLd.log
elif  [ "$1" = "max" ] 
then
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/Rst.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_Rst.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/Rst.log
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/TrimLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_TrimLd.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/TrimLd.log 
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/BcidCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_BcidCol.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/BcidCol.log 
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/DAC.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DAC.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/DAC.log
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/DataOut.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DataOut.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a /tmp/DataOut.log
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/DO.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DO.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/DO.log
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/EnDataCMOS.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnDataCMOS.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a /tmp/EnDataCMOS.log
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/EnInjLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnInjLd.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/EnInjLd.log
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/EnMonitorCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnMonitorCol.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/EnMonitorCol.log
echo "Gate_level_netlist=max" >> /tmp/EnMonitorLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnMonitorLd.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/EnMonitorLd.log
echo "Gate_level_netlist=max" >> /tmp/EnPreLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnPreLd.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/EnPreLd.log
echo "Gate_level_netlist=max" >> /tmp/Freeze.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_Freeze.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/Freeze.log
echo "Gate_level_netlist=max" >> /tmp/InjectionCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_InjectionCol.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/InjectionCol.log
echo "Gate_level_netlist=max" >> /tmp/TokenOut.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_TokenOut.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/InjectionCol.log
echo "_GATE_LEVEL_NETLIST_=max" >> /tmp/ReadCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_ReadCol.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/ReadCol.log
elif  [ "$1" = "min" ] 
then
#echo "_GATE_LEVEL_NETLIST_=min" >> /tmp/Rst.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_Rst.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/Rst.log
#echo "_GATE_LEVEL_NETLIST_=min" >> /tmp/TrimLd.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_TrimLd.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/TrimLd.log 
#echo "_GATE_LEVEL_NETLIST_=min" >> /tmp/BcidCol.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_BcidCol.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/BcidCol.log 
#echo "_GATE_LEVEL_NETLIST_=min" >> /tmp/DAC.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DAC.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/DAC.log
#echo "_GATE_LEVEL_NETLIST_=min" >> /tmp/DataOut.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DataOut.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a /tmp/DataOut.log
#echo "_GATE_LEVEL_NETLIST_=min" >> /tmp/DO.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_DO.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/DO.log
#echo "_GATE_LEVEL_NETLIST_=min" >> /tmp/EnDataCMOS.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnDataCMOS.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a /tmp/EnDataCMOS.log
#echo "_GATE_LEVEL_NETLIST_=min" >> /tmp/EnInjLd.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnInjLd.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/EnInjLd.log
#echo "_GATE_LEVEL_NETLIST_=min" >> /tmp/EnMonitorCol.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnMonitorCol.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/EnMonitorCol.log
echo "Gate_level_netlist=min" >> /tmp/InjectionCol.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_InjectionCol.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/InjectionCol.log
echo "Gate_level_netlist=min" > /tmp/TokenOut.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_TokenOut.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/TokenOut.log
#echo "_GATE_LEVEL_NETLIST_=min" > /tmp/ReadCol.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_ReadCol.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/ReadCol.log
#echo "Gate_level_netlist=min" >> /tmp/EnMonitorLd.log
#/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnMonitorLd.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/EnMonitorLd.log
echo "Gate_level_netlist=min" >> /tmp/EnPreLd.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_EnPreLd.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/EnPreLd.log
echo "Gate_level_netlist=min" >> /tmp/Freeze.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_Freeze.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/Freeze.log

else
echo "test_${1}.py" > /tmp/${1}.log
echo "========== RTL ==========" >> /tmp/${1}.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_${1}.py 2>&1 | tee -a  /tmp/${1}.log
echo "========== Gate Level Netlist with Typ ==========" >> /tmp/${1}.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_${1}.py _GATE_LEVEL_NETLIST_=typ 2>&1 | tee -a  /tmp/${1}.log
echo "========== Gate Level Netlist with Min ==========" >> /tmp/${1}.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_${1}.py _GATE_LEVEL_NETLIST_=min 2>&1 | tee -a  /tmp/${1}.log
echo "========== Gate Level Netlist with Max ==========" >> /tmp/${1}.log
/faust/user/thirono/miniconda2/bin/python /faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/daq/tests/test_${1}.py _GATE_LEVEL_NETLIST_=max 2>&1 | tee -a  /tmp/${1}.log
fi