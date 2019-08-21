# [PyPPL][3] - A [Py](#)thon [P](#)i[P](#)e[L](#)ine framework

[![Pypi][10]][18] [![Github][11]][3] [![PythonVers][14]][18] [![docs][19]][1] [![Travis building][5]][7] [![Codacy][4]][8] [![Codacy coverage][6]][8]

[Documentation][1] | [API][2] | [Change log][9]

<!-- toc -->
## Features
- Process caching.
- Process reusability.
- Process error handling.
- Runner customization.
- Running profile switching.
- Plugin system.
- Pipeline flowchart (using plugin [pyppl_flowchart][22]).
- Pipeline report (using plugin [pyppl_report][23]).

## Installation
```bash
pip install PyPPL
```

## Writing pipelines with predefined processes
Let's say we are implementing the [TCGA DNA-Seq Re-alignment Workflow][16]
(The very left part of following figure).
For demonstration, we will skip the QC and the co-clean parts here.

[![DNA_Seq_Variant_Calling_Pipeline][15]][16]

`demo.py`:
```python
from pyppl import PyPPL, Channel
# import predefined processes
from TCGAprocs import pBamToFastq, pAlignment, pBamSort, pBamMerge, pMarkDups

# Load the bam files
pBamToFastq.input = Channel.fromPattern('/path/to/*.bam')
# Align the reads to reference genome
pAlignment.depends = pBamToFastq
# Sort bam files
pBamSort.depends = pAlignment
# Merge bam files
pBamMerge.depends = pBamSort
# Mark duplicates
pMarkDups.depends = pBamMerge
# Export the results
pMarkDups.exdir = '/path/to/realigned_Bams'
# Specify the start process and run the pipeline
PyPPL().start(pBamToFastq).run()
```

[![asciicast][20]][21]

## Implementing individual processes
`TCGAprocs.py`:
```python
from pyppl import Proc
pBamToFastq = Proc(desc = 'Convert bam files to fastq files.')
pBamToFastq.input = 'infile:file'
pBamToFastq.output = [
    'fq1:file:{{i.infile | stem}}_1.fq.gz',
    'fq2:file:{{i.infile | stem}}_2.fq.gz']
pBamToFastq.script = '''
bamtofastq collate=1 exclude=QCFAIL,SECONDARY,SUPPLEMENTARY \
    filename= {{i.infile}} gz=1 inputformat=bam level=5 \
    outputdir= {{job.outdir}} outputperreadgroup=1 tryoq=1 \
    outputperreadgroupsuffixF=_1.fq.gz \
    outputperreadgroupsuffixF2=_2.fq.gz \
    outputperreadgroupsuffixO=_o1.fq.gz \
    outputperreadgroupsuffixO2=_o2.fq.gz \
    outputperreadgroupsuffixS=_s.fq.gz
'''

pAlignment = Proc(desc = 'Align reads to reference genome.')
pAlignment.input = 'fq1:file, fq2:file'
#                             name_1.fq.gz => name.bam
pAlignment.output = 'bam:file:{{i.fq1 | stem | stem | [:-2]}}.bam'
pAlignment.script = '''
bwa mem -t 8 -T 0 -R <read_group> <reference> {{i.fq1}} {{i.fq2}} | \
    samtools view -Shb -o {{o.bam}} -
'''

pBamSort = Proc(desc = 'Sort bam files.')
pBamSort.input = 'inbam:file'
pBamSort.output = 'outbam:file:{{i.inbam | basename}}'
pBamSort.script = '''
java -jar picard.jar SortSam CREATE_INDEX=true INPUT={{i.inbam}} \
    OUTPUT={{o.outbam}} SORT_ORDER=coordinate VALIDATION_STRINGENCY=STRICT
'''

pBamMerge = Proc(desc = 'Merge bam files.')
pBamMerge.input = 'inbam:file'
pBamMerge.output = 'outbam:file:{{i.inbam | basename}}'
pBamMerge.script = '''
java -jar picard.jar MergeSamFiles ASSUME_SORTED=false CREATE_INDEX=true \
    INPUT={{i.inbam}} MERGE_SEQUENCE_DICTIONARIES=false OUTPUT={{o.outbam}} \
    SORT_ORDER=coordinate USE_THREADING=true VALIDATION_STRINGENCY=STRICT
'''

pMarkDups = Proc(desc = 'Mark duplicates.')
pMarkDups.input = 'inbam:file'
pMarkDups.output = 'outbam:file:{{i.inbam | basename}}'
pMarkDups.script = '''
java -jar picard.jar MarkDuplicates CREATE_INDEX=true INPUT={{i.inbam}} \
    OUTPUT={{o.outbam}} VALIDATION_STRINGENCY=STRICT
'''
```

