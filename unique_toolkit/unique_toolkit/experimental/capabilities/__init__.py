"""Real capabilities built on top of :mod:`..resources`.

Everything here adds behavior the SDK does not provide: orchestration,
post-processing, evaluation, rule compilation, tokenization, etc. If a
module could be deleted without losing any functionality relative to raw
``unique_sdk`` usage, it belongs in :mod:`..resources`, not here.

Planned contents (current home → new home):

* ``agentic``                ← :mod:`unique_toolkit.agentic`
  (subpackages: ``tools``, ``loop_runner``, ``evaluation``,
  ``managers`` — collects the sibling ``*_manager`` packages —,
  ``feature_flags`` — single canonical home, collapses duplicates in
  :mod:`unique_toolkit.app.feature_flags` and
  :mod:`unique_toolkit._common.feature_flags`)
* ``data_extraction``        ← :mod:`unique_toolkit.data_extraction`
* ``smart_rules``            ← :mod:`unique_toolkit.smart_rules`
  + :mod:`unique_toolkit.content.smart_rules` (unified)
* ``chunk_relevancy_sorter`` ← :mod:`unique_toolkit._common.chunk_relevancy_sorter`
* ``config_checker``         ← :mod:`unique_toolkit._common.config_checker`
* ``docx_generator``         ← :mod:`unique_toolkit._common.docx_generator`
* ``tokenization``           ← :mod:`unique_toolkit._common.token`
* ``content_tree``           ← :mod:`unique_toolkit.experimental.content_tree`
  (derived tree/fuzzy-search view over the ``content`` resource; does not
  wrap an SDK endpoint of its own)
"""
