/**
 * ------------------------------------------------------------
 * Copyright (c) SILAB , Physics Institute of Bonn University
 * ------------------------------------------------------------
 */

`timescale 1ps / 1ps

module monopix2_core (
    //local bus
    input wire BUS_CLK,
    inout wire [7:0] BUS_DATA,
    input wire [15:0] BUS_ADD,
    input wire BUS_RD,
    input wire BUS_WR,
    input wire BUS_RST,
    
//clocks
    input wire CLK8,
    input wire CLK40,
    input wire CLK16,
    input wire CLK160,
    input wire CLK320,
    
//fifo
    input wire ARB_READY_OUT,
    output wire ARB_WRITE_OUT,
    output wire [31:0] ARB_DATA_OUT,
    input wire FIFO_FULL,
    input wire FIFO_NEAR_FULL,

//LED, LEMO, RJ45
    output wire [4:0] LED,
    input wire [1:0] LEMO_RX,
    input wire InjLoopIn,
    output wire TLU_CLK,    //TX0 and RJ45 
    output wire TLU_BUSY,   //TX1 and RJ45
    output wire InjLoopOut, //TX2 or Flatcable
    input wire TLU_RESET,   //RJ45
    input wire TLU_TRIGGER, //RJ45

// Chip Reset & Clock
   output wire ResetBcid,      //input logic 
   output wire nRst,           //input logic
   output wire ClkOut,            //input logic
   output wire ClkBX,              //input logic
   output wire ClkSR,              //input logic 

// Chip Configuration
   output wire En_Cnfg_Pix,         //input logic 
   output wire Def_Cnfg,        //input logic 
   output wire Ld,          //input logic 
   output wire Si,              //input logic 
   input wire So,               //output logic 

// Chip RO
   output wire Freeze,       //input logic 
   output wire Read,         //input logic
   input wire TokOut,        //output logic 
   input wire DataOut,       //output logic 
   input wire LVDS_Out,      //output logic 

// Chip Injection & Monitor
   output wire Injection,     //input logic
   input wire HitOr,          //output logic

   output wire DEBUG_MUTINJRISE,
   output wire DEBUG
);

// -------  MODULE ADREESSES  ------- //
// DO NOT assign 32'h2000-32'h3000 it is for GPAC in mio3!!

localparam GPIO_BASEADDR = 16'h0010;
localparam GPIO_HIGHADDR = 16'h0100-1;

localparam PULSE_MUTEINJRISE_BASEADDR = 16'h0200;
localparam PULSE_MUTEINJRISE_HIGHADDR = 16'h0300-1;

localparam PULSE_INJ_BASEADDR = 16'h0300;
localparam PULSE_INJ_HIGHADDR = 16'h0400-1;

localparam PULSE_GATE_BASEADDR = 16'h0400;
localparam PULSE_GATE_HIGHADDR = 16'h0500-1;

localparam DATA_RX_BASEADDR = 16'h0500;
localparam DATA_RX_HIGHADDR = 16'h0600-1;

localparam TLU_BASEADDR = 16'h0600;
localparam TLU_HIGHADDR = 16'h0700-1;

localparam TS_BASEADDR = 16'h0700;
localparam TS_HIGHADDR = 16'h0800-1;

localparam TS_TLU_BASEADDR = 16'h0800;
localparam TS_TLU_HIGHADDR = 16'h0900-1;

localparam TS_INJ_BASEADDR = 16'h0900;
localparam TS_INJ_HIGHADDR = 16'h0a00-1;

localparam TS_MON_BASEADDR = 16'h0a00;
localparam TS_MON_HIGHADDR = 16'h0b00-1;

localparam SPI_BASEADDR = 16'h5000;
localparam SPI_HIGHADDR = 16'h6000-1; // 36*2+16=0x58

localparam SPI_PIX_BASEADDR = 16'h0b00;
localparam SPI_PIX_HIGHADDR = 16'h1000-1; // 85*2+16=0x272

localparam FIFO_BASEADDR = 16'h8000;
localparam FIFO_HIGHADDR = 16'h9000-2;

// -------  FPGA VERSION ------- //
localparam VERSION = 8'h01;

reg RD_VERSION;
always@(posedge BUS_CLK)
    if(BUS_ADD == 16'h0000 && BUS_RD)
        RD_VERSION <= 1;
    else
        RD_VERSION <= 0;
assign BUS_DATA = (RD_VERSION) ? VERSION : 8'bz;


// ------- DATA interface ------- //
wire RX_FIFO_READ, RX_FIFO_EMPTY;
wire [31:0] RX_FIFO_DATA;

wire TS_INJ_FIFO_READ,TS_INJ_FIFO_EMPTY;
wire [31:0] TS_INJ_FIFO_DATA;

wire TLU_FIFO_READ,TLU_FIFO_EMPTY;
wire [31:0] TLU_FIFO_DATA;
// assign TLU_FIFO_EMPTY = 1;
//wire TLU_FIFO_PREEMPT_REQ;	# SET IF WANT TO FORCE TLU PRIORITY

wire TS_FIFO_READ,TS_FIFO_EMPTY;
wire [31:0] TS_FIFO_DATA;
// assign TS_FIFO_EMPTY = 1;

wire TS_TLU_FIFO_READ,TS_TLU_FIFO_EMPTY;
wire [31:0] TS_TLU_FIFO_DATA;
// assign TS_TLU_FIFO_EMPTY = 1;

wire TS_MON_FIFO_READ,TS_MON_FIFO_EMPTY;
wire [31:0] TS_MON_FIFO_DATA;
wire TS_MON_FIFO_READ_TRAILING,TS_MON_FIFO_EMPTY_TRAILING;
wire [31:0] TS_MON_FIFO_DATA_TRAILING;
// assign TS_MON_FIFO_EMPTY = 1;
// assign TS_MON_FIFO_EMPTY_TRAILING = 1;

rrp_arbiter 
#( 
    .WIDTH(7)
) rrp_arbiter
(
    .RST(BUS_RST),
    .CLK(BUS_CLK),
    .WRITE_REQ({ ~TS_INJ_FIFO_EMPTY,
                 ~TS_MON_FIFO_EMPTY,
                 ~TS_MON_FIFO_EMPTY_TRAILING, 
                 ~TS_FIFO_EMPTY,
                 ~RX_FIFO_EMPTY,
                 ~TS_TLU_FIFO_EMPTY,
                 ~TLU_FIFO_EMPTY}),
    .HOLD_REQ({7'b0}),
    //.HOLD_REQ({1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, TLU_FIFO_PREEMPT_REQ}),
    .DATA_IN({TS_INJ_FIFO_DATA,
              TS_MON_FIFO_DATA,
              TS_MON_FIFO_DATA_TRAILING,
              TS_FIFO_DATA,
              RX_FIFO_DATA,
              TS_TLU_FIFO_DATA,
              TLU_FIFO_DATA}),
    .READ_GRANT({TS_INJ_FIFO_READ,
                 TS_MON_FIFO_READ,
                 TS_MON_FIFO_READ_TRAILING, 
                 TS_FIFO_READ,
                 RX_FIFO_READ,
                 TS_TLU_FIFO_READ,
                 TLU_FIFO_READ}),
    .READY_OUT(ARB_READY_OUT),
    .WRITE_OUT(ARB_WRITE_OUT),
    .DATA_OUT(ARB_DATA_OUT)
    );

// -------  USER MODULES  ------- //
wire [15:0] GPIO_OUT;
gpio 
#( 
    .BASEADDR(GPIO_BASEADDR), 
    .HIGHADDR(GPIO_HIGHADDR),
    .IO_WIDTH(16),
    .IO_DIRECTION(16'hffff)
) gpio
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .IO(GPIO_OUT)
    ); 

wire EN_Cnfg_CONF;
wire EN_ClkBX_CONF, EN_ClkOut_CONF,SW_LVDS_Out_CONF;
wire Rst_CONF,ResetBcid_CONF,EN_ResetBcid_WITH_TIMESTAMP;
wire SW_SR_EN_CONF, SW_SLOW_RX_CONF;

assign Rst_CONF = GPIO_OUT[0];
//assign EN_Ld_DAC_CONF = GPIO_OUT[1];
assign En_Cnfg_Pix = GPIO_OUT[2];
assign Def_Cnfg = GPIO_OUT[3];
assign EN_ClkBX_CONF = GPIO_OUT[4];
assign EN_ClkOut_CONF = GPIO_OUT[5];
assign ResetBcid_CONF = GPIO_OUT[6];
assign SW_SR_EN_CONF= GPIO_OUT[7];
assign SW_LVDS_Out_CONF = GPIO_OUT[8];
assign SW_SLOW_RX_CONF = GPIO_OUT[9];
assign EN_ResetBcid_WITH_TIMESTAMP = GPIO_OUT[10];

////////////////////////////////////////////
//TLU
wire TRIGGER_ACKNOWLEDGE_FLAG,TRIGGER_ACCEPTED_FLAG;
assign TRIGGER_ACKNOWLEDGE_FLAG = TRIGGER_ACCEPTED_FLAG;
wire [63:0] TIMESTAMP;
tlu_slave #(
    .BASEADDR(TLU_BASEADDR),
    .HIGHADDR(TLU_HIGHADDR),
    .DIVISOR(8)
) i_tlu_slave (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    
    .TRIGGER_CLK(CLK40),
    
    .FIFO_READ(TLU_FIFO_READ),
    .FIFO_EMPTY(TLU_FIFO_EMPTY),
    .FIFO_DATA(TLU_FIFO_DATA),
    .FIFO_PREEMPT_REQ(),
    //.FIFO_PREEMPT_REQ(TLU_FIFO_PREEMPT_REQ),	# SET IF WANT TO FORCE TLU PRIORITY
     
    .TRIGGER_ENABLED(),
    .TRIGGER_SELECTED(),
    .TLU_ENABLED(),
    //.TRIGGER({8'b0}),
    .TRIGGER({7'b0, TLU_TRIGGER}),
    .TRIGGER_VETO({7'b0,FIFO_FULL}),
    .TIMESTAMP_RESET(),
    //.EXT_TRIGGER_ENABLE(),     //.EXT_TRIGGER_ENABLE(TLU_EXT_TRIGGER_ENABLE)
    .EXT_TRIGGER_ENABLE(1'b0),
    .TRIGGER_ACKNOWLEDGE(TRIGGER_ACKNOWLEDGE_FLAG),
    .TRIGGER_ACCEPTED_FLAG(TRIGGER_ACCEPTED_FLAG),

    .TLU_TRIGGER(TLU_TRIGGER),
    .TLU_RESET(TLU_RESET),
    .TLU_BUSY(TLU_BUSY),
    .TLU_CLOCK(TLU_CLK),
    .EXT_TIMESTAMP(),
    .TIMESTAMP(TIMESTAMP)
);


timestamp640 #(
    .BASEADDR(TS_TLU_BASEADDR),
    .HIGHADDR(TS_TLU_HIGHADDR),
    .IDENTIFIER(4'b0111)
) i_timestamp160_tlu (
    .BUS_CLK(BUS_CLK),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RST(BUS_RST),
    .BUS_WR(BUS_WR),
    .BUS_RD(BUS_RD),
    
    .CLK320(CLK320),
    .CLK160(CLK160),
    .CLK40(CLK40),
    .DI(TLU_TRIGGER),     // TLU_TRIGGER | LEMO_RX[0] (Connected to a clean LEMO Trigger output)
    .EXT_TIMESTAMP(TIMESTAMP),
    .EXT_ENABLE(~TLU_BUSY),

    .FIFO_READ(TS_TLU_FIFO_READ),
    .FIFO_EMPTY(TS_TLU_FIFO_EMPTY),
    .FIFO_DATA(TS_TLU_FIFO_DATA)
);

////////////////////////////////////////////
// SR config
wire CONF_CLK;
wire SCLK, SDI, SDO, SEN, SLD;
wire SCLK_Cnfg, SDI_Cnfg, SEN_Cnfg, SLD_Cnfg;

// CLK_SR has to be smaller than 8 MHz for proper pixel configuration ---> CLK8/8 = 1MHz
clock_divider 
#(
    .DIVISOR(8)
) i_clock_divisor_conf (
    .CLK(CLK8),
    .RESET(1'b0),
    .CLOCK(CONF_CLK)
);

spi 
#( 
    .BASEADDR(SPI_BASEADDR), 
    .HIGHADDR(SPI_HIGHADDR),
    .MEM_BYTES(37) 
    )  spi_dac
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .SPI_CLK(CONF_CLK),

    .SCLK(SCLK),
    .SDI(SDI),
    .SDO(SDO),
    .EXT_START(1'b0),
    .SEN(SEN),
    .SLD(SLD)
);
reg [3:0] delay_cnt;
//always@(posedge CONF_CLK)
//    if(BUS_RST)
//        delay_cnt <= 0;
//    else if(SEN)
//        delay_cnt <= 4'b1111;
//    else if(delay_cnt != 0)
//        delay_cnt <= delay_cnt - 1;
assign ClkSR = En_Cnfg_Pix? SCLK_Cnfg:SCLK;
assign Si = En_Cnfg_Pix? SDI_Cnfg:SDI;
assign SDO = So;
assign Ld = En_Cnfg_Pix? SLD_Cnfg:SLD;

spi 
#( 
    .BASEADDR(SPI_PIX_BASEADDR), 
    .HIGHADDR(SPI_PIX_HIGHADDR),
    .MEM_BYTES(85) 
)  spi_cnfg
(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .SPI_CLK(CONF_CLK),

    .SCLK(SCLK_Cnfg),
    .SDI(SDI_Cnfg),
    .SDO(SDO),
    .EXT_START(1'b0),
    .SEN(SEN_Cnfg),
    .SLD(SLD_Cnfg)
);

//GATE
wire GATE;
pulse_gen
#( 
    .BASEADDR(PULSE_GATE_BASEADDR), 
    .HIGHADDR(PULSE_GATE_HIGHADDR)
)     pulse_gen_gate(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .PULSE_CLK(~CLK40),
    .EXT_START(SLD),
    .PULSE(GATE)
);

////////////////////////////////////////////
/// Data RX
wire RX_DATA, RX_CLK;
mono_data_rx #(
   .BASEADDR(DATA_RX_BASEADDR),
   .HIGHADDR(DATA_RX_HIGHADDR),
   .IDENTYFIER(4'b0000)
) mono_data_rx (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    
    //.CLK_BX(~CLK40),
    .RX_TOKEN(TokOut), 
    .RX_DATA(RX_DATA), 
    .RX_CLK(~RX_CLK),
    .RX_READ(Read), 
    .RX_FREEZE(Freeze), 
    .TIMESTAMP(TIMESTAMP),
    
    .FIFO_READ(RX_FIFO_READ),
    .FIFO_EMPTY(RX_FIFO_EMPTY),
    .FIFO_DATA(RX_FIFO_DATA),
    
    .MUTE_INJHIGH(DEBUG),      // MUTEATTEMPT
    .LOST_ERROR()
);

//This was an initial option in software, but we got timing errors at the implementation. 40MHz by now.
//assign RX_CLK = SW_SLOW_RX_CONF? CLK40:CLK160;
assign RX_CLK = CLK40;

assign RX_DATA= SW_LVDS_Out_CONF? LVDS_Out : DataOut;
ODDR clk_bx_gate(.D1(EN_ClkBX_CONF), .D2(1'b0), .C(CLK40), .CE(1'b1), .R(1'b0), .S(1'b0), .Q(ClkBX) );
//assign ClkBX= CLK40 & EN_ClkBX_CONF;
assign ClkOut= RX_CLK & EN_ClkOut_CONF;

////////////////////////////////////////////
// INJECTION
`ifdef CODE_FOR_MIO3
pulse_gen640
#( 
    .BASEADDR(PULSE_INJ_BASEADDR), 
    .HIGHADDR(PULSE_INJ_HIGHADDR),
    .ABUSWIDTH(16),
    .CLKDV(4),
    .OUTPUT_SIZE(2)
) pulse_gen_inj (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .PULSE_CLK320(CLK320),
    .PULSE_CLK160(CLK160),
    .PULSE_CLK(CLK40),
    .EXT_START(GATE),
    .PULSE({InjLoopOut,Injection}),
    .DEBUG(DEBUG)
);
`else
pulse_gen 
#( 
    .BASEADDR(PULSE_INJ_BASEADDR), 
    .HIGHADDR(PULSE_INJ_HIGHADDR)
)     pulse_gen_inj(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .PULSE_CLK(CLK40),
    .EXT_START(GATE),
    .PULSE(InjLoopOut)
);
assign Injection = ~InjLoopOut;
`endif