Each process is indenpendent so that you may also reuse the processes in other pipelines.

## Pipeline flowchart
```python
# When try to run your pipline, instead of:
#   PyPPL().start(pBamToFastq).run()
# do:
PyPPL().start(pBamToFastq).flowchart().run()
```
Then an SVG file endswith `.pyppl.svg` will be generated under current directory.
Note that this function requires [Graphviz][13] and [graphviz for python][12].

See plugin [details][22].

![flowchart][17]

## Pipeline report
See plugin [details][23]

````python
pPyClone.report = """
## {{title}}

PyClone[1] is a tool using Probabilistic model for inferring clonal population structure from deep NGS sequencing.

![Similarity matrix]({{path.join(job.o.outdir, "plots/loci/similarity_matrix.svg")}})

```table
caption: Clusters
file: "{{path.join(job.o.outdir, "tables/cluster.tsv")}}"
rows: 10
```

[1]: Roth, Andrew, et al. "PyClone: statistical inference of clonal population structure in cancer." Nature methods 11.4 (2014): 396.
"""

# or use a template file

pPyClone.report = "file:/path/to/template.md"
````

```python
PyPPL().start(pPyClone).run().report('/path/to/report', title = 'Clonality analysis using PyClone')
```

![report][24]

## Full documentation
[ReadTheDocs][1]


[1]: https://pyppl.readthedocs.io/en/latest/
[2]: https://pyppl.readthedocs.io/en/latest/api/
[3]: https://github.com/pwwang/pyppl/
[4]: https://img.shields.io/codacy/grade/a04aac445f384a8dbe47da19c779763f.svg?style=flat-square
[5]: https://img.shields.io/travis/pwwang/PyPPL.svg?style=flat-square
[6]: https://img.shields.io/codacy/coverage/a04aac445f384a8dbe47da19c779763f.svg?style=flat-square
[7]: https://travis-ci.org/pwwang/PyPPL
[8]: https://app.codacy.com/project/pwwang/PyPPL/dashboard
[9]: https://pyppl.readthedocs.io/en/latest/CHANGELOG/
[10]: https://img.shields.io/pypi/v/pyppl.svg?style=flat-square
[11]: https://img.shields.io/github/tag/pwwang/PyPPL.svg?style=flat-square
[12]: https://github.com/xflr6/graphviz
[13]: https://www.graphviz.org/
[14]: https://img.shields.io/pypi/pyversions/PyPPL.svg?style=flat-square
[15]: https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/images/dna-alignment-pipeline_0.png
[16]: https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/DNA_Seq_Variant_Calling_Pipeline/
[17]: https://raw.githubusercontent.com/pwwang/PyPPL/development/examples/demo/demo.pyppl.svg?sanitize=true
[18]: https://pypi.org/project/PyPPL/
[19]: https://img.shields.io/readthedocs/pyppl.svg?style=flat-square
[20]: https://asciinema.org/a/Uiz6Wdo1buGCGPFd89bWiZzwn.svg?sanitize=true
[21]: https://asciinema.org/a/Uiz6Wdo1buGCGPFd89bWiZzwn
[22]: https://github.com/pwwang/pyppl_flowchart
[23]: https://github.com/pwwang/pyppl_report
[24]: https://pyppl_report.readthedocs.io/en/latest/snapshot.png
