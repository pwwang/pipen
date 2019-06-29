from pyppl import PyPPL, Channel
# import predefined processes
from TCGAprocs import pBamToFastq, pAlignment, pBamSort, pBamMerge, pMarkDups

# Load the bam files
pBamToFastq.input = Channel.fromPattern('./data/*.bam')
# Align the reads to reference genome
pAlignment.depends = pBamToFastq
# Sort bam files
pBamSort.depends = pAlignment
# Merge bam files
pBamMerge.depends = pBamSort
# Mark duplicates
pMarkDups.depends = pBamMerge
# Export the results
pMarkDups.exdir = './export/realigned_Bams'
# Specify the start process and run the pipeline
PyPPL().start(pBamToFastq).flowchart().run({'forks': 2, '_log': {'shorten': 40}})
