/**
 * ------------------------------------------------------------
 * Copyright (c) SILAB , Physics Institute of Bonn University 
 * ------------------------------------------------------------
 */

`timescale 1ps / 1ps

// chip
`include "Monopix2.sv"
// fpga
`include "monopix2_core.v"

`ifndef VERILATOR 
`include "clk_gen.v"
`include "utils/clock_multiplier.v"
`include "utils/DCM_sim.v"
`else
`include "tests/hdl/clk_gen_sim.v"
// `include "utils/clock_multiplier.v"
`endif

`include "timestamp640/timestamp640.v"
`include "timestamp640/timestamp640_core.v"
`include "mono_data_rx/mono_data_rx.v"
`include "mono_data_rx/mono_data_rx_core.v"

// basil modules
`include "utils/bus_to_ip.v"
`include "utils/fx2_to_bus.v"
`include "utils/reset_gen.v"
`include "utils/generic_fifo.v"
`include "sram_fifo/sram_fifo_core.v"
`include "sram_fifo/sram_fifo.v"
`include "utils/ODDR_sim.v"
`include "utils/BUFG_sim.v"

// basil modules in monopix2_core
`include "rrp_arbiter/rrp_arbiter.v"
`include "gpio/gpio.v"
`include "spi/spi_core.v"
`include "spi/spi.v"
`include "spi/blk_mem_gen_8_to_1_2k.v"
`include "pulse_gen/pulse_gen_core.v"
`include "pulse_gen/pulse_gen.v"
`include "utils/CG_MOD_pos.v"
`include "utils/cdc_pulse_sync.v"
`include "utils/cdc_syncfifo.v"
`include "utils/cdc_reset_sync.v"
`include "utils/ddr_des.v"

`include "utils/IDDR_sim.v"
`include "tests/hdl/RAMB16_S1_S9_sim2.v" 

module tb (
    input wire FCLK_IN, 

    //full speed 
    inout wire [7:0] BUS_DATA,
    input wire [15:0] ADD,
    input wire RD_B,
    input wire WR_B,
    
    //high speed
    inout wire [7:0] FD,
    input wire FREAD,
    input wire FSTROBE,
    input wire FMODE,

    output wire CLK_HIT,
    input wire [`ROWS*`COLS-1:0] HIT,
    output wire RESET_HIT

);

wire [19:0] SRAM_A;
wire [15:0] SRAM_IO;
wire SRAM_BHE_B;
wire SRAM_BLE_B;
wire SRAM_CE1_B;
wire SRAM_OE_B;
wire SRAM_WE_B;

// -------  MODULE ADREESSES  ------- //

localparam FIFO_BASEADDR = 16'h8000;
localparam FIFO_HIGHADDR = 16'h9000-1;

// -------  CLOCK ------- //
wire BUS_RST;
(* KEEP = "{TRUE}" *) 
wire CLK320;  
(* KEEP = "{TRUE}" *) 
wire CLK160;
(* KEEP = "{TRUE}" *) 
wire CLK40;
(* KEEP = "{TRUE}" *) 
wire CLK16;
(* KEEP = "{TRUE}" *) 
wire BUS_CLK;
(* KEEP = "{TRUE}" *) 
wire CLK8;
wire CLK_LOCKED;

reset_gen reset_gen(.CLK(BUS_CLK), .RST(BUS_RST));

clk_gen clk_gen(
    .CLKIN(FCLK_IN),
    .BUS_CLK(BUS_CLK),
    .U1_CLK8(CLK8),
    .U2_CLK40(CLK40),
    .U2_CLK16(CLK16),
    .U2_CLK160(CLK160),
    .U2_CLK320(CLK320),
    .U2_LOCKED(CLK_LOCKED)
);

// -------  BUS SYGNALING  ------- //
wire [15:0] BUS_ADD;
wire BUS_RD, BUS_WR;

fx2_to_bus fx2_to_bus (
    .ADD(ADD),
    .RD_B(RD_B),
    .WR_B(WR_B),

    .BUS_CLK(BUS_CLK),
    .BUS_ADD(BUS_ADD),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .CS_FPGA()
);

// -------  FIFO ------- //
wire FIFO_NEAR_FULL,FIFO_FULL;
wire USB_READ;
wire ARB_READY_OUT, ARB_WRITE_OUT;
wire [31:0] ARB_DATA_OUT;

assign USB_READ = FREAD & FSTROBE;

sram_fifo #(
    .BASEADDR(FIFO_BASEADDR),
    .HIGHADDR(FIFO_HIGHADDR)
) sram_fifo (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR), 

    .SRAM_A(SRAM_A),
    .SRAM_IO(SRAM_IO),
    .SRAM_BHE_B(SRAM_BHE_B),
    .SRAM_BLE_B(SRAM_BLE_B),
    .SRAM_CE1_B(SRAM_CE1_B),
    .SRAM_OE_B(SRAM_OE_B),
    .SRAM_WE_B(SRAM_WE_B),

    .USB_READ(USB_READ),
    .USB_DATA(FD),

    .FIFO_READ_NEXT_OUT(ARB_READY_OUT),
    .FIFO_EMPTY_IN(!ARB_WRITE_OUT),
    .FIFO_DATA(ARB_DATA_OUT),
	 
    .FIFO_NOT_EMPTY(),
    .FIFO_FULL(FIFO_FULL),
    .FIFO_NEAR_FULL(FIFO_NEAR_FULL),
    .FIFO_READ_ERROR()
);
 
//SRAM Model
reg [15:0] sram [1048576-1:0];
assign SRAM_IO = !SRAM_OE_B ? sram[SRAM_A] : 16'hzzzz;
always@(negedge SRAM_WE_B)
    sram[SRAM_A] <= SRAM_IO;

// -------  Extra In/Out ------- // 
wire [2:0] LEMO_RX;  
wire [2:0] LEMO_TX;
assign LEMO_RX[2]=LEMO_TX[2]; //loop back of injection

// -------  FPGA CORE ------- //
wire ClkBX_PAD; 
wire ClkOut_PAD;
wire ClkSR_PAD;
wire ResetBcid_PAD;
wire nRst_PAD;

wire SR_EN_PAD;
wire Si_PAD;
wire Def_Conf_PAD;
wire Ld_DAC_PAD;
wire Ld_Cnfg_PAD;
wire So_PAD;

wire Freeze_PAD;
wire Read_PAD;
wire TokOut_PAD;
wire DataOut_PAD;
wire LVDS_OutN_PAD;
wire LVDS_OutP_PAD;
wire Injection_PAD;
wire Idac_Mon_PAD;
wire HitOr_PAD;

wire Freeze;

monopix2_core fpga (
//local bus
    .BUS_CLK(BUS_CLK),
    .BUS_DATA(BUS_DATA),
    .BUS_ADD(BUS_ADD),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .BUS_RST(BUS_RST),

//clocks
    .CLK8(CLK8),
    .CLK40(CLK40),
    .CLK16(CLK16),
    .CLK160(CLK160),
    .CLK320(CLK320),
//fifo
    .ARB_READY_OUT(ARB_READY_OUT),
    .ARB_WRITE_OUT(ARB_WRITE_OUT),
    .ARB_DATA_OUT(ARB_DATA_OUT),
    .FIFO_FULL(FIFO_FULL),
    .FIFO_NEAR_FULL(FIFO_NEAR_FULL),
//in/out
    .LEMO_RX(LEMO_RX),
    .LEMO_TX(LEMO_RX),

//      Clock & reset
   .ClkBX(ClkBX_PAD),              //input logic
   .ClkOut(ClkOut_PAD),            //input logic
   .ClkSR(ClkSR_PAD),              //input logic 
//
   .ResetBcid(ResetBcid_PAD),      //input logic 
   .nRst(nRst_PAD),                //input logic

//      Configuration
   .SR_EN(SR_EN_PAD),              //input logic 
   .Si(Si_PAD),                    //input logic 
   .Def_Conf(Def_Conf_PAD),        //input logic 
   .Ld_DAC(Ld_DAC_PAD),            //input logic 
   .Ld_Cnfg(Ld_Cnfg_PAD),          //input logic 
   .So(So_PAD),                    //output logic 

//      RO
   .Freeze(Freeze_PAD),            //input logic 
   .Read(Read_PAD),                //input logic

   .TokOut(TokOut_PAD),            //output logic 
   .DataOut(DataOut_PAD),          //output logic 
   .LVDS_Out(LVDS_OutP_PAD),      //output logic 

// Injection & Monitor
   .Injection(Injection_PAD),     //input logic 
   .HitOr(HitOr_PAD)              //output logic 
);

//assing Freeze_PAD = Freeze | fpga.GPIO_OUT[15];

// -------  CHIP ------- //
wire Iref_PAD,AmpOutCurr_PAD,AmpOutTEST_PAD;
wire VcascN_PAD,Nbias_G_PAD,TH_PAD,BL_PAD,VHi_PAD,VLo_PAD,Vpc_PAD;
Monopix2 chip(
//      Clock & reset
   .ClkBX_PAD(ClkBX_PAD),              //input logic
   .ClkOut_PAD(ClkOut_PAD),            //input logic
   .ClkSR_PAD(ClkSR_PAD),              //input logic 
//
   .ResetBcid_PAD(ResetBcid_PAD),      //input logic 
   .nRst_PAD(nRst_PAD),                //input logic

//      Configuration
   .SR_EN_PAD(SR_EN_PAD),              //input logic 
   .Si_PAD(Si_PAD),                    //input logic 
   .Def_Conf_PAD(Def_Conf_PAD),        //input logic 
   .Ld_DAC_PAD(Ld_DAC_PAD),            //input logic 
   .Ld_Cnfg_PAD(Ld_Cnfg_PAD),          //input logic 
   .So_PAD(So_PAD),                    //output logic 

//      RO
   .Freeze_PAD(Freeze_PAD),            //input logic 
   .Read_PAD(Read_PAD),                //input logic

   .TokOut_PAD(TokOut_PAD),            //output logic 
   .DataOut_PAD(DataOut_PAD),          //output logic 
   .LVDS_OutN_PAD(LVDS_OutN_PAD),      //output logic 
   .LVDS_OutP_PAD(LVDS_OutP_PAD),      //output logic

// Analog
   .Iref_PAD(),                //inout TODO: NC for analog signals for now
   .VcascN_PAD(),            //inout 
   .Nbias_G_PAD(),          //inout 
   .TH_PAD(),      //inout 
   .BL_PAD(),      //inout 
   .VHi_PAD(),      //inout 
   .VLo_PAD(),      //inout 
   .Vpc_PAD(),      //inout 

// Injection & Monitor
   .Injection_PAD(Injection_PAD),       //input logic 
   .Idac_Mon_PAD(Idac_Mon_PAD),         //inout 
   .AmpOutCurr_PAD(),   //inout 
   .AmpOutTEST_PAD(),   //inout 
   .HitOr_PAD(HitOr_PAD)              //output logic 

);

//-- Analog_hit --/
assign chip.matrix.analog_hit=HIT;
wire CLK_HIT_GATE;
assign CLK_HIT=CLK40 & CLK_HIT_GATE;

wire [7:0] IP_DATA_IN;
wire [15:0] IP_ADD;
wire IP_RD,IP_WR;
reg [7:0] IP_DATA_OUT;
bus_to_ip #(
    .BASEADDR(16'h2000), 
    .HIGHADDR(16'h2FFF), 
    .ABUSWIDTH(16) 
) i_bus_to_ip_top (
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),

    .IP_RD(IP_RD),
    .IP_WR(IP_WR),
    .IP_ADD(IP_ADD),
    .IP_DATA_IN(IP_DATA_IN),
    .IP_DATA_OUT(IP_DATA_OUT)
);
always @(posedge BUS_CLK) begin
    if(IP_RD) begin
        if(IP_ADD == 0)
          IP_DATA_OUT <= 8'b00000001;
        else if(IP_ADD ==1 )
          IP_DATA_OUT <= {1'b0, chip.dac.Mon_BLRes, chip.dac.DAC_BLRes};
        else if(IP_ADD ==2)
          IP_DATA_OUT <= {1'b0, chip.dac.Mon_VAmp, chip.dac.DAC_VAmp};
        else if(IP_ADD ==3)
          IP_DATA_OUT <= {1'b0, chip.dac.Mon_VPFB, chip.dac.DAC_VPFB};
        else if(IP_ADD ==4)
          IP_DATA_OUT <= {1'b0, chip.dac.Mon_VFoll, chip.dac.DAC_VFoll};
        else if(IP_ADD ==5)
          IP_DATA_OUT <= {1'b0, chip.dac.Mon_VLoad, chip.dac.DAC_VLoad};
        else if(IP_ADD ==6)
          IP_DATA_OUT <= {1'b0, chip.dac.Mon_LSBdacL, chip.dac.DAC_LSB_tdac};
        else if(IP_ADD ==7)
          IP_DATA_OUT <= {1'b0, chip.dac.Mon_Vsf, chip.dac.DAC_Vsf};
        else if(IP_ADD ==8)
          IP_DATA_OUT <= {6'b000000,RESET_HIT,CLK_HIT_GATE};
        else if(IP_ADD ==9)
          IP_DATA_OUT <= {7'b000000,TokOut_PAD};
        else if(IP_ADD ==10)
          IP_DATA_OUT <= {6'b000000,chip.dcb.EnDataCMOS, DataOut_PAD};
        else if(IP_ADD ==11)
          IP_DATA_OUT <= {5'b00000,chip.dcb.EnDataLVDS, LVDS_OutN_PAD,LVDS_OutP_PAD};

        else if(IP_ADD ==12)
          IP_DATA_OUT <= fpga.TIMESTAMP[7:0];
        else if(IP_ADD ==13)
          IP_DATA_OUT <= fpga.TIMESTAMP[15:8];
        else if(IP_ADD ==14)
          IP_DATA_OUT <= fpga.TIMESTAMP[23:16];
        else if(IP_ADD ==15)
          IP_DATA_OUT <= fpga.TIMESTAMP[31:24];
        else if(IP_ADD ==16)
          IP_DATA_OUT <= fpga.TIMESTAMP[39:32];
        else if(IP_ADD ==17)
          IP_DATA_OUT <= fpga.TIMESTAMP[47:40];
        else if(IP_ADD ==18)
          IP_DATA_OUT <= fpga.TIMESTAMP[55:48];
        else if(IP_ADD ==19)
          IP_DATA_OUT <= fpga.TIMESTAMP[63:56];

        else if(IP_ADD ==27)
          IP_DATA_OUT <= chip.dcb.EnMonitorCol[7:0];
        else if(IP_ADD ==28)
          IP_DATA_OUT <= chip.dcb.EnMonitorCol[15:8];
        else if(IP_ADD ==29)
          IP_DATA_OUT <= chip.dcb.EnMonitorCol[23:16];
        else if(IP_ADD ==30)
          IP_DATA_OUT <= chip.dcb.EnMonitorCol[31:24];
        else if(IP_ADD ==31)
          IP_DATA_OUT <= chip.dcb.EnMonitorCol[39:32];
        else if(IP_ADD ==32)
          IP_DATA_OUT <= chip.dcb.EnMonitorCol[47:40];
        else if(IP_ADD ==33)
          IP_DATA_OUT <= chip.dcb.EnMonitorCol[55:48];

        else if(IP_ADD ==34)
          IP_DATA_OUT <= chip.dcb.nRstCol[7:0];
        else if(IP_ADD ==35)
          IP_DATA_OUT <= chip.dcb.nRstCol[15:8];
        else if(IP_ADD ==36)
          IP_DATA_OUT <= chip.dcb.nRstCol[23:16];
        else if(IP_ADD ==37)
          IP_DATA_OUT <= chip.dcb.nRstCol[31:24];
        else if(IP_ADD ==38)
          IP_DATA_OUT <= chip.dcb.nRstCol[39:32];
        else if(IP_ADD ==39)
          IP_DATA_OUT <= chip.dcb.nRstCol[47:40];
        else if(IP_ADD ==40)
          IP_DATA_OUT <= chip.dcb.nRstCol[55:48];

        else if(IP_ADD ==41)
          IP_DATA_OUT <= chip.dcb.FreezeCol[7:0];
        else if(IP_ADD ==42)
          IP_DATA_OUT <= chip.dcb.FreezeCol[15:8];
        else if(IP_ADD ==43)
          IP_DATA_OUT <= chip.dcb.FreezeCol[23:16];
        else if(IP_ADD ==44)
          IP_DATA_OUT <= chip.dcb.FreezeCol[31:24];
        else if(IP_ADD ==45)
          IP_DATA_OUT <= chip.dcb.FreezeCol[39:32];
        else if(IP_ADD ==46)
          IP_DATA_OUT <= chip.dcb.FreezeCol[47:40];
        else if(IP_ADD ==47)
          IP_DATA_OUT <= chip.dcb.FreezeCol[55:48];
        else
            IP_DATA_OUT <= 8'b0;
    end
end
reg [7:0] status_regs;
always @(posedge BUS_CLK) begin
    if (BUS_RST) 
        status_regs <= 0;
    if(IP_WR && IP_ADD ==8)
        status_regs <= IP_DATA_IN;
end
assign CLK_HIT_GATE = status_regs[0];
assign RESET_HIT = status_regs[1];

//initial begin
//    $dumpfile("/tmp/monopix2.vcd.gz");
//    $dumpvars(1);
//end

endmodule