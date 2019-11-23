---
layout: index
---

[« Back to the index](index)

<hr>

# Code Review Guidelines

Using our purely [pull-request-based workflow](development_workflow),
code can be developed very flexibly by internal and external
contributors. At the same time this workflow allows us to enforce
stricter rules on code that ends up in the public repository.

Following are rough guidelines for the code reviewers. These are not
meant to prevent progress, but to keep up the code quality as the
number of developers is growing. All of this is not set in stone and
can be discussed on the [NEST mailing
lists](http://www.nest-simulator.org/community/).

* In general, the rule is that each pull request needs an OK from the CI
  platform and at least two reviewers to be merged.
* For changes that are “not code” or “trivial” (e.g. changes in documentation,
  fixes for typos, etc.), the release manager can waive the need for a second
  reviewer and just accept the OK from Travis and a single positive review in
  order to merge the request.
* Each pull request should to be documented by an issue in the [issue
  tracker](https://github.com/nest/nest-simulator/issues) explaining the reason
  for the changes and the solution. The issue is also the place for discussions
  about the code. The description of the pull request must include
  `Fixes #´*issue_number* in the commit message (see [keywords understood by
  GitHub](https://help.github.com/en/github/managing-your-work-on-github/closing-issues-using-keywords)
* All discussions and suggestions must be resolved in order to not miss points
  of discussion that came up during the review.
* The title of the pull request has to meet the criteria defined in *Comit
  messages and Pull Request titles* (FIXME). 
* New features like SLI or PyNEST functions, neuron or synapse models need to
  be accompanied by one or more tests written either in SLI or Python. New
  features for the NEST kernel need a test written in SLI.
* Each change to the code has to be reflected also in the corresponding
  examples and documentation.
* All source code has to be adhering to the Coding Guidelines for
  [C++](coding_guidelines_c++), [Python PEP8](https://www.python.org/dev/peps/pep-0008/)
  and [SLI](coding_guidelines_sli) in order to pass the [continuous integration
  system checks](continuous_integration).
* All Commits should be coherent and contain only changes that belong together.
* Pull requests should contain the smallest set of necessary changes for the
  particular modification. Try to prevent "Then we can also fix this here...",
  which will lead to pull request bloat and make it difficult to tell when
  things are "done".
