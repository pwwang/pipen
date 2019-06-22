from pyppl import PyPPL, Proc

pHeatmap        = Proc(desc = 'Draw a heatmap.')
pHeatmap.input  = {'seed': 8525}
pHeatmap.output = "outfile:file:heatmap.png"
pHeatmap.exdir  = './export'
# or /path/to/Rscript if it's not in $PATH
pHeatmap.lang   = 'Rscript'
pHeatmap.script = """
set.seed({{i.seed}})
mat = matrix(rnorm(100), ncol=10)
png(filename = "{{o.outfile}}")
heatmap(mat)
dev.off()
"""

PyPPL().start(pHeatmap).run()