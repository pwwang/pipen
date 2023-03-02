A process group is a collection of processes that are related to each other. It is a convenient way to manage a set of processes.

With `pipen`, not only a process can be reused, but also a group of processes can be reused. We just need to define the relationship between the processes in the group, and then we can reuse the group in other pipelines, or even run it directly as a pipeline.

## Define a process group

To define a process group, we need to define a class that inherits from `pipen.procgroup.ProcGroup`. The class name will be the name of the group, unless we specify a `name` attribute.

```python
from pipen.procgroup import ProcGroup

class MyGroup(ProcGroup):
    ...
```

Note that the subclasses of `ProcGroup` are singleton classes. If you need to define multiple groups, you can define a base class and then inherit from it.

## Add processes to a group

There are two ways to add processes to a group, using `pg.add_proc` or `ProcGroup.add_proc`, where `pg` is a process group instance. The first method is used after the group is instantiated and it decorates a process class directly. The second method is used before the group is instantiated and it decorates a property of `ProcGroup` that returns a process.

1. Using the `pg.add_proc()` decorator.

    ```python
    from pipen import Proc, ProcGroup

    class MyGroup(ProcGroup):
        ...

    pg = MyGroup()

    @pg.add_proc
    class MyProc(Proc):
        ...
    ```

2. Using the `ProcGroup.add_proc()` decorator to decorate a property of the group class.

    ```python
    from pipen import Proc, ProcGroup

    class MyGroup(ProcGroup):

        @ProcGroup.add_proc
        def my_proc(self):
            class MyProc(Proc):
                ...
            return MyProc
    ```

This method adds a process at runtime, so it is useful when we want to add processes to a group dynamically.

## Access processes in a group

We can access the processes in a group using the `pg.<proc>` attribute, where `pg` is a process group instance. Note that when we use the `ProcGroup.add_proc` method to add processes, the process name is the name of the property.

However, you can always use `pg.procs.<proc_name>` to access the process, where the `<proc_name>` is the real name of the process.

```python
from pipen import Proc, ProcGroup

class MyGroup(ProcGroup):

    @ProcGroup.add_proc
    def my_proc(self):
        class MyProc(Proc):
            ...
        return MyProc

pg = MyGroup()
assert pg.my_proc.name == 'MyProc'
assert pg.procs.MyProc.name == 'MyProc'
```

We can use `pg.starts` to get the start processes of the group, which are the processes that have no required processes. So when you add processes to a group, remember to specify `.requires` for each process, unless they are start processes.

## Run a process group as a pipeline

To run a process group as a pipeline, we can convert it to a pipeline using the `as_pipen()` method. The method takes the same arguments as the `Pipen` constructor.

```python
from pipen import Proc, ProcGroup

class MyGroup(ProcGroup):
    ...

pg = MyGroup()

@pg.add_proc
class MyProc(Proc):
    ...

pg.as_pipen().set_data(...).run()
```

## Integrate a process group into a pipeline

```python
from pipen import Proc, ProcGroup

class MyGroup(ProcGroup):

    @ProcGroup.add_proc
    def my_proc(self):
        class MyProc(Proc):
            ...
        return MyProc

    @ProcGroup.add_proc
    def my_proc2(self):
        class MyProc2(Proc):
            requires = self.my_proc
            ...

        return MyProc2

pg = MyGroup()

class PrepareData(Proc):
    ...

class PostGroup(Proc):
    requires = pg.my_proc2

pg.my_proc.requires = PrepareData

pipen = Pipen().set_starts(PrepareData).set_data(...).run()
```
