/* -*- c++ -*-
 * Copyright (c) 2012-2016 by the GalSim developers team on GitHub
 * https://github.com/GalSim-developers
 *
 * This file is part of GalSim: The modular galaxy image simulation toolkit.
 * https://github.com/GalSim-developers/GalSim
 *
 * GalSim is free software: redistribution and use in source and binary forms,
 * with or without modification, are permitted provided that the following
 * conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions, and the disclaimer given in the accompanying LICENSE
 *    file.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions, and the disclaimer given in the documentation
 *    and/or other materials provided with the distribution.
 */

#ifndef GalSim_SBProfileImpl_H
#define GalSim_SBProfileImpl_H

#include "SBProfile.h"
#include "FFT.h"
#include "integ/Int.h"
#include "TMV.h"

namespace galsim {

    class SBProfile::SBProfileImpl
    {
    public:

        // Constructor
        SBProfileImpl(const GSParamsPtr& _gsparams);

        // Virtual destructor
        virtual ~SBProfileImpl() {}

        // Pure virtual functions:
        virtual double xValue(const Position<double>& p) const =0;
        virtual std::complex<double> kValue(const Position<double>& k) const =0;

        // Calculate xValues and kValues for a bunch of positions at once.
        // For some profiles, this may be more efficient than repeated calls of xValue(pos)
        // since it affords the opportunity for vectorization of the calculations.
        //
        // For the first two versions, the x,y values for val(ix,iy) are
        //     x = x0 + ix dx
        //     y = y0 + iy dy
        // The izero, jzero values are the indices where x=0, y=0.
        // For some profiles (e.g. axi-symmetric profiles), this affords further opportunities
        // for optimization.  If there is no such index, then izero, jzero = 0, which indicates
        // that all the values need to be used.
        //
        // For the latter two versions, the x,y values for val(ix,iy) are
        //     x = x0 + ix dx + iy dxy
        //     y = y0 + iy dy + ix dyx
        //
        // If these aren't overridden, then the regular xValue or kValue will be called for each
        // position.
        virtual void fillXValue(tmv::MatrixView<double> val,
                                double x0, double dx, int izero,
                                double y0, double dy, int jzero) const;
        virtual void fillXValue(tmv::MatrixView<double> val,
                                double x0, double dx, double dxy,
                                double y0, double dy, double dyx) const;
        virtual void fillKValue(tmv::MatrixView<std::complex<double> > val,
                                double kx0, double dkx, int izero,
                                double ky0, double dky, int jzero) const;
        virtual void fillKValue(tmv::MatrixView<std::complex<double> > val,
                                double kx0, double dkx, double dkxy,
                                double ky0, double dky, double dkyx) const;

        virtual double maxK() const =0;
        virtual double stepK() const =0;
        virtual bool isAxisymmetric() const =0;
        virtual bool hasHardEdges() const =0;
        virtual bool isAnalyticX() const =0;
        virtual bool isAnalyticK() const =0;
        virtual Position<double> centroid() const = 0;
        virtual double getFlux() const =0;
        virtual boost::shared_ptr<PhotonArray> shoot(int N, UniformDeviate ud) const=0;

        // Functions with default implementations:
        virtual void getXRange(double& xmin, double& xmax, std::vector<double>& /*splits*/) const
        { xmin = -integ::MOCK_INF; xmax = integ::MOCK_INF; }

        virtual void getYRange(double& ymin, double& ymax, std::vector<double>& /*splits*/) const
        { ymin = -integ::MOCK_INF; ymax = integ::MOCK_INF; }

        virtual void getYRangeX(
            double /*x*/, double& ymin, double& ymax, std::vector<double>& splits) const
        { getYRange(ymin,ymax,splits); }

        virtual double getPositiveFlux() const { return getFlux()>0. ? getFlux() : 0.; }

        virtual double getNegativeFlux() const { return getFlux()>0. ? 0. : -getFlux(); }

        // Utility for drawing into Image data structures.
        // returns flux integral
        template <typename T>
        double fillXImage(ImageView<T>& image, double gain) const;

        // Utility for drawing a k grid into FFT data structures
        void fillKGrid(KTable& kt) const;

        // Utility for drawing an x grid into FFT data structures
        void fillXGrid(XTable& xt) const;

        // Public so it can be directly used from SBProfile.
        const GSParamsPtr gsparams;

        virtual std::string serialize() const = 0;

        virtual std::string repr() const {return serialize(); }

    protected:

        // A helper function for cases where the profile has f(x,y) = f(|x|,|y|).
        // This includes axisymmetric profiles, but also a few other cases.
        // Only one quadrant has its values computed.  Then these values are copied to the other
        // 3 quadrants.  The input values izero, jzero are the index of x=0, y=0.
        // At least one of these needs to be != 0.
        void fillXValueQuadrant(tmv::MatrixView<double> val,
                                double x0, double dx, int nx1,
                                double y0, double dy, int ny1) const;
        void fillKValueQuadrant(tmv::MatrixView<std::complex<double> > val,
                                double kx0, double dkx, int nkx1,
                                double ky0, double dky, int nky1) const;

    private:
        // Copy constructor and op= are undefined.
        SBProfileImpl(const SBProfileImpl& rhs);
        void operator=(const SBProfileImpl& rhs);
    };

}

#endif
