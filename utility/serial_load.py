#!/usr/bin/env python

import sys
import os
import serial
import struct
import time
import random
import binascii
import select
from elftools.elf.elffile import ELFFile

ser = serial.Serial('/dev/cu.usbserial', 115200, timeout=1)

def write_uart(buf):
    ser.write(buf)
    ser.flush()

def write_ram(start, content):
    time.sleep(0.01)
    write_uart('0')
    x = ser.read(1)
    if not x:
        print "ack timed out"
        raise IOError
        return
    assert x=='~'

    write_uart(struct.pack('<I',start))
    time.sleep(0.01)
    write_uart(struct.pack('<I',(len(content)+3)/4))
    # for b in struct.pack('<I',start):
    #     write_uart(b)
    #     time.sleep(0.01)
    # for b in struct.pack('<I',(len(content)+3)/4):
    #     write_uart(b)
    #     time.sleep(0.01)

    time.sleep(0.01)

    cnt=0
    for b in content:
        write_uart(b)
        time.sleep(0.0001)
        cnt+=1

    while cnt%4!=0:
        write_uart('\x00')
        time.sleep(0.01)
        cnt+=1

    print "%d bytes written"%cnt

def read_ram(start, length):
    time.sleep(0.01)
    write_uart('1')
    x = ser.read(1)
    if not x:
        print "ack timed out"
        raise IOError
        return
    assert x=='~'

    length = (length+3)/4*4 #round up

    write_uart(struct.pack('<I',start))
    time.sleep(0.01)
    write_uart(struct.pack('<I',length/4))
    # for b in struct.pack('<I',start):
    #     write_uart(b)
    #     time.sleep(0.01)
    # for b in struct.pack('<I',length/4):
    #     write_uart(b)
    #     time.sleep(0.01)

    buf = ser.read(length)
    if len(buf) < length:
        print "read data timed out"
        raise IOError
        return
    print "%d bytes read"%len(buf)
    return buf

def go_ram(start):
    time.sleep(0.01)
    write_uart('4')
    x = ser.read(1)
    if not x:
        print "ack timed out"
        raise IOError
        return
    assert x=='~'

    write_uart(struct.pack('<I',start))
    print "Go: 0x%x"%start

def uart_loopback_test():
    time.sleep(0.01)
    write_uart('5')
    x = ser.read(1)
    if not x:
        print "ack timed out"
        raise IOError
        return
    assert x=='~'

    while True:
        t = random.randint(0,2**32-1)
        sent = struct.pack('<I',t)
        # for b in sent:
        #     write_uart(b)
        #     time.sleep(0.1)
        write_uart(sent)
        recv = ser.read(4)
        if not recv:
            print "read data timed out"
            raise IOError
            return
        for i in xrange(4):
            assert recv[i] == sent[i]

def ram_test():

    while True:
        size = 128*1024
        offset = 0*1024
        # data = ''.join(chr(random.randint(0,255)) for _ in range(size))
        data = ''.join('\xaa' for _ in range(size))

        write_ram(offset, data)
        # raw_input("Press Enter to continue...")
        recv = read_ram(offset, size)


        if data != recv:
            print binascii.hexlify(data)
            print binascii.hexlify(recv)
            for x in xrange(size):
                if data[x] != recv[x]:
                    print "%x!=%x @ 0x%x" % (ord(data[x]),ord(recv[x]),x)
            break

def load_and_run(f, addr, entry):
    size = os.fstat(f.fileno()).st_size
    print "File size: %d" % size
    print "Load address: 0x%x" % addr
    print "Entry point: 0x%x" % entry

    write_ram(addr, f.read())
    go_ram(entry)


def load_elf_and_run(f):
    elffile = ELFFile(f)

    for segment in elffile.iter_segments():
        print "Program Header: Size: %d, Virtual Address: 0x%x" % (segment['p_filesz'], segment['p_vaddr'])
        if segment['p_filesz']==0 or segment['p_vaddr']==0:
            print "Skipped"
            continue
        write_ram(segment['p_vaddr'], segment.data())

    print "Entry: 0x%x" % elffile['e_entry']
    go_ram(elffile['e_entry'])

def start_terminal():
    slt_list = [sys.stdin, ser]
    while True:
        ready = select.select(slt_list, [], [])
        if ser in ready:
            recv = ser.read()
            if not(recv is None):
                sys.stdout.write(recv)
        if sys.stdin in ready:
            recv = sys.stdin.read()
            if not(recv is None):
                write_uart(recv)

# uart_loopback_test()
# ram_test()

with open(sys.argv[1], 'rb') as f:
    # ram_test()
    # uart_loopback_test()
    # load_and_run(f, 0, 0)
    # load_elf_and_run(f)

    start_terminal()