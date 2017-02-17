; Copyright (c) 2012-2016 by the GalSim developers team on GitHub
; https://github.com/GalSim-developers
;
; This file is part of GalSim: The modular galaxy image simulation toolkit.
; https://github.com/GalSim-developers/GalSim
;
; GalSim is free software: redistribution and use in source and binary forms,
; with or without modification, are permitted provided that the following
; conditions are met:
;
; 1. Redistributions of source code must retain the above copyright notice, this
;    list of conditions, and the disclaimer given in the accompanying LICENSE
;    file.
; 2. Redistributions in binary form must reproduce the above copyright notice,
;    this list of conditions, and the disclaimer given in the documentation
;    and/or other materials provided with the distribution.
;

PRO make_test_ims
; IDL script used to generate external test images for GalSim.
; Used by tests/test_Image.py, see Issue #144.
;

; Single images
test_array = [[11, 21, 31, 41, 51, 61, 71], $
              [12, 22, 32, 42, 52, 62, 72], $
              [13, 23, 33, 43, 53, 63, 73], $
              [14, 24, 34, 44, 54, 64, 74], $ 
              [15, 25, 35, 45, 55, 65, 75]]
writefits, 'testS.fits', test_array
writefits, 'testI.fits', long(test_array)
writefits, 'testF.fits', float(test_array)
writefits, 'testD.fits', double(test_array)

; Then do cubes with NIMAGES = 12 and multi-extension FITS images with
; each extension
; having ext_no added to it
nimages = 12
test_cube = intarr([size(test_array, /DIM), 12])
for k=0, nimages-1 do begin

   test_cube[*, *, k] = test_array + k
  
endfor

; First write these cubes out
writefits, 'test_cubeS.fits', test_cube
writefits, 'test_cubeI.fits', long(test_cube)
writefits, 'test_cubeF.fits', float(test_cube)
writefits, 'test_cubeD.fits', double(test_cube)

; Multi-ext: start with 16 bit ints
filename = 'test_multiS.fits'
spawn, "rm "+filename
mkhdr, header, test_array, /EXTEND
writefits, filename, test_array, header
for k=1, nimages-1 do begin

   writefits, filename, test_cube[*, *, k], /APPEND
  
endfor
; then proceed to other types
filename = 'test_multiI.fits'
spawn, "rm "+filename
mkhdr, header, long(test_array), /EXTEND
writefits, filename, long(test_array), header
for k=1, nimages-1 do begin

   writefits, filename, long(test_cube[*, *, k]), /APPEND
  
endfor
;
filename = 'test_multiF.fits'
spawn, "rm "+filename
mkhdr, header, float(test_array), /EXTEND
writefits, filename, float(test_array), header
for k=1, nimages-1 do begin

   writefits, filename, float(test_cube[*, *, k]), /APPEND
  
endfor
;
filename = 'test_multiD.fits'
spawn, "rm "+filename
mkhdr, header, double(test_array), /EXTEND
writefits, filename, double(test_array), header
for k=1, nimages-1 do begin

   writefits, filename, double(test_cube[*, *, k]), /APPEND
  
endfor
END

