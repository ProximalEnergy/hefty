# Style Guide

Bruno organizes api calls into collections.  We separate out `get` requests so that we can run only gets during smoke testing.  Running `post`, `patch`, `put` may change the state of our database which is undesired.