wire Inj_Rise;
assign Inj_Rise = Injection;
//assign DEBUG_MUTINJRISE = 1'b1;
/**
pulse_gen #( 
    .BASEADDR(PULSE_MUTEINJRISE_BASEADDR), 
    .HIGHADDR(PULSE_MUTEINJRISE_HIGHADDR)
)     pulse_mute_injrise(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA[7:0]),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),

    .PULSE_CLK(CLK40),
    .EXT_START(Inj_Rise),
    .PULSE(DEBUG_MUTINJRISE)
);
**/

timestamp640
#(
    .BASEADDR(TS_BASEADDR),
    .HIGHADDR(TS_HIGHADDR),
    .IDENTIFIER(4'b0100)
)i_timestamp(
    .BUS_CLK(BUS_CLK),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RST(BUS_RST),
    .BUS_WR(BUS_WR),
    .BUS_RD(BUS_RD),
      
    .CLK320(CLK320),
    .CLK160(CLK160),
    .CLK40(CLK40),
    .DI(LEMO_RX[1]),
    .TIMESTAMP_OUT(),
    .EXT_TIMESTAMP(TIMESTAMP),
    .EXT_ENABLE(1'b1),

    .FIFO_READ(TS_FIFO_READ),
    .FIFO_EMPTY(TS_FIFO_EMPTY),
    .FIFO_DATA(TS_FIFO_DATA)
);

timestamp640
#(
    .BASEADDR(TS_INJ_BASEADDR),
    .HIGHADDR(TS_INJ_HIGHADDR),
    .IDENTIFIER(4'b0101)
)i_timestamp_inj(
    .BUS_CLK(BUS_CLK),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RST(BUS_RST),
    .BUS_WR(BUS_WR),
    .BUS_RD(BUS_RD),
      
    .CLK320(CLK320),
    .CLK160(CLK160),
    .CLK40(CLK40),
    .DI(InjLoopIn),   //loop back of injection (TX2 or flatcalbe)
    .TIMESTAMP_OUT(),
    .EXT_TIMESTAMP(TIMESTAMP),
    .EXT_ENABLE(GATE),

    .FIFO_READ(TS_INJ_FIFO_READ),
    .FIFO_EMPTY(TS_INJ_FIFO_EMPTY),
    .FIFO_DATA(TS_INJ_FIFO_DATA),

    .FIFO_READ_TRAILING(1'b0),
    .FIFO_EMPTY_TRAILING(),
    .FIFO_DATA_TRAILING()
);

timestamp640
#(
    .BASEADDR(TS_MON_BASEADDR),
    .HIGHADDR(TS_MON_HIGHADDR),
    .IDENTIFIER(4'b0110)
)i_timestamp160_mon(
    .BUS_CLK(BUS_CLK),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RST(BUS_RST),
    .BUS_WR(BUS_WR),
    .BUS_RD(BUS_RD),
      
    .CLK320(CLK320),
    .CLK160(CLK160),
    .CLK40(CLK40),
    .DI(HitOr),
    .TIMESTAMP_OUT(),
    .EXT_TIMESTAMP(TIMESTAMP),
    .EXT_ENABLE(1'b1),

    .FIFO_READ(TS_MON_FIFO_READ),
    .FIFO_EMPTY(TS_MON_FIFO_EMPTY),
    .FIFO_DATA(TS_MON_FIFO_DATA),
    
    .FIFO_READ_TRAILING(TS_MON_FIFO_READ_TRAILING),
    .FIFO_EMPTY_TRAILING(TS_MON_FIFO_EMPTY_TRAILING),
    .FIFO_DATA_TRAILING(TS_MON_FIFO_DATA_TRAILING)
);

//reset
reg ResetBcid_reg;
assign ResetBcid =EN_ResetBcid_WITH_TIMESTAMP ? ResetBcid_reg : ResetBcid_CONF;
always@(negedge CLK40) begin
    if (BUS_RST)
        ResetBcid_reg <= 1'b0;
    else if (TIMESTAMP[5:0]==6'h30)
        ResetBcid_reg <= ResetBcid_CONF;
end

reg MuteInjRise_reg;
assign DEBUG_MUTINJRISE = MuteInjRise_reg;
reg [8:0] mutinj_cnt = 9'b000000000;
always@ (posedge CLK40) begin
    if (DEBUG & (mutinj_cnt< 9'd320)) begin
        MuteInjRise_reg <= 1'b0;
        mutinj_cnt <= mutinj_cnt + 1'b1;
    end
    else if (DEBUG & (mutinj_cnt == 9'd320)) begin
        MuteInjRise_reg <= 1'b1;
    end
    else begin
        MuteInjRise_reg <= 1'b1;
        mutinj_cnt <= 9'b000000000;
    end
end

reg nRst_reg;
//assign nRst = (nRst_reg & MuteInjRise_reg);
assign nRst = nRst_reg;
always@(negedge CLK40)
    nRst_reg <= ~Rst_CONF;

endmodule
