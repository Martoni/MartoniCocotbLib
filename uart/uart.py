#! /usr/bin/python3
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Author:   Fabien Marteau <mail@fabienm.eu>
# Created:  12/12/2018
#-----------------------------------------------------------------------------
#  Copyright (2018)
#-----------------------------------------------------------------------------
""" cocotb uart quick and dirty library
"""

import sys
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, FallingEdge, RisingEdge, ReadOnly
from cocotb.result import TestError
import logging


class Uart(object):
    """
    """

    def __init__(self, dut, clock, rx, tx,
                speed=57600, parity=False,
                datasize=8, stop=True):
        self._dut = dut
        self._log = dut._log
        self.clock = clock
        self.rx = rx
        self.tx = tx
        self.speed = speed
        self._period = 10**9/speed
        self.parity = parity
        self.datasize = datasize
        self.stop = stop
        if(parity):
            self._log.info("Parity not implemented yet")
            raise Exception()
        if(datasize!=8):
            self._log.info("Only 8 bits supported")
            raise Exception()
        self.rx_buf = []

    @property
    def rx_str(self):
        return "".join([chr(value) for value in self.rx_buf]).split('\r')

    @cocotb.coroutine
    def init(self):
        self._log.debug("initialize uart")
        self.tx <= 1
        self.rx_buf = []
        self._rcv = cocotb.fork(self.rcv())
        yield RisingEdge(self.clock)

    @cocotb.coroutine
    def rcv(self):
        """ Monitor RX and add byte received to rx_buf list """
        self._log.debug("launching rcv monitor")
        onebaud = Timer(self._period + 300, units="ns") #XXX
        frx = FallingEdge(self.rx)
        rrx = RisingEdge(self.rx)
        while True:
            yield frx
            # wait start bit
            yield [onebaud, frx, rrx]
            readingvalue = ""
            for i in range(self.datasize):
                readingvalue = "{:1d}".format(self.rx.value.integer) + readingvalue
                yield [onebaud, frx, rrx]
            # read last bit
            #wait stop bit
            yield [onebaud, frx, rrx]
            readingvalue = "0b" + readingvalue
            self.rx_buf.append(int(readingvalue, 2))
            if(int(readingvalue, 2) == 0x0D):
                self._log.info("Read char \\r (value 0x0D)")
            else:
                self._log.info("Read char {} (value {:02X})"
                            .format(chr(int(readingvalue, 2)),
                            int(readingvalue, 2)))

    @cocotb.coroutine
    def send(self, onebyte):
        """ send a uart frame, onebyte is an unsigned integer"""
        onebaud = Timer(self._period, units="ns") 
        # start bit
        self.tx <= 0
        yield onebaud
        sbyte = onebyte&0xff
        for i in range(self.datasize):
            self.tx <= sbyte&0x01
            sbyte = sbyte >> 1
            yield onebaud
        if(self.stop):
            self.tx <= 1
            yield onebaud

    @cocotb.coroutine
    def sendcmd(self, cmd, intertime=10, units="ns", log=None):
        """ sent a uart command. cmd is a caracter string, intertime give 
        the time between two caracters sent unit is baud"""
        itte = Timer(intertime, units=units)
        for car in cmd:
            if log is not None:
                log.info("sending {}".format(car))
            word = ord(car)
            yield self.send(word)
            yield itte
