from pyppl import PyPPL, Proc

pHeatmap           = Proc(desc = 'Draw heatmap.')
pHeatmap.input     = {'seed': [1,2,3]}
pHeatmap.output    = "outfile:file:heatmap{{in.seed}}.png"
pHeatmap.exdir     = "./export"
pHeatmap.forks     = 3
pHeatmap.args.ncol = 10
pHeatmap.args.nrow = 10
pHeatmap.lang      = 'Rscript' # or /path/to/Rscript if it's not in $PATH
pHeatmap.script = """
set.seed({{in.seed}})
mat = matrix(rnorm({{args.ncol, args.nrow | lambda x, y: x*y}}), ncol={{args.ncol}})
png(filename = "{{out.outfile}}", width=150, height=150)
heatmap(mat)
dev.off()
"""

PyPPL().start(pHeatmap).run()