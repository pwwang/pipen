# [PyPPL][3] - A [Py](#)thon [P](#)i[P](#)e[L](#)ine framework

![Pypi][22] ![Github][23] ![PythonVers][37] ![Travis building][8]  ![Codacy][4] ![Codacy coverage][11]

[Documentation][1] | [API][2] | [Change log][19]

<!-- toc -->
## Features
- Process caching.
- Process reusability.
- Process error handling.
- Runner customization.
- Running profile switching.
- Pipeline flowchart.

## Installation
```bash
pip install PyPPL
```

## Writing pipelines with predefined processes
Let's say we are implementing the [TCGA DNA-Seq Re-alignment Workflow][42]

(The very left part of following figure):

For demonstration, we will skip the QC and the Co-clean part here.

[![DNA_Seq_Variant_Calling_Pipeline][41]][42]

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
Note that this function requires [Graphviz][44] and [graphviz for python][36].



[1]: https://pwwang.github.io/PyPPL/
[2]: https://pwwang.github.io/PyPPL/api/
[3]: https://github.com/pwwang/pyppl/
[4]: https://img.shields.io/codacy/grade/a04aac445f384a8dbe47da19c779763f.svg?style=flat-square
[5]: https://github.com/pwwang/testly
[6]: https://pwwang.github.io/PyPPL/caching/
[7]: https://pwwang.github.io/PyPPL/placeholders/
[8]: https://img.shields.io/travis/pwwang/PyPPL.svg?style=flat-square
[9]: https://pwwang.github.io/PyPPL/runners/
[10]: https://pwwang.github.io/PyPPL/error-handling/
[11]: https://img.shields.io/codacy/coverage/a04aac445f384a8dbe47da19c779763f.svg?style=flat-square
[12]: https://pwwang.github.io/PyPPL/set-other-properties-of-a-process/#error-handling-perrhowperrntry
[13]: https://pwwang.github.io/PyPPL/configure-a-pipeline/#use-a-configuration-file
[14]: https://en.wikipedia.org/wiki/DOT_(graph_description_language)
[15]: https://pwwang.github.io/PyPPL/draw-flowchart-of-a-pipeline/
[16]: https://pwwang.github.io/PyPPL/aggregations/
[17]: https://github.com/pwwang/liquidpy
[18]: https://raw.githubusercontent.com/pwwang/PyPPL/master/docs/drawFlowchart_pyppl.png
[19]: https://pwwang.github.io/PyPPL/change-log/
[20]: https://pwwang.github.io/PyPPL/getStarted.gif
[21]: https://pypi.org/project/futures/
[22]: https://img.shields.io/pypi/v/pyppl.svg?style=flat-square
[23]: https://img.shields.io/github/tag/pwwang/PyPPL.svg?style=flat-square
[24]: https://github.com/pwwang/bioprocs
[25]: https://github.com/benjaminp/six
[26]: https://pwwang.github.io/PyPPL/faq/
[27]: https://pwwang.github.io/PyPPL/command-line-argument-parser/
[28]: https://pwwang.github.io/PyPPL/configure-your-logs/
[29]: https://raw.githubusercontent.com/pwwang/PyPPL/master/docs/heatmap.png
[30]: https://raw.githubusercontent.com/pwwang/PyPPL/master/docs/heatmap1.png
[31]: https://raw.githubusercontent.com/pwwang/PyPPL/master/docs/heatmap2.png
[32]: https://raw.githubusercontent.com/pwwang/PyPPL/master/docs/heatmap3.png
[33]: https://github.com/yaml/pyyaml
[34]: https://raw.githubusercontent.com/pwwang/PyPPL/master/docs/debugScript.png
[35]: https://github.com/benediktschmitt/py-filelock
[36]: https://github.com/xflr6/graphviz
[44]: https://www.graphviz.org/
[37]: https://img.shields.io/pypi/pyversions/PyPPL.svg?style=flat-square
[38]: https://img.shields.io/github/license/pwwang/PyPPL.svg?style=flat-square
[39]: http://jinja.pocoo.org/
[40]: https://pypi.org/project/colorama/
[41]: https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/images/dna-alignment-pipeline_0.png
[42]: https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/DNA_Seq_Variant_Calling_Pipeline/
