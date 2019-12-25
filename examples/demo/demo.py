from pyppl import PyPPL, Channel, config_plugins
# import predefined processes
from TCGAprocs import pBamToFastq, pAlignment, pBamSort, pBamMerge, pMarkDups

# Load the bam files
pBamToFastq.input = Channel.from_pattern('./data/*.bam')
# Align the reads to reference genome
pAlignment.depends = pBamToFastq
# Sort bam files
pBamSort.depends = pAlignment
# Merge bam files
pBamMerge.depends = pBamSort
# Mark duplicates
pMarkDups.depends = pBamMerge
# Export the results
pMarkDups.plugin_config.export_dir = './export/realigned_Bams'
# Specify the start process and run the pipeline
PyPPL(forks = 2).start(pBamToFastq).flowchart().run()
