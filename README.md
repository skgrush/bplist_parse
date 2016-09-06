# bplist_parse
> A pure-python parser for Apple's binary plist files.

[![Python Version][pyver-image]]()
[![Project Status][status-image]]()
[![License][license-image]][license-url]

A python parser for Apple's binary property list format as defined in
Apple's CFBinaryPList.c source file.

I originally wrote this back in early 2014 so that I could read the output files
from an app called WiFiFoFum. The module that does this can be found in the
[`wfff_parse`](./wfff_parse) directory.

###Warning!
*This code should not be considered stable!* It's been quite a while since
I've looked at this code in depth, and it is not sufficiently tested.

[pyver-image]: https://img.shields.io/badge/python-v2.7-blue.svg
[status-image]: https://img.shields.io/badge/status-unstable-orange.svg
[license-image]: https://img.shields.io/github/license/skgrush/bplist_parse.svg
[license-url]: ./LICENSE.md
