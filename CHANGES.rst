CHANGES
~~~~~~~

2.1.0
=====
Date: 09.07.2017

- perform the commit rewrites in python. This leads to a tremendous
  performance improvement. In a test repo the cost for the second phase went
  down from more than 2 minutes to about 2 seconds.


2.0.0
=====
Date: 09.07.2017

- speedup for first phase: factor on the order 3
- major structural changes:
    - use asyncio based scheduler to avoid double job-execution
    - use pygit2 for tree-rewrite phase
- requirements:
    - depends on python≥3.6!
    - needs pygit2 installed


1.0.1
=====
Date: 09.07.2017

- fix bug that can result in incorrect file modes (due to incorrect caching)
- make the ETA display smoother (but also more inaccurate) by showing
  prediction based on total average rate
- improve API: add member functions for the git-specific operations
- add NOP module (useful for testing/demo)


1.0.0
=====
Date: 25.06.2017

- first stable version
- version that was used to migrate MAD-X_
- runs on python≥3.3
- no external dependencies (except for git)
- simple/clean API

.. _MAD-X: https://github.com/MethodicalAcceleratorDesign/MAD-X
