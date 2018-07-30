# Aggregations

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

pMarkDuplicates.args.params.tmpdir   = "/local2/tmp/"
pAlignPEByBWA.args.reffile           = reffile
pRealignerTargetCreator.args.reffile = reffile
pRealignerTargetCreator.args.params.tmpdir='/local2/tmp/'
pIndelRealigner.args.reffile         = reffile
pIndelRealigner.args.params.tmpdir   = '/local2/tmp/'
pBaseRecalibrator.args.reffile       = reffile
pBaseRecalibrator.args.knownSites    = dbsnp
pBaseRecalibrator.args.params.tmpdir ='/local2/tmp/'
pPrintReads.args.reffile             = reffile
pPrintReads.args.params              = '/local2/tmp/'

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
from bioprocs import params
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
aFastqPE2Bam.pMarkDuplicates.args.params.tmpdir       = params.tmpdir
aFastqPE2Bam.pAlignPEByBWA.args.reffile               = params.hg19fa
aFastqPE2Bam.pRealignerTargetCreator.args.reffile     = params.hg19fa
aFastqPE2Bam.pRealignerTargetCreator.args.params.tmpdir= params.tmpdir
aFastqPE2Bam.pIndelRealigner.args.reffile             = params.hg19fa
aFastqPE2Bam.pIndelRealigner.args.params.tmpdir       = params.tmpdir
aFastqPE2Bam.pBaseRecalibrator.args.reffile           = params.hg19fa
aFastqPE2Bam.pBaseRecalibrator.args.knownSites        = params.dbsnp
aFastqPE2Bam.pBaseRecalibrator.args.params.tmpdir     = params.tmpdir
aFastqPE2Bam.pPrintReads.args.reffile                 = params.hg19fa
aFastqPE2Bam.pPrintReads.args.params.tmpdir           = params.tmpdir
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
    a = Aggr (p1, p2, p3, depends = False)
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
       p1.copy(id = 'p1copy')
   )
   # then to access the 2nd p1: a.p1copy
   ```
4. Each process is copied by aggregation, so the original one can still be used.
5. The tag of each process is regenerated by the id of the aggregation.

## Add a process on the run
`aggr.addProc(p, where=None)`
You can add a process, and also define whether to put it in `starts`, `ends`, `both` or `None`.
    
## Delegate attributes of processes to an aggregation
You can Delegate the attributes directly for a process to an aggregation:
```python
aFastqPE2Bam.delegate('args.reffile', 'pAlignPEByBWA')
```
Then when you want to set `args.reffile` for `pAlignPEByBWA`, you can just do:
```python
aFastqPE2Bam.args.reffile = '/path/to/hg19.fa'
```
You may use `starts/ends` represents the start/end processes.  

Delegate an attribute to multiple processes:
```python
aFastqPE2Bam.delegate('args.reffile', 'pAlignPEByBWA, pPrintReads')
# or
aFastqPE2Bam.delegate('args.reffile', ['pAlignPEByBWA', 'pPrintReads'])
# or
aFastqPE2Bam.delegate('args.reffile', [aFastqPE2Bam.pAlignPEByBWA, aFastqPE2Bam.pPrintReads])
```

Delegate multiple attributes at one time:
```python
aFastqPE2Bam.delegate('args.reffile, args.tmpdir', 'pAlignPEByBWA, pPrintReads')
# or
aFastqPE2Bam.delegate(['args.reffile', 'args.tmpdir'], 'pAlignPEByBWA, pPrintReads')
```

!!! caution

    Undelegated attributes will be delegated to all processes. But remember if an attribute has been set before, say `p.runner = 'local'` then, `aggr.runner` will not overwrite it if `runner` is not delegated. If it is, then it'll be overwritten.

!!! note

    For attributes that have sub-attributes (i.e. `p.args.params.inopts.cnames`), you may just delegate the first parts, then the full assignment of the attribute will still follow the delegation. For example:  
    ```python
    aggr.delegate('args.params', 'p1,p2')
    aggr.args.params.inopts.cnames = True # only affects p1, p2
    ```
    Keep in mind that shorter delegations always come first. In the above case, if we have another delegation: `aggr.delegate('args.params.inopts', 'p3')`, then the assignment will still affect `p1, p2` (the first delegation) and `p3` (the second delegation).

## Default delegations
By default, `input/depends` are delegated for start processes, and `exdir/exhow/exow/expart` for end processes. Importantly, as `aggr.starts` is a list, the values for `input/depends` must be a list as well, with elements corresponing to each start process. 
Besides, we have two special attributes for aggregations: `input2` and `depends2`. Unlike `input` and `depends`, `input2` and `depends2` try to pass everything it gets to each process, instead of passing corresponind element to each process. For example:
```python
# aggr.starts = [aggr.p1, aggr.p2]
aggr.input = [['a'], ['b']]
# then:
# aggr.p1.config['input'] == ['a']
# aggr.p2.config['input'] == ['b']

