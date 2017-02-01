from pyppl import pyppl
from helpers.proc import proc

"""
@description:
	convert TCGA sample names with submitter id with metadata and sample containing folder
@input:
	dir:file:    the directory containing the samples
	mdfile:file: the metadata file
@output:
	outdir:      the directory containing submitter-id named files
"""
TCGA_Sample2SubmitterID = proc ()
TCGA_Sample2SubmitterID.input     = "dir:file, mdfile:file"
TCGA_Sample2SubmitterID.output    = "outdir:file:out"
TCGA_Sample2SubmitterID.defaultSh = "python"
TCGA_Sample2SubmitterID.script    = """
import json, glob, os
if not os.path.exists ("{{outdir}}"):
	os.makedirs("{{outdir}}")
sam_meta = None
sample_ids = {}
with open ("{{mdfile}}") as f:
	sam_meta = json.load (f)

ext = ''
for sam in sam_meta:
	if not ext:
		ext = os.path.splitext (sam['file_name'])[1]
	sample_ids[sam['file_name']] = sam['associated_entities'][0]['entity_submitter_id'][:15]

for samfile in glob.glob (os.path.join("{{dir}}", "*", "*" + ext)):
	bn = os.path.basename (samfile)
	newfile = os.path.join ("{{outdir}}", sample_ids[bn] + ext)
	if os.path.exists (newfile):
		os.remove(newfile)
	os.symlink (samfile, newfile)
"""

"""
@description:
	Call DEG from expressoin matrix, where column names must in accordant order of <group>
@input:
	matfile:file: the expression matrix
	group1:       columns of group1 (separated by comma)
	group2:       columns of group2 (separated by comma)
	group1name:   the name of group1
	group2name:   the name of group2
@output:
	degfile:file: the output file containing DEGs
@args:
	pval: the cutoff of DEGs (default: .05)
@requires:
	limma (https://bioconductor.org/packages/release/bioc/html/limma.html)
"""
DEG_CallerByLimmaFromMatrix = proc ()
DEG_CallerByLimmaFromMatrix.input     = "matfile:file, group1, group2, group1name, group2name"
DEG_CallerByLimmaFromMatrix.output    = "degfile:file:{{matfile.fn}}.deg"
DEG_CallerByLimmaFromMatrix.args      = {'pval': 0.05}
DEG_CallerByLimmaFromMatrix.defaultSh = "Rscript"
DEG_CallerByLimmaFromMatrix.script    = """
library('limma')
expdata = read.table ("{{matfile}}", sep="\\t", header=T, row.names=1)
group1  = strsplit("{{group1}}", ",")[[1]]
group2  = strsplit("{{group2}}", ",")[[1]]
g1data  = expdata[, which(names(expdata) %in% group1)]
g2data  = expdata[, which(names(expdata) %in% group2)]

group   = c(rep("{{group1name}}", length(group1)), rep("{{group2name}}", length(group2)))
design  = model.matrix (~group)
fit     = lmFit (cbind(g1data, g2data), design)
fit     = eBayes(fit)
ret     = topTable(fit, n=length(fit$p.value))
out     = ret [ret$P.Value < {{proc.args.pval}}, ]
deg     = paste (rownames(out), collapse=',')
opv     = paste (format(out$P.Value, digits=3, scientific=T), collapse=',')
write (paste(deg, opv, sep="\\t"), file = "{{degfile}}", append=T)
"""

"""
@description:
	Call DEG from expression files
@input:
	expdir:file:  the directory containing expression files
	group1:       columns of group1 (separated by comma)
	group2:       columns of group2 (separated by comma)
	group1name:   the name of group1
	group2name:   the name of group2   
@output:
	degfile:file: the output file containing DEGs
@args:
	pval: the cutoff of DEGs (default: .05)
@requires:
	limma (https://bioconductor.org/packages/release/bioc/html/limma.html)
"""
DEG_CallerByLimmaFromFiles = proc ()
DEG_CallerByLimmaFromFiles.input     = "expdir:file, group1, group2, group1name, group2name"
DEG_CallerByLimmaFromFiles.output    = "degfile:file:{{matfile.fn}}.deg"
DEG_CallerByLimmaFromFiles.args      = {'pval': 0.05}
DEG_CallerByLimmaFromFiles.defaultSh = "Rscript"
DEG_CallerByLimmaFromFiles.script    = """
library('limma')
group1  = strsplit("{{group1}}", ",")[[1]]
group2  = strsplit("{{group2}}", ",")[[1]]

expmatrix = matrix()
for (i in 1:length (group1)) {
	file = paste ("{{expdir}}/", group1[i])
	if (grepl ('\\.gz$', group1[i])) {
		file = gzfile(file)
	}
	tmp  = read.table (file, sep="\\t", header=F, row.names = 1)
	expmatrix = cbind (expmatrix, tmp)
}

for (i in 1:length (group2)) {
	file = paste ("{{expdir}}/", group2[i])
	if (grepl ('\\.gz$', group2[i])) {
		file = gzfile(file)
	}
	tmp  = read.table (file, sep="\\t", header=F, row.names = 1)
	expmatrix = cbind (expmatrix, tmp)
}

group   = c(rep("{{group1name}}", length(group1)), rep("{{group2name}}", length(group2)))
design = model.matrix (~group)
fit    = lmFit (expmatrix, design)
fit    = eBayes(fit)
ret    = topTable(fit, n=length(fit$p.value))
out    = ret [ret$P.Value < {proc.args.pval}, ]
deg    = paste (rownames(out), collapse=',')
opv    = paste (format(out$P.Value, digits=3, scientific=T), collapse=',')
write (paste(deg, opv, sep="\\t"), file = "{degfile}", append=T)
"""


