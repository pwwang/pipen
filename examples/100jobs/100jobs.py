from pyppl import PyPPL, Proc

p100 = Proc()
p100.input = {'a': list(range(100))}
p100.output = 'a:var:1'
p100.args.a = 1
p100.forks = 16

PyPPL().start(p100).run()
