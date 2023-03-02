A process group is a collection of processes that are related to each other. It is a convenient way to manage a set of processes.

With `pipen`, not only a process can be reused, but also a group of processes can be reused. We just need to define the relationship between the processes in the group, and then we can reuse the group in other pipelines, or even run it directly as a pipeline.

## Define a process group

To define a process group, we need to define a class that inherits from `pipen.procgroup.ProcGroup`. The class name will be the name of the group, unless we specify a `name` attribute. The class should have a `build` method that defines the relationship between the processes in the group. It should return a list of processes, that are the start processes of the group.

```python
from pipen.procgroup import ProcGroup

class MyGroup(ProcGroup):
    def build(self):
        ...
```

Note that the subclasses of `ProcGroup` are singleton classes. If you need to define multiple groups, you can define a base class and then inherit from it.

## Add processes to a group

There are two ways to add processes to a group.

1. Use the `pg.add_proc()` decorator, where `pg` is the process group instance.

    ```python
    from pipen import Proc, ProcGroup

    class MyGroup(ProcGroup):
        def build(self):
            return [self.MyProc]

    pg = MyGroup()

    @pg.add_proc
    class MyProc(Proc):
        ...
    ```

2. Use the `ProcGroup.define_proc()` decorator to decorate a property of the group class.

    ```python
    from pipen import Proc, ProcGroup

    class MyGroup(ProcGroup):

        def build(self):
            return [self.my_proc]

        @ProcGroup.define_proc
        def my_proc(self):
            class MyProc(Proc):
                ...
            return MyProc
    ```

The second method make sure that the subclasses of `MyGroup` have different instances of `MyProc`. This is useful when we want to define a group that can be reused in different pipelines.

## Run a process group as a pipeline

To run a process group as a pipeline, we can convert it to a pipeline using the `as_pipen()` method. The method takes the same arguments as the `Pipen` constructor.

```python
from pipen import Proc, ProcGroup

class MyGroup(ProcGroup):
    def build(self):
        return [self.MyProc]

pg = MyGroup()

@pg.add_proc
class MyProc(Proc):
    ...

# build is called automatically
pg.as_pipen().set_data(...).run()
```

## Integrate a process group into a pipeline

```python
from pipen import Proc, ProcGroup

class MyGroup(ProcGroup):
    def build(self):
        self.my_proc2.requires = self.my_proc
        return self.my_proc

    @ProcGroup.define_proc
    def my_proc(self):
        class MyProc(Proc):
            ...
        return MyProc

    @ProcGroup.define_proc
    def my_proc2(self):
        class MyProc2(Proc):
            ...
        return MyProc2

pg = MyGroup()

class PrepareData(Proc):
    ...

class PostGroup(Proc):
    requires = pg.my_proc2

# has to call build() manually to build the relationship
pg.build().requires = PrepareData
# PostGroup.requires = pg.my_proc2

pipen = Pipen().set_starts(PrepareData).set_data(...).run()
```
