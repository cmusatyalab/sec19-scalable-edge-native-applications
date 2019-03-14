# Related Topics

## Distributed Stream Processing

Stream processing involves continuous processing, aggregation, and analysis of
unbounded data. Distributed stream processing involves distributing workloads on
multiple machines. Distributed stream processing can be implemented by hand with
queues and processing nodes, self-organized and managed. However, as the pattern
becoming more prevalent, frameworks that ease the development of such design
pattern have been created. Examples include Aurora, Apache Storm, Flink, Samza, and
Spark stream. The frameworks helps with creating queues, allocating jobs,
fault-tolerance aspects of implementing such a pipeline.

Aspects that certain design choices can be made:

- Data mobility: how data is moved around. Blocking operations increase the latency.
- Programming abstraction: sql for query vs custom defined functions
- Fault-tolerance: exact once, at least once, at most once? deterministic when
  faults occur?
  - at least once semantics via record acknowledgement (Storm)
  - micro-batch fault tolerance (Spark Streaming)
  - transactional updates (google cloud dataflow)
  - distributed snapshots (flink)
- Data partitioning
- Handling special Stream data characteristics: out of order? might be delayed?
- Elasticity: when and how would scale-up/scale-out occur?

A typical distributed stream processing application has a logical plan,
specifying how the data should be partitioned and flow through the processing
DAG. Then the scheduler comes up with a physical plan in which different PE are
allocated with resources and are assigned to nodes.

### Fault-tolerance

- Precise Recovery
  - no effect of a failure visible except some increase in latency.
- Rollback Recovery
  - side effects occurs besides latency while the information flowing through
    the system is not lost, e.g. at least once processing.
  - can be achieved through
    - active standby: two processing engines (PE) run independently, with the
      backup PE storing outputs until downstream PE ACK the receptions of the
      output.
    - passive standby: primary PE periodically checkpoints its state. Backup PE
      restart from the latest checkpoint when doing the recovery.
    - upstream backup: upstream stores their outputs until the downstream ACK them.
- Gap recovery (amnesia)
  - information will be lost.
  - new tasks starts from an empty state

### Comparison

![comparison-dsps](https://i.imgur.com/KnsWwI7.png)

## Scheduling in Real-time Systems

## Scheduling in Stream Processing Systems
