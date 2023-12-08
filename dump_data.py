import os
import struct
from enum import Enum

from dataclasses import dataclass, field

import pyspread


# filename  = './roller/em0.emi'
filename  = './roller/second em0.emi'
program_size = 2000
step_offset = 1820
type_offset = 4
value_offset = 1004
name_position = 1840
name_length = 160

class Axis(Enum):
    X = 1
    Y = 2
    Z = 3
    S = 4
    u5 = 5
    u6= 6
    u7 = 7
    u8 = 8
    u9 = 9
    u10 = 10
    u15 = 15
    Xv = 11
    Xvv = 12
    u19 = 19
    HOLD = 13
    

@dataclass
class RollerProgram:
    """Roller Program Class"""
    name: str
    number:int 
    lines: [] = field(default_factory=list)
    
    # def __init__(self, name, number):
    #     self.name = name
    #     self.number = number
    #     self.lines = []
    
    def add_line(self, axis,value):
        self.lines.append([Axis(axis), value])
        
    def __str__(self):
        out = (f'{self.name}\t\t{self.number}\n')
        out = out + ('---------------------------------------------\n')
        for line in self.lines:
            out = out + (f'{line[0].name}\t\t{line[1]}\n')
        return out



def dump_first_program(f):
    #dump first program
    f.seek(2000+1820)
    data = struct.unpack("i",f.read(4))[0]
    print(f'Number of steps: {data}')
    data = struct.unpack("i",f.read(4))[0]
    print(f'Program #: {data}')
    f.seek(2000+1820+8+12)
    data = f.read(160)
    print(f'Program Name: {data.decode()}')
    
def get_program_list(f):
    """Return filenames and numbers in file"""
    # print('list programs')
    program_list = {}
    current_pos = 0
    filesize = os.path.getsize(filename)
    f.seek(program_size)
    f.seek(name_position,1)
    while ( f.tell() < filesize):
        current_pos =f.tell()
        data = f.read(name_length).split(b'\00')[0].decode()
        # data = f.read(name_length).decode().rstrip()

        if data:
            # print(f'Program Name: {data} at {current_pos}')
            end_of_program = f.tell()
            f.seek(-20-160,1)
            op = struct.unpack('i', f.read(4))[0]
            num = struct.unpack('i', f.read(4))[0]
            # print(f'program number {num}, with {op} steps')
            program_list[data] = num
            f.seek(end_of_program)
        f.seek(name_position,1)
        
    return program_list

def get_program(f, program_to_print = 1):    
    # program_to_print = 1

    program_address = program_to_print*program_size
    f.seek(program_address + step_offset)
    number_of_steps = struct.unpack('i', f.read(4))[0]
    unpack_format = 'i' * number_of_steps
    f.seek(program_address + type_offset)
    b_type =[x for x in struct.unpack(unpack_format, f.read(4*number_of_steps))]
    f.seek(program_address + value_offset)
    b_value = [x/10 for x in struct.unpack(unpack_format, f.read(4*number_of_steps))]
    f.seek(program_address+name_position)
    program_name = f.read(name_length).split(b'\00')[0].decode()

    # print(b_type)
    # print(b_value)
    p = RollerProgram(program_name,program_to_print)
    for x in range(0,number_of_steps):
        p.add_line(b_type[x],b_value[x])
    return p

if __name__=="__main__":
    with open(filename, 'rb') as f:
        programs = get_program_list(f)
        print(programs)
        # print(get_program( f, programs['FIRST']))
   


