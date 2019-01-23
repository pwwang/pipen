from pyppl import PyPPL, Proc

pHeatmap           = Proc(desc = 'Draw heatmap.')
pHeatmap.input     = {'seed': [1,2,3,4,5]}
pHeatmap.output    = "outfile:file:heatmap{{i.seed}}.png"
pHeatmap.exdir     = "./export"
# Don't cache jobs for debugging
pHeatmap.cache     = False
# Output debug information for all jobs, but don't echo stdout and stderr
pHeatmap.echo      = {'jobs': range(5), 'type': ''}
pHeatmap.forks     = 5
pHeatmap.args.ncol = 10
pHeatmap.args.nrow = 10
pHeatmap.lang      = 'Rscript' # or /path/to/Rscript if it's not in $PATH
pHeatmap.script = """
set.seed({{i.seed}})
Sys.sleep({{job.index}})
mat = matrix(rnorm({{args.ncol, args.nrow | *lambda x, y: x*y}}), ncol={{args.ncol}})
png(filename = "{{o.outfile}}", width=150, height=150)

# have to be on stderr
cat("pyppl.log.debug:Plotting heatmap #{{job.index | lambda x: int(x) + 1}} ...", file = stderr())

heatmap(mat)
dev.off()
"""

PyPPL({
	'_log': {
		'levels' : 'basic',
		'lvldiff': []
	}
}).start(pHeatmap).run()
