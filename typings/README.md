# Skyfield typing support

These partial stubs describe the Skyfield API used by this project. They supplement the installed library for Pyright and its language server; they contain no runtime implementation.

Skyfield uses dynamic unit descriptors and attaches propagation errors to position objects at runtime. Pyright otherwise infers descriptor objects instead of numerical values and cannot see the error messages. The stubs also distinguish a scalar time/angle from an array of samples, so scalar UTC values are typed as `datetime` and sampled values as NumPy arrays.

The signatures follow the installed Skyfield 1.55 implementation. Keep this subset aligned when changing the Skyfield dependency or using additional library APIs. Runtime behavior remains provided by Skyfield.
