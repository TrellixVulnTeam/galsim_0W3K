Changes from v1.3 to v1.4
=========================

API Changes
-----------

- Changed the galsim.Bandpass and galsim.SED classes so that formerly optional
  keywords to indicate units (`wave_type` for the former, `wave_type` and
 `flux_type` for the latter) are now required. (#745)
- Changed the default shift and/or offset for the output.psf field in a config
  file to not do any shift or offset.  It had been the default to match what
  was applied to the galaxy (cf. demo5).  However, we thought that was probably
  not the most intuitive default.  Now, matching the galaxy is still possible,
  but requires explicit specification of output.psf.shift = "galaxy" or
  output.psf.offset = "galaxy". (#691)


Dependency Changes
------------------

- Added future module as a dependency.  This is a trivial one to install, so
  it should not be any hardship.  You can use either `pip install future` or
  `easy_install future`. (#534)
- Changed PyYAML to a nominal dependency, even though it is still not
  technically required if you do not plan to use the `galsim` executable
  (or only plan to use JSON config files).  (#768)


Bug Fixes
---------

- Fixed bug in config that did not allow users to pass in a filename for
  COSMOS (correlated) noise.  (#732)
- Improved ability of galsim.fits.read to handle invalid but fixable FITS
  headers. (#602)
- Fixed bug in des module related to building meds file with wcs taken from
  the input images. (#654)
- Improved ability of ChromaticObjects to find fiducial achromatic profiles
  and wavelengths with non-zero flux. (#680)
- Fixed a bug in some of the WCS classes if the RA/Dec axes in the FITS header
  are reversed (which is allowed by the FITS standard). (#681)
- Fixed a bug in the way Images are instantiated for certain combinations of
  ChromaticObjects and image-setup keyword arguments (#683)
- Added ability to manipulate the width of the moment-measuring weight function
  for the KSB shear estimation method of the galsim.hsm package. (#686)
- Fixed bug in the (undocumented) function COSMOSCatalog._makeSingleGalaxy,
  where the resulting object did not set the index attribute properly. (#694)
- Fixed an error in the `CCDNoise.getVariance()` function, as well as some
  errors in the documentation about the units of CCDNoise parameters. (#713)
- Fixed a bug in drawKImage when non-default scale is given, but no images
  are provided. (#720)
- Fixed an assert failure in InterpolatedImage if the input image is
  identically equal to zero. (#720)
- Fixed a potential instability in drawing with deconvolution.  Now the fft of
  the deconvolved image will not be made larger than 1/kvalue_accuracy. (#720)
- Fixed a bug in how InterpolatedKImage checked for properly Hermitian input
  images. (#723)
- Updated ups table file so that setup command is `setup galsim` instead of
  `setup GalSim` (#724)
- Added new default algorithm for thinning SEDs and Bandpasses to enable faster
  calculations while still meeting relative error constraints. (#739).
- Fixed a bug in how DistDeviate handled probabilities that were nearly, but
  not quite, flat (#741)
- Fixed a bug in chromatic parametric galaxy models based on COSMOS galaxies.
  (#745)
- Fixed a bug in the Image copy constructor where the wcs was not copied if
  the `image` parameter is a galsim.Image. (#762)
- Fixed a bug in the Sum and Convolution constructors when they are only
  adding or convolving a single element that could lead to erroneous str and
  reprs for the resulting object if it was then transformed. (#763)
- Fixed a bug related to boost-v1.60 python shared_ptr registration. (#764)
- Made the error message when trying to read a non-existent *.fits.gz or
  *.fits.bz2 file more helpful. (#773)
- Changed an assert in the HSM module to an exception, since it can actually
  happen in rare (i.e. exceptional) circumstances. (#784)


Deprecated Features
-------------------

- Deprecated the gal.type=Ring option in the config files.  The preferred way
  to get a ring test is now with the new stamp.type=Ring.  See demo5 and demo10
  for examples of the new syntax. (#698)


New Features
------------

- Added OutputCatalog class, which can be used to keep track of and then output
  truth information.  cf. demos 9 and 10. (#301, #691)
- Added methods calculateHLR, calculateMomentRadius, and calculateFWHM to both
  GSObject and Image. (#308)
- Added LookupTable2D to facilitate quick interpolation of two-dimensional
  tabular data. (#465)
- Added support for Python 3.  Specifically, we tested with Python 3.4 and 3.5,
  but we expect that it should work for Python versions >= 3.3. (#534)
- Added AtmosphericScreen, OpticalScreen, and PhaseScreenList used
  to generate PSFs via Fourier optics. (#549)
- Added PhaseScreenPSF to transform PhaseScreens into GSObjects.  (#549)
- Added Atmosphere function to conveniently assemble a multi-layer atmosphere
  PhaseScreenList. (#549)
- Rewrote OpticalPSF to operate under the PhaseScreen framework to enable
  fully self-consistent optics+atmospheric PSFs. (#549)
- OpticalPSF now able to handle Zernike polynomial aberrations up to arbitrary
  order. (#549)
- Added a simple, linear model for persistence in the detectors that accepts a
  list of galsim.Image instances and a list of an equal number of floats. (#554)
- Added BoundsI.numpyShape() to easily get the numpy shape that corresponds
  to a given bounds instance. (#654)
- Have FITS files with unsigned integer data automatically convert that into
  the corresponding signed integer data type for use in GalSim, rather than
  converting to float64, which it had been doing. (#654)
- Made COSMOSCatalog write an index parameter for both parameteric and real
  galaxy types to indicate the index of the object in the full COSMOS catalog.
  (#654, #694)
- Added ability to specify lambda and r0 separately for Kolmogorov to have
  GalSim do the conversion from radians to the given scale unit. (#657)
- Made it possible to initialize an InterpolatedImage from a user-specified
  HDU in a FITS file with multiple extensions. (#660)
- Changed `galsim.fits.writeMulti` to allow any of the "image"s to be
  already-built hdus, which are included as is. (#691)
- Added optional `wcs` argument to `Image.resize()`. (#691)
- Added `BaseDeviate.discard(n)` and `BaseDeviate.raw()`. (#691)
- Added `sersic_prec` option to COSMOSCatalog.makeGalaxy(). (#691)
- Made it possible to impose some cuts on galaxy image quality in the
  COSMOSCatalog class. (#693)
- Added `convergence_threshold` as a parameter of HSMParams. (#709)
- Improved the readability of Image and BaseDeviate reprs. (#723)
- Sped up some Bandpass and SED functionality (and LookupTable class in
  general). (#735)
- Added the FourierSqrt operator to compute the Fourier-space square root of a
  profile.  This is useful in implementing optimal coaddition algorithms; see
  make_coadd.py in the examples directory (#748).
- Made Bandpass.thin() and Bandpass.truncate() preserve the zeropoint by
  default. (#711)
- Added version information to the compiled C++ library. (#750)


Updates to galsim executable
----------------------------

- Dropped default verbosity from 2 to 1, since for real simulations, 2 is
  usually too much output. (#691)
- Added ability to easily split the total work into several jobs with
  galsim -n njobs -j jobnum. (#691)
- Added galsim -p to perform profiling on the run. (#691)


New config features
-------------------

- Added ability to write truth catalogs using output.truth field. (#301, #691)
- Improved the extensibility of the config parsing.  It is now easier to write
  custom image types, object types, value types, etc. and register them with
  the config parser.  The code with the new type definitions should be given
  as a module for the code to import using the new 'modules' top-level
  config field. (#691, #774)
- Added the 'template' option to read another config file and use either the
  whole file as a template or just a given field from the file. (#691)
- Made '$' and '@' shorthand for 'Eval' and 'Current' types respectively in
  string values.  e.g. '$(@image.pixel_scale) * 2' would be parsed to mean
  2 times the current value of image.pixel_scale.  (#691)
- Allowed gsobjects to be referenced from Current types. (#691)
- Added x,f specification for a RandomDistribution. (#691)
- Added a new 'stamp' top level field and moved some of the items that had
  belonged in 'image' over to 'stamp'.  Notably, 'draw_method', 'offset', and
  'gsparams', among other less commonly used parameters.  However, for
  backwards compatibility, they are all still allowed in the image field
  as well. (#691)
- Added more example scripts to showcase how to use some of the new config
  features to make fairly sophisticated simulations.  cf. examples/great3 and
  examples/des. (#654, #691)
- Added new stamp type=Ring to effect ring tests.  This replaces the old
  gsobject type=Ring, which is now deprecated.  See demo5 and demo10 for
  examples of the new preferred syntax. (#698)


File name changes
-----------------

- Changed the names of the real galaxy catalog examples from *catalog_example*
  to *catalog_23.5_example* (#740)


Changes from v1.4.0 to v1.4.1
=============================

Bug fix
-------

- Fixed an installation error when using both DYLD_LIBRARY_PATH and
  DYLD_FALLBACK_LIBRARY_PATH.

Changes from v1.4.1 to v1.4.2
=============================

Bug fix
-------

- Fixed bug when whitening noise in images based on COSMOS training datasets using
  the config functionality, and other minor config bug. (#792)

Changes from v1.4.2 to v1.4.3
=============================

Bug fix
-------

- Fixed bug in the photon shooting code that could occasionally lead to an assert
  failure due to rounding errors if the numbers came out just right. (#866)

Changes from v1.4.3 to v1.4.4
=============================

Bug fix
-------

- Fixed bug in the photon shooting code where poisson_flux=True could result in
  a negative number of photons to be shot, which in turn could (depending on
  the profile) lead to an assert failure.  (#881)
