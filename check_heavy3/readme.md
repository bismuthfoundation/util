# How to check heavy3 file consistency

## Full check

sha256 of the full file should be `ffe30d8a63e1731e613b16ff8fd040d2946dba6a09823d7cc09d837570c55199`  
See full_check.py for az python impl.

Takes from 10 to 30 sec.

## Minimal check, file size

Not a full check, but tells if the creation process was interrupted (major cause of fails)

File size is 1073741824 bytes

See size_check.py

## Sampling tests

TODO
