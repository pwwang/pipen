# Aggregations
<!-- toc -->

Imagine that you have a set of processes predefined, and every time when you deal with similar problems (i.e. format a file and plot the data or some next generation sequencing data analysis), you will consistently use those processes, then you have to configure and call them every time. 

Aggregations are designed for this kind of situations, you can just define an aggregations with those processes, and adjust the dependencies, input and arguments, you will be able to re-use the aggregation with very less configuration.

For example:
```python
pTrimmomaticPE.input             = <input channel>
pAlignPEByBWA.depends            = pTrimmomaticPE
pSortSam.depends                 = pAlignPEByBWA
pMarkDuplicates.depends          = pSortSam
pIndexBam.depends                = pMarkDuplicates
pRealignerTargetCreator.depends  = pIndexBam
pIndelRealigner.depends          = pIndexBam, pRealignerTargetCreator
pBaseRecalibrator.depends        = pIndelRealigner
pPrintReads.depends              = pIndelRealigner, pBaseRecalibrator
pPrintReads.exportdir            = exdir

pMarkDuplicates.args.params         += ' TMP_DIR="/local2/tmp/"'
pAlignPEByBWA.args.reffile           = reffile
pRealignerTargetCreator.args.reffile = reffile
pRealignerTargetCreator.args.params += ' -Djava.io.tmpdir=/local2/tmp/'
pIndelRealigner.args.reffile         = reffile
pIndelRealigner.args.params         += ' -Djava.io.tmpdir=/local2/tmp/'
pBaseRecalibrator.args.reffile       = reffile
pBaseRecalibrator.args.knownSites    = dbsnp
pBaseRecalibrator.args.params       += ' -Djava.io.tmpdir=/local2/tmp/'
pPrintReads.args.reffile             = reffile
pPrintReads.args.params             += ' -Djava.io.tmpdir=/local2/tmp/'

PyPPL({
    'proc': {
        'forks': 100,
        'runner': 'sge',
        'sgeRunner': {
            'sge.q': 'lg-mem'
        }
    }
}).start(pTrimmomaticPE).run()
```
This is a very commonly used Whole Genome Sequencing data cleanup pipeline from the raw reads according to the [GATK best practice](https://software.broadinstitute.org/gatk/best-practices/). And it will be used pretty much every time when the raw read files come. 

With an aggregation defined, you don't need to configure and call those processes every time:
```python
from pyppl import Aggr
# some paramters defined in params
aFastqPE2Bam = Aggr (
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
aFastqPE2Bam.pIndelRealigner.depends   = aFastqPE2Bam.pIndexBam, aFastqPE2Bam.pRealignerTargetCreator
aFastqPE2Bam.pPrintReads.depends       = aFastqPE2Bam.pIndelRealigner, aFastqPE2Bam.pBaseRecalibrator
# input adjustment
# args adjustment
aFastqPE2Bam.pMarkDuplicates.args.params             += ' TMP_DIR="%s"' % params.tmpdir
aFastqPE2Bam.pAlignPEByBWA.args.reffile               = params.hg19fa
aFastqPE2Bam.pRealignerTargetCreator.args.reffile     = params.hg19fa
aFastqPE2Bam.pRealignerTargetCreator.args.params     += ' -Djava.io.tmpdir=%s' % params.tmpdir
aFastqPE2Bam.pIndelRealigner.args.reffile             = params.hg19fa
aFastqPE2Bam.pIndelRealigner.args.params             += ' -Djava.io.tmpdir=%s' % params.tmpdir
aFastqPE2Bam.pBaseRecalibrator.args.reffile           = params.hg19fa
aFastqPE2Bam.pBaseRecalibrator.args.knownSites        = params.dbsnp
aFastqPE2Bam.pBaseRecalibrator.args.params           += ' -Djava.io.tmpdir=%s' % params.tmpdir
aFastqPE2Bam.pPrintReads.args.reffile                 = params.hg19fa
aFastqPE2Bam.pPrintReads.args.params                 += ' -Djava.io.tmpdir=%s' % params.tmpdir
```

Then every time you just need to call the aggregation:
```python
aFastqPE2Bam.input = channel.fromPairs ( datadir + '/*.fastq.gz' )
aFastqPE2Bam.exdir = exdir
PyPPL({
    'proc': {
        'sgeRunner': {
            'sge.q' : '1-day'
        }
    }
}).start(aFastqPE2Bam).run()
```

## Initialize an aggregation
Like previous example shows, you just need to give the constructor all the processes to construct an aggretation. However, there are several things need to be noticed:

1. The dependencies are automatically constructed by the order of the processes. 
   ```python
   a = Aggr (p1, p2, p3)
   # The dependencies will be p1 -> p2 -> p3
   ```
2. The starting and ending processes are defined as the first and last processes, respectively. If you need to modify the dependencies, keep that in mind whether the starting and ending processes are changed.
    ```python
    a = Aggr (p1, p2, p3)
    # a.starts == [p1]
    # a.ends   == [p3]
    #                                / p2
    # change the dependencies to  p1      >
    #                                \ p3
    # both p2, p3 depend on p1, and p3 depends on p2
    a.p3.depends = p1, p2
    # but remember the ending processes are changed from [p3] to [p2, p3]
    a.ends = [p2, p3]
    ```
    You can also specify the dependencies manually:
    ```python
    a = Aggr (p1, p2, p3, False)
    a.p2.depends = p1
    a.p3.depends = p1, p2
    a.starts = [p1]
    a.ends   = [p2, p3]
    ```
3. If you have one process used twice in the aggregation, copy it with a different id:
   ```python
   a = Aggr(
       p1,
       p2,
       p1.copy(newid = 'p1copy')
   )
   # then to access the 2nd p1: a.p1copy
   ```
4. Each process is copied by aggregation, so the original one can still be used.
5. The tag of each process is regenerated by the id of the aggregation.

## Add a process on the run
`aggr.addProc(p, where=None)`
You can add a process, and also define whether to put it in `starts`, `ends`, `both` or `None`.
    
## Set attributes of processes of an aggregation
You can set the attributes directly for a process of an aggregation:
```python
aFastqPE2Bam.pAlignPEByBWA.args.reffile = params.hg19fa
```
Or you may use `set` method of an aggregation:
```python
aFastqPE2Bam.set('args.reffile', params.hg19fa, 'pAlignPEByBWA')
```
The benefit of the latter method is that you can set the attributes of multiple processes at one time:
```python
aFastqPE2Bam.set('args.reffile', params.hg19fa, 'pAlignPEByBWA, pBaseRecalibrator')
# Both args.reffile of aFastqPE2Bam.pAlignPEByBWA and aFastqPE2Bam.pBaseRecalibrator 
# were set as params.hg19fa
```
You can also do:
```python
aFastqPE2Bam.set('forks', 10)
```
to set `forks` of all processes as `10`.

## Set an aggregation as starting aggregation for a pipeline
You can do it just like setting a process as the starting process of pipeline (see [here][1]). Actually the starting processes in the aggregation (`aggr.starts`) will be set as the starting processes of the pipeline.

## The dependency of aggregations and processes
An aggregation can depend on aggregations and/or processes, you just treat the aggregations as processes. A process can also depend on aggregations and/or processes. 

| What am I? | Whom I am depending on? | Real relations |
|-|-|-|
| `Aggr` (`a1`) | `Aggr` (`a2`) | `a1.starts` depends on `a2.ends` |
| `Aggr` (`a`) | `Proc` (`p`) | `a.starts` depends on `p` |
| `Proc` (`p`) | `Aggr` (`a`) | `p` depends on `a.ends` |

## Copy an aggregation
`Aggr.copy(tag = 'notag', copyDeps = True, newid = None)`
You may copy an aggregation, all the processes in the aggregation will be copied, and the dependencies will be switched to the corresponding copied processes, as well as the starting and ending processes, if `copyDeps == True`. 

You can keep the ids of processes unchanged but give a new tag and also give the aggregation an new id instead of the variable name:
```python
a = Aggr(p1, p2, p3)
# access the processes:
# a.p1, a.p2, a.p3
a2 = a.copy('copied')
# a2.procs == [
# <proc with id "p1" and tag "copied">,
# <proc with id "p2" and tag "copied">,
# <proc with id "p3" and tag "copied">,
# ]
# a2.id == 'a2'
# to access the processes:
# a2.p1, a2.p2, a2.p3
a2 = a.copy('copied', newid = 'newAggr')
# a2.id == 'newAggr'
```
[1]: https://pwwang.gitbooks.io/pyppl/configure-a-pipeline.html#starting-processes