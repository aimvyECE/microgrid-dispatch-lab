# Contributing

This is an early research prototype. Contributions should include a reproducible example and tests. Preserve the explicit distinction between synthetic examples and measured evidence.

- Keep units explicit at every interface.
- Add a conservation/bounds test when changing dispatch equations.
- Do not upload private meter records, client invoices, credentials or personal data.
- Cite dataset provenance and license before adding real measurements.
- Do not describe a new algorithm as validated until its limits have been tested.

Run `python -m unittest discover -s tests -v` and the example CLI before proposing a change.
