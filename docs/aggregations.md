# Aggregations
<!-- toc -->

Imagine that you have a set of processes predefined, and every time when you deal with similar problems (i.e. format a file and plot the data or some next generation sequencing data analysis), you will consistently use those processes, then you have to configure and call them every time. 

Aggregations are designed for this kind of situations, you can just define an aggregations with those processes, and adjust the dependencies, input and arguments, you will be able to re-use the aggregation with very less configuration.

For example:
```python
pTrimmomaticPE.input             = {pTrimmomaticPE.input: inchan}
pAlignPEByBWA.depends            = pTrimmomaticPE
pSortSam.depends                 = pAlignPEByBWA
pMarkDuplicates.depends          = pSortSam
pIndexBam.depends                = pMarkDuplicates
pRealignerTargetCreator.depends  = pIndexBam
pIndelRealigner.depends          = [pIndexBam, pRealignerTargetCreator]
pBaseRecalibrator.depends        = pIndelRealigner
pPrintReads.depends              = [pIndelRealigner, pBaseRecalibrator]
pPrintReads.exportdir            = exdir

pMarkDuplicates.args['params']         += ' TMP_DIR="/local2/tmp/"'
pAlignPEByBWA.args['reffile']           = reffile
pRealignerTargetCreator.args['reffile'] = reffile
pRealignerTargetCreator.args['params'] += ' -Djava.io.tmpdir=/local2/tmp/'
pIndelRealigner.args['reffile']         = reffile
pIndelRealigner.args['params']         += ' -Djava.io.tmpdir=/local2/tmp/'
pBaseRecalibrator.args['reffile']       = reffile
pBaseRecalibrator.args['knownSites']    = dbsnp
pBaseRecalibrator.args['params']       += ' -Djava.io.tmpdir=/local2/tmp/'
pPrintReads.args['reffile']             = reffile
pPrintReads.args['params']             += ' -Djava.io.tmpdir=/local2/tmp/'

pyppl.pyppl({
    'proc': {
        'forks': 100,
        'runner': 'sge',
        'sgeRunner': {
            'sge_q': 'lg-mem'
        }
    }
}).starts(pTrimmomaticPE).run()
```
This is a very commonly used Whole Genome Sequencing data cleanup pipeline from the raw reads according to the [GATK best practice](https://software.broadinstitute.org/gatk/best-practices/). And it will be used pretty much every time when the raw read files come. 

With an aggregation defined, you don't need to configure and call those processes every time:
```python
# some paramters defined in params
aFastqPE2Bam = aggr (
    pTrimmomaticPE,
    pAlignPEByBWA,
    pSortSam,
    pMarkDuplicates,
    pIndexBam,
    pRealignerTargetCreator,
    pIndelRealigner,
    pBaseRecalibrator,
    pPrintReads
)
# dependency adjustment
pIndelRealigner.depends   = [pIndexBam, pRealignerTargetCreator]
pPrintReads.depends       = [pIndelRealigner, pBaseRecalibrator]
# input adjustment
# args adjustment
pMarkDuplicates.args['params']             += ' TMP_DIR="%s"' % params.tmpdir
pAlignPEByBWA.args['reffile']                   = params.hg19fa
pRealignerTargetCreator.args['reffile']     = params.hg19fa
pRealignerTargetCreator.args['params'] += ' -Djava.io.tmpdir=%s' % params.tmpdir
pIndelRealigner.args['reffile']                     = params.hg19fa
pIndelRealigner.args['params']                += ' -Djava.io.tmpdir=%s' % params.tmpdir
pBaseRecalibrator.args['reffile']                = params.hg19fa
pBaseRecalibrator.args['knownSites']      = params.dbsnp
pBaseRecalibrator.args['params']           += ' -Djava.io.tmpdir=%s' % params.tmpdir
pPrintReads.args['reffile']                          = params.hg19fa
pPrintReads.args['params']                     += ' -Djava.io.tmpdir=%s' % params.tmpdir
```

Then every time you just need to call the aggregation:
```python
aFastqPE2Bam.input = channel.fromPairs ( datadir + '/*.fastq.gz' )
aFastqPE2Bam.exdir = exdir
pyppl({
    'proc': {
        'sgeRunner': {
            'sge_q' : '1-day'
        }
    }
}).starts(aFastqPE2Bam).run()
```

## Initialize an aggregation
Like previous example shows, you just need to give the constructor all the processes to construct an aggretation. However, there are several things need to be noticed:

1. The dependencies are automatically constructed by the order of the processes. 
   ```python
   a = aggr (p1, p2, p3)
   # The dependencies will be p1 -> p2 -> p3
   ```
2. The starting and ending processes are defined as the first and last processes, respectively. If you need to modify the dependencies, keep that in mind if the starting and ending processes are changed.
    ```python
    a = aggr (p1, p2, p3)
    # a.starts == [p1]
    # a.ends   == [p3]
    #                                / p2
    # change the dependencies to  p1     >
    #                                \ p3
    # both p2, p3 depend on p1, and p3 depends on p2
    p3.depends = [p1, p2]
    # but remember the ending processes are changed from [p3] to [p2, p3]
    a.ends = [p2, p3]
    ```
    You can also specify the dependencies manually:
    ```python
    a = aggr (p1, p2, p3, False)
    p2.depends = p1
    p3.depends = [p1, p2]
    a.starts = [p1]
    a.ends   = [p2, p3]
    ```

> **Hint** You can also access the processes using `a.p1`, `a.p2` and `a.p3`. If the tags of `p1`, `p2` and `p3` are not `notag`, you should access them by `p.p1_tag`, `p.p2_tag` and `p.p3_tag`
    
## Set properties of an aggregation
Basically, most of the properties available for a process are available for an aggregation, which just passes the values to the processes. However, some properties are just passed to starting processes, some just to ending processes, some to all of the processes, and some just affect the aggregation itself:

| Property name | Affected processes/aggregation |
|-|-|
| `input` | starting<sup>*</sup> |
| `depends`, `ex*` | ending |
| `starts`, `ends`, `id` | aggregation |
| `tag`, `tmpdir`, `forks`, `cache`, `retcodes`, `rc`, `echo`, `runner`, `errorhow`, `errhow`, `errorntry`, `errntry` | all processes |

> **Caution** <sup>*</sup>: As the input of processes already have the keys defined, when you specify the input to an aggregation, you just need to give the channel. And there could be multiple starting processes, the input channel you specify to the aggregation should be column-combined of the input channels when you specify them separately.
```python
p1.input = "v1"  # channel: [1,2,3]
p2.input = "v2"  # channel: [4,5,6]
a = aggr (p1, p2, p3, False)
p3.depends = [p1,p2]
a.starts = [p1,p2]
a.ends   = [p3]
a.input = [(1,4), (2,5), (3,6)]
```

## Set an aggregation as starting aggregation for a pipeline
You can do it just like setting a process as the starting process of pipeline (see [here][1]). Actually the starting processes in the aggregation (`agg.starts`) will be set as the starting processes of the pipeline.

## The dependency of aggregations and processes
An aggregation can depend on aggregations and/or processes, you just treat the aggregations as processes. A process can also depend on aggregations and/or processes. 

| What am I? | Whom I am depending on? | Real relations |
|-|-|-|
| `aggr` (`a1`) | `aggr` (`a2`) | `a1.starts` depends on `a2.ends` |
| `aggr` (`a`) | `proc` (`p`) | `a.starts` depends on `p` |
| `proc` (`p`) | `aggr` (`a`) | `p` depends on `a.ends` |


## Copy an aggregation
You may copy an aggregation, all the processes in the aggregation will be copied, and the dependencies will be switched to the corresponding copied processes, as well as the starting and ending processes.

You can keep the ids of processes unchanged but give a new tag and also give the aggregation an new id instead of the variable name:
```python
a = aggr(p1, p2, p3)
a2 = a.copy('copied')
# a2.procs == [
#    <proc with id "p1" and tag "copied">,
#    <proc with id "p2" and tag "copied">,
#    <proc with id "p3" and tag "copied">,
# ]
# a2.id == 'a2'
a2 = a.copy('copied', 'newAggr')
# a2.id == 'newAggr'
```
[1]: https://pwwang.gitbooks.io/pyppl/configure-a-pipeline.html#starting-processes