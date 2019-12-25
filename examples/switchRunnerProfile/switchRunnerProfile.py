from pyppl import PyPPL, Proc

pHeatmap           = Proc(desc = 'Draw heatmap.')
pHeatmap.input     = {'seed': [1,2,3,4,5]}
pHeatmap.output    = "outfile:file:heatmap{{i.seed}}.png"
pHeatmap.args.ncol = 10
pHeatmap.args.nrow = 10
pHeatmap.lang      = 'Rscript' # or /path/to/Rscript if it's not in $PATH
pHeatmap.script = """
set.seed({{i.seed}})
mat = matrix(rnorm({{args.ncol, args.nrow | *lambda x, y: x*y}}), ncol={{args.ncol}})
png(filename = "{{o.outfile}}", width=150, height=150)
heatmap(mat)
dev.off()
"""

PyPPL(config_files = ['./PyPPL.toml']).start(pHeatmap).run('local5')
