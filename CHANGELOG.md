Changes from v1.5 to v1.6
=========================

API Changes
-----------

- Delayed AtmosphericScreen instantiation until its first use, the nature of
  which can change the value of the generated screens.  Use the .instantiate()
  method to manually override auto-instantiation. (#864)
- Reduced the number of types for the return value of various NFWHalo and
  PowerSpectrum methods.  Now they either return a single value if the input
  `pos` is a single Position or a numpy array if multiple positions were
  provided. (#855)
- Changed the return value of LookupTable, SED and Bandpass, when used as a
  function, to return only either a float or a numpy array. (#955)


Bug Fixes
---------

- Fixed error in amplitude of phase screens created by AtmosphericScreen (#864)
- Fixed a bug in the DES MEDS writer setting the cutout row/col wrong. (#928)
- Fixed a number of small bugs in the config processing uncovered by the
  galsim_extra FocalPlane output type. (#928)
- Fixed python3 unicode/str mismatches in tests/SConscript (#932)
- Fixed memory leak when drawing PhaseScreenPSFs using photon-shooting (#942)
- Fixed a few minor bugs in the Silicon code. (#963)
- Fixed a bug in SED.thin(), where it would always use the default rel_err,
  rather than the provided value. (#963)


Deprecated Features
-------------------

- Deprecated passing Image arguments to kappaKaiserSquires function. (#855)
- Deprecated the interpolant argument for PowerSpectrum methods getShear,
  getConvergence, getMagnification, and getLensing.  The interpolant should
  be set when calling buildGrid. (#855)
- Deprecated PowerSpectrum.subsampleGrid. (#855)


New Features
------------

- Added Zernike submodule. (#832, #951)
- Updated PhaseScreen wavefront and wavefront_gradient methods to accept `None`
  as a valid time argument, which means to use the internally stored time in
  the screen(s). (#864)
- Added SecondKick profile GSObject. (#864)
- Updated PhaseScreenPSFs to automatically include SecondKick objects when
  being drawn with geometric photon shooting. (#864)
- Added option to use circular weight function in HSM adaptive moments code.
  (#917)
- Added VonKarman profile GSObject. (#940)
- Added PhotonDCR surface op to apply DCR for photon shooting. (#955)
- Added astropy units as allowed values of wave_type in Bandpass. (#955)
- Added ability to get net pixel areas from the Silicon code for a given flux
  image. (#963)
- Added ability to transpose the meaning of (x,y) in the Silicon class. (#963)
