########################################################
  dashex: Exchange monitoring dashboard configurations
########################################################


Description
===========

You have a staging infrastructure and a production infrastructure?  Wouldn't
you like to store your monitoring configurations in a single place?  Wouldn't
you like to use "infra as code" to get versionning, leave an audit trail,
back-up your configurations, etc.?

If you answered yes to any of those questions, this tool is for you!

In short, ``dashex`` is a command-line tool that allows you to:

1. save/export your monitoring configuration to disk in a normalized format;
2. load/import your monitoring configuration from disk to your monitoring
   infrastructure.

The storage on disk is a text-based format designed to be "easily" diffeable,
allowing you to review/audit changes.  You can store this in Git to submit
monitoring configuration changes as pull requests, have your peers review your
changes, deploy them as post-commit hooks, etc.


Contributing
============

This project uses permissive licensing.  Nobody is paid to support/maintain
this software.  You may request support in the issue tracker, but be prepared
to submit a pull request to fix bugs and/or submit improvements.
