## Section 5 Resource vs Utility Result Analysis

* When doing the trace study, face2pool1pingpong1lego2's baseline is better than ours
  * baseline run all the applications, while ours replaces 2 faces with 1 lego.

* things to find out
  * are there any workers waiting? (Yes)
    * when multiple workers present, the effects of higher per worker throughput make client the bottleneck. 5 lego workers each processing ~20ms --> 150 FPS, while client only has 60 fps
  * Why does pool increase?
  * is our code working optimal when processing delay is a constant?

* If workers are waiting, how to improve
  * experiemnt over (res, # clients) grid
  * real-time estimation:
    * each worker records its FPS in the last second
    * determine # worker, # resource
    * a quick estimation: avg worker wait time, (avg worker process time --> avg utility)

### Real-time Scheduling

* Our goals should be match client throuphput (FPS) as much as possible while not violating latency constraints
* If all delays are met, increase the number of workers for service whose avg_cpu_time/util is the lowest.
* If there are latency > bound, decrease the number of workers whose avg_cpu_time/util is the largest.