# ninja-robots

## Coding conventions

- Write Python code as reusable, importable functions/modules rather than one-off scripts, since it will be used to build Claude skills. Favor clear function signatures, avoid hardcoded/inline assumptions, and keep logic decoupled from any specific skill's I/O so it can be imported across multiple skills.
