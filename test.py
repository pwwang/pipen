from pipen import Pipen, Proc
from pipen_args import params

class Process(Proc):
    input_keys = ['a', 'b']
    input = [(1, 3), (2, 4)]
    args = {'a': 1}
    output = 'a:{{in.a}}'
    script = "echo {{in.a}} {{in.b}}"

class Process2(Proc):
    input_keys = 'a'
    requires = Process
    script = 'echo {{in.a}}'

pipen = Pipen(starts=Process, loglevel='debug')

pipen.run()
