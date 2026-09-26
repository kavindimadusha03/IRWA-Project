# IRWA fresh test kit

Extract this ZIP **directly into your existing IRWA project root**. This creates the `irwa_retest/` folder alongside your existing `app/` and `data/` folders. It does not overwrite your updated application, original tests or working SQLite database.

Then read `irwa_retest/README.md` before moving the old `audit/` folder outside the project. Start with `py irwa_retest/self_check.py` and `python irwa_retest/run_all.py --list`.

This kit contains adapted IR-01–IR-15 evidence collectors, focused new quick regression tests, and a suite launcher. It does NOT contain or reuse the pre-update audit outcomes.