aggr.input2 = [['a'], ['b']]
# then:
# aggr.p1.config['input'] == [['a'], ['b']]
# aggr.p2.config['input'] == [['a'], ['b']]
```

## Set attribute value for specific processes of an aggregation
There are several ways to do that:
```python
# refer to the process directly
aFastqPE2Bam.pPrintReads.args.tmpdir = '/tmp'
aFastqPE2Bam.pPrintReads.runner = 'local'
# refer to the index of the process
aFastqPE2Bam[8].args.tmpdir = '/tmp'
aFastqPE2Bam[8].runner = 'local'
# refer to the name of the process
aFastqPE2Bam['pPrintReads'].args.tmpdir = '/tmp'
aFastqPE2Bam['pPrintReads'].runner = 'local'

# for multiple processes
aFastqPE2Bam[:3].args.tmpdir = '/tmp'
aFastqPE2Bam[0,1,3].args.tmpdir = '/tmp'
aFastqPE2Bam['aFastqPE2Bam', 'pPrintReads'].args.tmpdir = '/tmp'
aFastqPE2Bam['aFastqPE2Bam, pPrintReads'].args.tmpdir = '/tmp'

# or you may use starts/ends to refer to the start/end processes
# has to be done after aggr.starts/aggr.ends assigned 
# or initialized with depends = True
aFastqPE2Bam['starts'].args.tmpdir = '/tmp'
aFastqPE2Bam['ends'].args.tmpdir = '/tmp'
```

!!! hint

    If an attribute is delegated for other processes, you can still set the value of it by the above methods.

!!! note

    When use `__getitem__` to select processes from aggregations, only the index or the id will return the processes itself (instance of `Proc`), otherwise it will return an instance `_Proxy`, which is proxy used to pass attribute values to a set of processes.  
    So pay attention to it, because we can do `aggr['pXXX1, pXXX2'].depends = "pXXX3, pXXX4"` to `aggr.pXXX3` and `aggr.pXXX4` as the dependent of `aggr.pXXX1` and `aggr.pXXX2` respectively, but if you do `aggr['pXXX1'] = 'pXXX3'` will raise an error. Because `_Proxy` helps the aggregation to select the processes from itselt, but a `Proc` instance doesn't know how to.

## Define modules of an aggregation.
We can define some modules for an aggregation, later on we can switch them on or off.  
To define a module, you can simply do:
```python
aggr.module('name', starts = 'pStart', ends = 'pEnd', depends = {'pEnd': 'pStart'})
```
Later on, when we switch this module on: `aggr.on('name')`, then `aggr.pStart` will be added to `aggr.starts`, `aggr.pEnds` will be added to `aggr.ends`, and `aggr.pEnd` will be set to depend on `aggr.pStart`. When we switch it off, then `aggr.pStart` will be removed from `aggr.starts`, `aggr.pEnds` will be removed from `aggr.ends`, and `aggr.pStart` will be removed from `aggr.pStart`'s dependents.  
If you want to keep some processes from being removed when the module is switched off, as they are used by other modules, you may do: 
```python
aggr.module(
    'name', 
    starts      = 'pStart',
    ends        = 'pEnd',
    depends     = {'pEnd': 'pStart'},
    ends_shared = {'pEnd': 'othermod'}
)
```
Then when the module is switched off, `aggr.pEnd` will be kept.

If you have something else to be done when a module is switched on/off, you may use `moduleFunc` to define them:
```python
def name_on(a):
    a.addStart(a.pStart)
    a.pEnd.depends = a.pStart
    a.addEnd(a.pEnd)
    # more stuff go here
def name_off(a):
    a.delStart(a.pStart)
    a.pEnd.depends = []
    a.delEnd(a.pEnd)
    # more stuff go here
aggr.moduleFunc('name', on, off)
```

!!! hint

    You may use `aggr.on()` to switch all modules on and `aggr.off()` to switch all modules off.

## Set an aggregation as start aggregation for a pipeline
You can do it just like setting a process as the starting process of pipeline (see [here][1]). Actually the starting processes in the aggregation (`aggr.starts`) will be set as the starting processes of the pipeline.

## The dependency of aggregations and processes
An aggregation can depend on aggregations and/or processes, you just treat the aggregations as processes. A process can also depend on aggregations and/or processes. 

| What am I? | Whom I am depending on? | Real relations |
|-|-|-|
| `Aggr` (`a1`) | `Aggr` (`a2`) | `a1.starts` depends on `a2.ends` |
| `Proc` (`p`) | `Aggr` (`a`) | `p` depends on `a.ends` |

!!! note
    You have to specify `depends` for start processes of an aggregation.

## Copy an aggregation
`Aggr.copy(tag = 'notag', depends = True, id = None, delegates = True, modules = True)`
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
a2 = a.copy('copied', id = 'newAggr')
# a2.id == 'newAggr'
```
[1]: ./configure-a-pipeline/#starting-processes