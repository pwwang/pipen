.. role:: raw-html-m2r(raw)
   :format: html


`PyPPL <https://github.com/pwwang/pyppl/>`_ - A `Py <#>`_\ thon `P <#>`_\ i\ `P <#>`_\ e\ `L <#>`_\ ine framework
=========================================================================================================================

`
.. image:: https://img.shields.io/pypi/v/pyppl.svg?style=flat-square
   :target: https://img.shields.io/pypi/v/pyppl.svg?style=flat-square
   :alt: Pypi
 <https://pypi.org/project/PyPPL/>`_ `
.. image:: https://img.shields.io/github/tag/pwwang/PyPPL.svg?style=flat-square
   :target: https://img.shields.io/github/tag/pwwang/PyPPL.svg?style=flat-square
   :alt: Github
 <https://github.com/pwwang/pyppl/>`_ `
.. image:: https://img.shields.io/pypi/pyversions/PyPPL.svg?style=flat-square
   :target: https://img.shields.io/pypi/pyversions/PyPPL.svg?style=flat-square
   :alt: PythonVers
 <https://pypi.org/project/PyPPL/>`_ `
.. image:: https://img.shields.io/readthedocs/pyppl.svg?style=flat-square
   :target: https://img.shields.io/readthedocs/pyppl.svg?style=flat-square
   :alt: docs
 <https://pyppl.readthedocs.io/en/latest/>`_ `
.. image:: https://img.shields.io/travis/pwwang/PyPPL.svg?style=flat-square
   :target: https://img.shields.io/travis/pwwang/PyPPL.svg?style=flat-square
   :alt: Travis building
 <https://travis-ci.org/pwwang/PyPPL>`_ `
.. image:: https://img.shields.io/codacy/grade/a04aac445f384a8dbe47da19c779763f.svg?style=flat-square
   :target: https://img.shields.io/codacy/grade/a04aac445f384a8dbe47da19c779763f.svg?style=flat-square
   :alt: Codacy
 <https://app.codacy.com/project/pwwang/PyPPL/dashboard>`_ `
.. image:: https://img.shields.io/codacy/coverage/a04aac445f384a8dbe47da19c779763f.svg?style=flat-square
   :target: https://img.shields.io/codacy/coverage/a04aac445f384a8dbe47da19c779763f.svg?style=flat-square
   :alt: Codacy coverage
 <https://app.codacy.com/project/pwwang/PyPPL/dashboard>`_

`Documentation <https://pyppl.readthedocs.io/en/latest/>`_ | `API <https://pyppl.readthedocs.io/en/latest/api/>`_ | `Change log <https://pyppl.readthedocs.io/en/latest/CHANGELOG/>`_

:raw-html-m2r:`<!-- toc -->`

Features
--------


* Process caching.
* Process reusability.
* Process error handling.
* Runner customization.
* Running profile switching.
* Plugin system.
* Pipeline flowchart (using plugin `pyppl_flowchart <https://github.com/pwwang/pyppl_flowchart>`_\ ).
* Pipeline report (using plugin `pyppl_report <https://github.com/pwwang/pyppl_report>`_\ ).

Installation
------------

.. code-block:: bash

   pip install PyPPL

Writing pipelines with predefined processes
-------------------------------------------

Let's say we are implementing the `TCGA DNA-Seq Re-alignment Workflow <https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/DNA_Seq_Variant_Calling_Pipeline/>`_
(The very left part of following figure).
For demonstration, we will skip the QC and the co-clean parts here.

`
.. image:: https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/images/dna-alignment-pipeline_0.png
   :target: https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/images/dna-alignment-pipeline_0.png
   :alt: DNA_Seq_Variant_Calling_Pipeline
 <https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/DNA_Seq_Variant_Calling_Pipeline/>`_

``demo.py``\ :

.. code-block:: python

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

`
.. image:: https://asciinema.org/a/Uiz6Wdo1buGCGPFd89bWiZzwn.svg?sanitize=true
   :target: https://asciinema.org/a/Uiz6Wdo1buGCGPFd89bWiZzwn.svg?sanitize=true
   :alt: asciicast
 <https://asciinema.org/a/Uiz6Wdo1buGCGPFd89bWiZzwn>`_

Implementing individual processes
---------------------------------

``TCGAprocs.py``\ :

.. code-block:: python

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

Each process is indenpendent so that you may also reuse the processes in other pipelines.

Pipeline flowchart
------------------

.. code-block:: python

   # When try to run your pipline, instead of:
   #   PyPPL().start(pBamToFastq).run()
   # do:
   PyPPL().start(pBamToFastq).flowchart().run()

Then an SVG file endswith ``.pyppl.svg`` will be generated under current directory.
Note that this function requires `Graphviz <https://www.graphviz.org/>`_ and `graphviz for python <https://github.com/xflr6/graphviz>`_.

See plugin `details <https://github.com/pwwang/pyppl_flowchart>`_.


.. image:: https://raw.githubusercontent.com/pwwang/PyPPL/development/examples/demo/demo.pyppl.svg?sanitize=true
   :target: https://raw.githubusercontent.com/pwwang/PyPPL/development/examples/demo/demo.pyppl.svg?sanitize=true
   :alt: flowchart


Pipeline report
---------------

See plugin `details <https://github.com/pwwang/pyppl_report>`_

.. code-block:: python

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

.. code-block:: python

   PyPPL().start(pPyClone).run().report('/path/to/report', title = 'Clonality analysis using PyClone')


.. image:: https://pyppl_report.readthedocs.io/en/latest/snapshot.png
   :target: https://pyppl_report.readthedocs.io/en/latest/snapshot.png
   :alt: report


Full documentation
------------------

`ReadTheDocs <https://pyppl.readthedocs.io/en/latest/>`_