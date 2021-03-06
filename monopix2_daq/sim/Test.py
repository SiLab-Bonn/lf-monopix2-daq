#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#
# Initial version by Chris Higgs <chris.higgs@potentialventures.com>
#


import logging
import os
import socket
import yaml

import cocotb
from cocotb.triggers import RisingEdge

from monopix2_daq.sim.Protocol import WriteRequest, ReadRequest, ReadResponse, PickleInterface, ReadRequestStr


def get_bus():
    bus_name_path = os.getenv("SIMULATION_BUS", "monopix2_daq.sim.BasilBusDriver")
    bus_name = bus_name_path.split('.')[-1]
    return getattr(__import__(bus_name_path, fromlist=[bus_name]), bus_name)


def import_driver(path):
    name = path.split('.')[-1]
    return getattr(__import__(path, fromlist=[name]), name)


@cocotb.test(skip=False)
def socket_test(dut, debug=False):
    """Testcase that uses a socket to drive the DUT"""

    host = os.getenv("SIMULATION_HOST", 'localhost')
    port = os.getenv("SIMULATION_PORT", '12345')

    if debug:
        dut._log.setLevel(logging.DEBUG)

    bus = get_bus()(dut)

    dut._log.info("Using bus driver : %s" % (type(bus).__name__))

    sim_modules = []
    sim_modules_data = os.getenv("SIMULATION_MODULES", "")
    if sim_modules_data:
        sim_modules_yml = yaml.safe_load(sim_modules_data)
        for mod in sim_modules_yml:
            mod_import = import_driver(mod)
            kargs = dict(sim_modules_yml[mod])
            sim_modules.append(mod_import(dut, **kargs))
            dut._log.info("Using simulation modules : %s  arguments: %s" % (mod, kargs))

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((host, int(port)))
        s.listen(1)
    except Exception:
        s.close()
        s = None
        raise

    # start sim_modules
    for mod in sim_modules:
        cocotb.fork(mod.run())

    yield bus.init()

    while True:
        dut._log.info("Waiting for incoming connection on %s:%d" % (host, int(port)))
        clientsocket, socket_address = s.accept()
        dut._log.info("New connection from %s:%d" % (socket_address[0], socket_address[1]))
        iface = PickleInterface(clientsocket)

        while True:
            # uncomment for constantly advancing clock
            # yield RisingEdge(bus.clock)

            try:
                req = iface.try_recv()
            except EOFError:
                dut._log.info("Remote server closed the connection")
                clientsocket.shutdown(socket.SHUT_RDWR)
                clientsocket.close()
                break
            if req is None:
                continue

            dut._log.debug("Received: %s" % str(req))

            # add few clocks
            for _ in range(10):
                yield RisingEdge(bus.clock)

            if isinstance(req, WriteRequest):
                yield bus.write(req.address, req.data)
            elif isinstance(req, ReadRequest):
                result = yield bus.read(req.address, req.size)
                resp = ReadResponse(result)
                dut._log.debug("Send: %s" % str(resp))
                iface.send(resp)
            elif isinstance(req, ReadRequestStr):
                result = yield bus.read(req.address, req.size, dtype="s")
                resp = ReadResponse(result)
                dut._log.debug("Send: %s" % str(resp))
                iface.send(resp)
            else:
                raise NotImplementedError("Unsupported request type: %s" % str(type(req)))

            # add few clocks
            for _ in range(10):
                yield RisingEdge(bus.clock)

        if(os.getenv("SIMULATION_END_ON_DISCONNECT")):
            break

    s.shutdown(socket.SHUT_RDWR)
    s.close()


@cocotb.test(skip=True)
def bringup_test(dut):
    """Initial test to see if simulation works"""

    bus = get_bus()(dut)

    yield bus.init()

    for _ in range(10):
        yield RisingEdge(bus.clock)

    yield bus.write(0, [0xff, 0xf2, 0xf3, 0xa4])

    for _ in range(10):
        yield RisingEdge(bus.clock)

    ret = yield bus.read(0, 4)

    print('bus.read {}'.format(ret))

    for _ in range(10):
        yield RisingEdge(bus.clock)
