igor-ci - the ghastly CI system
===============================

igor-ci is a `continuous integration`_ system that stores build
instructions and build results in `Git`_.  It adheres to the `Unix
philosophy`_, consisting of a collection of small programs that work
together, possibly communicating over a network.

.. _continuous integration: http://en.wikipedia.org/wiki/Continuous_Integration
.. _Git: http://git-scm.com/
.. _Unix philosophy: http://en.wikipedia.org/wiki/Unix_philosophy


What are its features?
----------------------

Current features include:

* store build instructions in Git, with history
* store build results in Git, (easy to see full build history,
  differences between build environment, transcripts, etc.)
* build reports link to the previous build report, the build
  instructions that were executed, and optionally the source commit
  that was built
* parallel builds to leverage multi-core/CPU

Current triggers include:

* manual build trigger

Currently supported source VCSes:

* Git

Planned features:

* Gerrit trigger
* security
* notifier processes
* web dashboard or UI

Other ideas:

* support more VCSes (on an as-needs basis; patches welcome)
* artifacts
* test reports
* ``.travis.yml`` support


Dependencies
------------

* Git >= v1.8.1.3
* Python 3.3
* libgit2 ~ v0.19
* pygit2 ~ v0.19


License
-------

::

  igor-ci is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.


Contributing
------------

Bug reports, general feedback, patches and translations are welcome.

To submit a patch, please use ``git send-email`` or generate a
pull/merge request.  Write a `well formed commit message`_.  If your
patch is nontrivial, add a copyright notice (or, if appropriate,
update an existing notice) at the top of each added or changed file.

.. _well formed commit message: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
