
`timescale 1ns / 1ps
`default_nettype none

`include "clk_gen.v"
`include "monopix_core.v"

`include "utils/bus_to_ip.v"

`include "utils/cdc_syncfifo.v"
`include "utils/generic_fifo.v"
`include "utils/cdc_pulse_sync.v"

`include "utils/reset_gen.v"
`include "utils/CG_MOD_pos.v"
 
`include "spi/spi_core.v"
`include "spi/spi.v"
`include "spi/blk_mem_gen_8_to_1_2k.v"

`include "gpio/gpio.v"

`include "tlu/tlu_controller.v"
`include "tlu/tlu_controller_core.v"
`include "tlu/tlu_controller_fsm.v"

`include "timestamp/timestamp.v"
`include "timestamp/timestamp_core.v"

`include "timestamp640/timestamp640.v"
`include "timestamp640/timestamp640_core.v"

`include "utils/fx2_to_bus.v"

`include "pulse_gen/pulse_gen.v"
`include "pulse_gen/pulse_gen_core.v"

`include "sram_fifo/sram_fifo_core.v"
`include "sram_fifo/sram_fifo.v"

`include "utils/3_stage_synchronizer.v"
`include "rrp_arbiter/rrp_arbiter.v"
`include "utils/ddr_des.v"
`include "utils/flag_domain_crossing.v"

`include "mono_data_rx/mono_data_rx.v"
`include "mono_data_rx/mono_data_rx_core.v"
`include "utils/cdc_reset_sync.v"

`ifdef COCOTB_SIM //for simulation
    `include "utils/ODDR_sim.v"
    `include "utils/IDDR_sim.v"
    `include "utils/DCM_sim.v"
    `include "utils/clock_multiplier.v"
    `include "utils/BUFG_sim.v"

    `include "utils/RAMB16_S1_S9_sim.v"
`else
    `include "utils/IDDR_s3.v"
    `include "utils/ODDR_s3.v"
`endif 



module monopix_mio (
    
    input wire FCLK_IN, // 48MHz
    
    //full speed 
    inout wire [7:0] BUS_DATA,
    input wire [15:0] ADD,
    input wire RD_B,
    input wire WR_B,
    
    //high speed
    inout wire [7:0] FDATA,
    input wire FREAD,
    input wire FSTROBE,
    input wire FMODE,

    //LED
    output wire [4:0] LED,
    
    //SRAM
    output wire [19:0] SRAM_A,
    inout wire [15:0] SRAM_IO,
    output wire SRAM_BHE_B,
    output wire SRAM_BLE_B,
    output wire SRAM_CE1_B,
    output wire SRAM_OE_B,
    output wire SRAM_WE_B,


    input wire [2:0] LEMO_RX,
    output wire [2:0] LEMO_TX, // TX[0] == RJ45 trigger clock output, TX[1] == RJ45 busy output
    input wire RJ45_RESET,
    input wire RJ45_TRIGGER,

    input wire SR_OUT,    //DIN4
    output wire SR_IN,    //DOUT11
    output wire LDPIX,    //DOUT15
    output wire CKCONF,   //DOUT10
    output wire LDDAC,    //DOUT12
    output wire SR_EN,    //DOUT13
    output wire RESET,    //DOUT14
    output wire INJECTION,
    input wire MONITOR,   //DIN1
    
    output wire CLK_BX,   //DOUT1
    output wire READ,     //DOUT2
    output wire FREEZE,   //DOUT3
    output wire nRST,     //DOUT4
    output wire EN_TEST_PATTERN,  //DOUT5
    output wire RST_GRAY,         //DOUT6
    output wire EN_DRIVER,        //DOUT7
    output wire EN_DATA_CMOS,     //DOUT8
    output wire CLK_OUT,          //DOUT9
    input wire TOKEN,             //DIN2
    input wire DATA,              //DIN0
    input wire DATA_LVDS,         //DIN8_LVDS0
	 
	output wire DEBUG, //DOUT0
    
    // I2C
    inout wire SDA,
    inout wire SCL
);

assign SDA = 1'bz;
assign SCL = 1'bz;


// ------- RESRT/CLOCK  ------- //

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

reset_gen reset_gen(.CLK(BUS_CLK), .RST(BUS_RST));

wire CLK_LOCKED;

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

// -------  MODULE ADREESSES  ------- //

localparam FIFO_BASEADDR = 16'h8000;
localparam FIFO_HIGHADDR = 16'h9000-1;


// -------  BUS SYGNALING  ------- //
wire [15:0] BUS_ADD;
wire BUS_RD, BUS_WR;

// -------  BUS SYGNALING  ------- //
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

// -------  USER MODULES  ------- //

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
    .USB_DATA(FDATA),

    .FIFO_READ_NEXT_OUT(ARB_READY_OUT),
    .FIFO_EMPTY_IN(!ARB_WRITE_OUT),
    .FIFO_DATA(ARB_DATA_OUT),
	 
    .FIFO_NOT_EMPTY(),
    .FIFO_FULL(FIFO_FULL),
    .FIFO_NEAR_FULL(FIFO_NEAR_FULL),
    .FIFO_READ_ERROR()
);

monopix_core i_monopix_core(

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

    //LED
    .LED(LED[4:0]),
    
    .LEMO_RX(LEMO_RX),
    .LEMO_TX(LEMO_TX), // TX[0] == RJ45 trigger clock output, TX[1] == RJ45 busy output
    .RJ45_RESET(RJ45_RESET),
    .RJ45_TRIGGER(RJ45_TRIGGER),

    .SR_OUT(SR_OUT),   //DIN4
    .SR_IN(SR_IN),     //DOUT11
    .LDPIX(LDPIX),     //DOUT15
    .CKCONF(CKCONF),   //DOUT10
    .LDDAC(LDDAC),     //DOUT12
    .SR_EN(SR_EN),     //DOUT13
    .RESET(RESET),     //DOUT14
    .INJECTION(INJECTION),
    .MONITOR(MONITOR), //DIN1
    
    .CLK_BX(CLK_BX),   //DOUT1
    .READ(READ),       //DOUT2
    .FREEZE(FREEZE),   //DOUT3
    .nRST(nRST),       //DOUT4
    .EN_TEST_PATTERN(EN_TEST_PATTERN),  //DOUT5
    .RST_GRAY(RST_GRAY),                //DOUT6
    .EN_DRIVER(EN_DRIVER),              //DOUT7
    .EN_DATA_CMOS(EN_DATA_CMOS),        //DOUT8
    .CLK_OUT(CLK_OUT), //DOUT9
    .TOKEN(TOKEN),     //DIN2
    .DATA(DATA),       //DIN0
    .DATA_LVDS(DATA_LVDS),              //DIN8_LVDS0
    .DEBUG(DEBUG)     //nc
);

endmodule
