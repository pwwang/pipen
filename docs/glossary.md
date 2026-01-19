# Glossary

This glossary defines key terms used throughout the pipen documentation.

## A

### Args

Short for **arguments**. The parameters that a function or method accepts. In docstrings, this section lists input parameters with their types and descriptions.

**Example:**
```python
def process_data(input_file: str, output_dir: str) -> None:
    """Process a data file.

    Args:
        input_file: Path to the input data file.
        output_dir: Directory where processed results will be saved.

    Returns:
        None
    """
```

---

## B

---

## C

### Cache

A mechanism that stores the results of completed jobs to avoid recomputing them when the same inputs are used again. pipen automatically computes a cache key (signature) based on input data, script content, and configuration.

**Related:** [Caching](caching.md)

---

## C (continued)

### Channel

A pandas DataFrame that structures data flow between processes. Each row in a channel represents an independent job, and each column represents a piece of data that the job needs.

**Types of channels:**
- **Input channel**: Data fed into a process
- **Output channel**: Data produced by a process

**Channel operations:** `create()`, `from_glob()`, `expand_dir()`, `collapse_files()`

**Related:** [Channels](channels.md)

---

## D

---

## E

---

## F

---

## G

---

## H

---

## I

---

## J

### Job

An individual execution of a process. When a process has input data with multiple rows, pipen creates multiple jobs (one for each row) that can run in parallel.

**Job lifecycle:**
1. **Initiated**: Job created
2. **Queued**: Waiting to run
3. **Submitted**: Submitted to scheduler
4. **Running**: Currently executing
5. **Succeeded**: Completed successfully
6. **Failed**: Completed with errors
7. **Cached**: Used cached results instead of running

**Related:** [Job Caching](caching.md)

---

## K

---

## L

---

## M

---

## N

---

## O

---

## P

### Pipeline

The main orchestrator that manages a workflow. A pipeline consists of multiple processes connected by dependencies. The `Pipen` class handles:
- Process discovery and dependency resolution
- Configuration management
- Progress tracking
- Plugin initialization

**Pipeline structure:**
```
Pipeline (orchestrator)
├── Process 1 (first step)
│   └── Jobs (parallel execution)
├── Process 2 (depends on Process 1)
│   └── Jobs
└── Process N (depends on previous steps)
    └── Jobs
```

**Related:** [Basics](basics.md), [Architecture](architecture.md)

---

### Process

A class that inherits from `Proc` and defines a single step in a pipeline. A process specifies:
- **Input**: What data it needs (`input` attribute)
- **Output**: What data it produces (`output` attribute)
- **Script**: How to transform input to output (`script` attribute)
- **Dependencies**: Which processes must complete first (`requires` attribute)

**Example:**
```python
class MyProcess(Proc):
    """Process data files."""
    input = "infile:file"
    output = "outfile:file:result.txt"
    script = "cat {{ in.infile }} > {{ out.outfile }}"
```

**Related:** [Defining a Process](defining-proc.md)

---

### Proc

Abbreviation for **Process**. The base class `Proc` is the foundation for defining pipeline steps.

---

### ProcGroup

A collection of related processes that can be managed together. ProcGroups allow you to organize processes logically and apply configurations to multiple processes at once.

**Related:** [Process Group](proc-group.md)

---

## Q

---

## R

### Raises

A section in docstrings that lists exceptions that a function or method can raise. This helps users understand what errors to expect and how to handle them.

**Example:**
```python
def process_data(data: str) -> dict:
    """Process data string.

    Args:
        data: The data string to process.

    Returns:
        Dictionary with processing results.

    Raises:
        ValueError: If data is empty.
        TypeError: If data is not a string.
    """
    if not data:
        raise ValueError("Data cannot be empty")
    if not isinstance(data, str):
        raise TypeError("Data must be a string")
    return {"processed": data}
```

---

### Returns

A section in docstrings that describes what a function or method returns. This includes the return type and description of the returned value.

**Example:**
```python
def calculate_sum(numbers: list[int]) -> int:
    """Calculate the sum of a list of numbers.

    Args:
        numbers: List of integers to sum.

    Returns:
        The sum of all numbers in the list.
    """
    return sum(numbers)
```

---

## S

### Scheduler

A backend that manages job execution. pipen supports multiple schedulers:
- **Local**: Execute jobs on the local machine
- **SGE**: Submit jobs to Sun Grid Engine
- **SLURM**: Submit jobs to SLURM workload manager
- **SSH**: Execute jobs on remote servers via SSH
- **Container**: Run jobs in containers
- **Gbatch**: Submit jobs to Google Cloud Batch

**Related:** [Scheduler](scheduler.md)

---

## T

---

## U

---

## V

---

## W

---

## X

---

## Y

---

## Z

---

## Related Documentation

- [Architecture](architecture.md) - Understanding how pipen components interact
- [Basics](basics.md) - Pipeline layers and folder structure
- [Defining a Process](defining-proc.md) - Creating process classes
- [Channels](channels.md) - Data flow between processes
- [Caching](caching.md) - How job caching works
- [Scheduler](scheduler.md) - Available scheduler backends

## Common Patterns

### Input/Output Types

| Type | Syntax | Description |
|-------|---------|-------------|
| `var` | `"name:var"` | In-memory variable |
| `file` | `"name:file"` | Single file path |
| `dir` | `"name:dir"` | Single directory path |
| `files` | `"name:files"` | Multiple file paths |
| `dirs` | `"name:dirs"` | Multiple directory paths |

### Error Strategies

| Strategy | Behavior |
|----------|-----------|
| `halt` | Stop entire pipeline on any failure |
| `ignore` | Continue pipeline, ignoring failed jobs |
| `retry` | Retry failed jobs up to `num_retries` times |

### Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `in.*` | Input variables | `{{ in.input_data }}` |
| `out.*` | Output placeholders | `{{ out.result_file }}` |
| `proc.*` | Process metadata | `{{ proc.name }}`, `{{ proc.workdir }}` |
 | `envs.*` | Template options (NOT shell env vars) | `{{ envs.my_option }}` |
| | Defined via `proc.envs` attribute. These are custom options passed to template rendering context. They are NOT shell environment variables like PATH or HOME. |
