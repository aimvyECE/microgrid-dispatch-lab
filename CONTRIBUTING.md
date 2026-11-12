# Contributing

This is an early research prototype. Contributions should include a reproducible example and tests. Preserve the explicit distinction between synthetic examples and measured evidence.

- Keep units explicit at every interface.
- Add a conservation/bounds test when changing dispatch equations.
- Do not upload private meter records, client invoices, credentials or personal data.
- Cite dataset provenance and license before adding real measurements.
- Do not describe a new algorithm as validated until its limits have been tested.

Run `python -m unittest discover -s tests -v` and the example CLI before proposing a change.

## First contribution workflow

1. Fork the repository and create a descriptive branch.
2. Reproduce the default CLI and sensitivity sweep in a clean virtual environment.
3. For a bug, add a minimal failing test before changing the implementation.
4. Keep one concern per pull request; explain the units, assumptions, before/after
   behavior, test command and any backward-incompatible changes.
5. If outputs change, regenerate examples with the documented commands and explain
   why. Do not hand-edit numerical example results.

Good starting tasks: an input schema with explicit timestamp/timezone rules;
property tests on random nonnegative profiles; a rolling-horizon experiment.
These are suggestions, not claims of open assignments or community activity.

For a suspected credential leak, do not paste the secret into an issue. No secret
or private dataset is needed to reproduce the current synthetic examples.
