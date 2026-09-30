# Locale Resources

This directory holds locale data and negotiation policy resources for the LA Brow localization subsystem.

Implementation lives in `locale_engine/`. The directory name `locale` is reserved for resources so that Python source modules are never placed in a directory name that collides with the standard library module of the same name.

Contents to be added as the localization subsystem grows:

- language registry data
- region and locale mapping data
- localization policy documents
- external localization test corpora that never appear in product user interface
