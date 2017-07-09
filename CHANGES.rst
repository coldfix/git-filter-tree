CHANGES
~~~~~~~

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
