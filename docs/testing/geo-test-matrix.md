# Geo Test Matrix

| Case | Input | Expected |
| --- | --- | --- |
| Fixed coordinate | Center with zero radius | Center returned unchanged |
| Radius sampling | Center with radius | Sample inside the radius, verified by distance |
| Uniform distribution | Many samples | Mean distance close to two thirds of the radius, maximum within radius |
| Deterministic seed | Same seed twice | Identical coordinate |
| Distinct seeds | Two seeds | Different coordinates |
| Invalid coordinate | Latitude above ninety | Structured coordinate error |
| Invalid radius | Negative radius | Structured radius error |
| Missing pair | Latitude without longitude | Validation problem reported |
| Permission denial | Permission model | Default is prompt, override recorded |
| Virtual mode | Manual mode profile | Source reported as virtual, seed recorded |
| Virtual without fallback | Failed provider in manual mode | Forbidden fallback error, no physical resolution |
| Automatic mode | Signals without a location hint | Country level proposal with capped confidence |
| Automatic without signals | Empty signals | Structured provider unavailable error |
| Hybrid mode | Automatic base plus manual overrides | Every override reported in the signal list |
| Disabled mode | Disabled profile | Structured refusal |
| State machine | Any mode resolution | Deterministic transition history |
| Antimeridian | Sampling across the boundary | Longitude normalized, bounding box flagged |

All cases are executed by `tests/unit/test_geo_models.py`, `tests/unit/test_geodesy.py`, `tests/unit/test_randomization.py`, `tests/unit/test_state_machine.py` and `tests/unit/test_environment_core.py`.
