igor-ci installation guide
==========================

This guide details how build igor-ci against the development
versions of libgit2 and pygit2.  It assumes that ``python`` is
``python3.3``.  Installing in a Python virtual environment is
recommended.


libgit2
-------

Build and install libgit2.

::

  % git clone git://github.com/libgit2/libgit2.git
  % cd libgit2
  % export LIBGIT2=$(pwd)
  % git checkout <see DEPENDENCIES for revision>
  % mkdir lib
  % cd lib
  % cmake ..
  % cmake --build .
  % cd ../..


pygit2
------

Note that the ``LIBGIT2`` environment variable exported above is
required.

::

  % git clone git://github.com/libgit2/pygit2.git
  % cd pygit2
  % git checkout <see DEPENDENCIES for revision>
  % python setup.py install
  % cd ..


igor-ci
-------

Install igor-ci::

  % git clone git://github.com/frasertweedale/igor-ci.git
  % cd igor-ci
  % python setup.py install


Run igor-ci::

  % export LD_LIBRARY_PATH=$LIBGIT2/lib:$LD_LIBRARY_PATH
  % python -m igor.server &
  % python -m igor.worker --host localhost &


To monitor the behaviour of the system by subscribing to all server
events, open a netcat session ``nc localhost 1602`` and follow the
example transcript::

  [bacardi:~] fraser% nc -v localhost 1602
  Connection to localhost 1602 port [tcp/*] succeeded!

::

  >>> {"command": "subscribe", "params": {"events": []}}
  <<< {"params": {}, "event": "Subscribe"}
  ... time elapses; more events happen
  <<< {"params": {}, "event": "OrderWaiting"}
