
## Specification of the start processes

Once the requirements of the processes are specified, we are able to build the entire process dependency network. To start runing a pipeline, we just need to specify the start processes to start:

```python
class P1(Proc):
    ...

class P2(Proc):
    ...

class P3(Proc):
    requires = [P1, P2]
    ...

Pipen().run(P1, P2)
```

You can specify the start processes individually, like we did above, or send a list of processes:

```python
Pipen().run([P1, P2])
```

## Running with a different profile

`Pipen.run()` also accepts a keyword-argument `profile`, which allows you to use different profile from configuration files to run the pipeline:

```python
Pipen().run(P1, P2, profile="sge")
```

See [configurations][1] for more details.

[1]: ../configurations
