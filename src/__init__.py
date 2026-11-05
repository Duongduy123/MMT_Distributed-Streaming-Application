"""Root package for CN Assignment 1 (Distributed Streaming-based Client-Server Collaboration).

Sub-packages:
    common     -- constants, configuration, lifecycle, shared raw-socket HTTP layer, protocol contracts
    transport  -- shared custom UDP transport (reliability, flow control, CUBIC, pacer, scheduler)
    server     -- server process (Machine A) components
    client     -- client process (Machine B/C/...) components

Importing any module in this package must not create sockets or start threads.
"""
