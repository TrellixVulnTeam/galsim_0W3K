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

//#define DEBUGLOGGING

#include "SBKolmogorov.h"
#include "SBKolmogorovImpl.h"

#ifdef DEBUGLOGGING
#include <fstream>
//std::ostream* dbgout = new std::ofstream("debug.out");
//int verbose_level = 2;
#endif

// Uncomment this to do the calculation that solves for the conversion between lam_over_r0
// and fwhm and hlr.
// (Solved values are put into Kolmogorov class in galsim/base.py = 0.975865, 0.554811)
//#define SOLVE_FWHM_HLR

#ifdef SOLVE_FWHM_HLR
#include "Solve.h"
#endif

namespace galsim {

    SBKolmogorov::SBKolmogorov(double lam_over_r0, double flux,
                               const GSParamsPtr& gsparams) :
        SBProfile(new SBKolmogorovImpl(lam_over_r0, flux, gsparams)) {}

    SBKolmogorov::SBKolmogorov(const SBKolmogorov& rhs) : SBProfile(rhs) {}

    SBKolmogorov::~SBKolmogorov() {}

    double SBKolmogorov::getLamOverR0() const
    {
        assert(dynamic_cast<const SBKolmogorovImpl*>(_pimpl.get()));
        return static_cast<const SBKolmogorovImpl&>(*_pimpl).getLamOverR0();
    }

    std::string SBKolmogorov::SBKolmogorovImpl::serialize() const
    {
        std::ostringstream oss(" ");
        oss.precision(std::numeric_limits<double>::digits10 + 4);
        oss << "galsim._galsim.SBKolmogorov("<<getLamOverR0()<<", "<<getFlux();
        oss << ", galsim.GSParams("<<*gsparams<<"))";
        return oss.str();
    }

    LRUCache<GSParamsPtr, KolmogorovInfo> SBKolmogorov::SBKolmogorovImpl::cache(
        sbp::max_kolmogorov_cache);

    // The "magic" number 2.992934 below comes from the standard form of the Kolmogorov spectrum
    // from Racine, 1996 PASP, 108, 699 (who in turn is quoting Fried, 1966, JOSA, 56, 1372):
    // T(k) = exp(-1/2 D(k))
    // D(k) = 6.8839 (lambda/r0 k/2Pi)^(5/3)
    //
    // We convert this into T(k) = exp(-(k/k0)^5/3) for efficiency,
    // which implies 1/2 6.8839 (lambda/r0 / 2Pi)^5/3 = (1/k0)^5/3
    // k0 * lambda/r0 = 2Pi * (6.8839 / 2)^-3/5 = 2.992934
    //
    SBKolmogorov::SBKolmogorovImpl::SBKolmogorovImpl(
        double lam_over_r0, double flux, const GSParamsPtr& gsparams) :
        SBProfileImpl(gsparams),
        _lam_over_r0(lam_over_r0),
        _k0(2.992934 / lam_over_r0),
        _k0sq(_k0*_k0),
        _inv_k0(1./_k0),
        _inv_k0sq(1./_k0sq),
        _flux(flux),
        _xnorm(_flux * _k0sq),
        _info(cache.get(this->gsparams.duplicate()))
    {
        dbg<<"SBKolmogorov:\n";
        dbg<<"lam_over_r0 = "<<_lam_over_r0<<std::endl;
        dbg<<"k0 = "<<_k0<<std::endl;
        dbg<<"flux = "<<_flux<<std::endl;
        dbg<<"xnorm = "<<_xnorm<<std::endl;
    }

    double SBKolmogorov::SBKolmogorovImpl::xValue(const Position<double>& p) const
    {
        double r = sqrt(p.x*p.x+p.y*p.y) * _k0;
        return _xnorm * _info->xValue(r);
    }

    double KolmogorovInfo::xValue(double r) const
    { return r < _radial.argMax() ? _radial(r) : 0.; }

    std::complex<double> SBKolmogorov::SBKolmogorovImpl::kValue(const Position<double>& k) const
    {
        double ksq = (k.x*k.x+k.y*k.y) * _inv_k0sq;
        return _flux * _info->kValue(ksq);
    }

    void SBKolmogorov::SBKolmogorovImpl::fillXValue(tmv::MatrixView<double> val,
                                                    double x0, double dx, int izero,
                                                    double y0, double dy, int jzero) const
    {
        dbg<<"SBKolmogorov fillXValue\n";
        dbg<<"x = "<<x0<<" + i * "<<dx<<", izero = "<<izero<<std::endl;
        dbg<<"y = "<<y0<<" + j * "<<dy<<", jzero = "<<jzero<<std::endl;
        if (izero != 0 || jzero != 0) {
            xdbg<<"Use Quadrant\n";
            fillXValueQuadrant(val,x0,dx,izero,y0,dy,jzero);
        } else {
            xdbg<<"Non-Quadrant\n";
            assert(val.stepi() == 1);
            const int m = val.colsize();
            const int n = val.rowsize();
            typedef tmv::VIt<double,1,tmv::NonConj> It;

            x0 *= _k0;
            dx *= _k0;
            y0 *= _k0;
            dy *= _k0;

            for (int j=0;j<n;++j,y0+=dy) {
                double x = x0;
                double ysq = y0*y0;
                It valit = val.col(j).begin();
                for (int i=0;i<m;++i,x+=dx) {
                    double r = sqrt(x*x + ysq);
                    *valit++ = _xnorm * _info->xValue(r);
                }
            }
        }
    }

    void SBKolmogorov::SBKolmogorovImpl::fillKValue(tmv::MatrixView<std::complex<double> > val,
                                                    double kx0, double dkx, int izero,
                                                    double ky0, double dky, int jzero) const
    {
        dbg<<"SBKolmogorov fillKValue\n";
        dbg<<"kx = "<<kx0<<" + i * "<<dkx<<", izero = "<<izero<<std::endl;
        dbg<<"ky = "<<ky0<<" + j * "<<dky<<", jzero = "<<jzero<<std::endl;
        if (izero != 0 || jzero != 0) {
            xdbg<<"Use Quadrant\n";
            fillKValueQuadrant(val,kx0,dkx,izero,ky0,dky,jzero);
        } else {
            xdbg<<"Non-Quadrant\n";
            assert(val.stepi() == 1);
            const int m = val.colsize();
            const int n = val.rowsize();
            typedef tmv::VIt<std::complex<double>,1,tmv::NonConj> It;

            kx0 *= _inv_k0;
            dkx *= _inv_k0;
            ky0 *= _inv_k0;
            dky *= _inv_k0;

            for (int j=0;j<n;++j,ky0+=dky) {
                double kx = kx0;
                double kysq = ky0*ky0;
                It valit = val.col(j).begin();
                for (int i=0;i<m;++i,kx+=dkx) *valit++ = _flux * _info->kValue(kx*kx + kysq);
            }
        }
    }

    void SBKolmogorov::SBKolmogorovImpl::fillXValue(tmv::MatrixView<double> val,
                                                    double x0, double dx, double dxy,
                                                    double y0, double dy, double dyx) const
    {
        dbg<<"SBKolmogorov fillXValue\n";
        dbg<<"x = "<<x0<<" + i * "<<dx<<" + j * "<<dxy<<std::endl;
        dbg<<"y = "<<y0<<" + i * "<<dyx<<" + j * "<<dy<<std::endl;
        assert(val.stepi() == 1);
        assert(val.canLinearize());
        const int m = val.colsize();
        const int n = val.rowsize();
        typedef tmv::VIt<double,1,tmv::NonConj> It;

        x0 *= _k0;
        dx *= _k0;
        dxy *= _k0;
        y0 *= _k0;
        dy *= _k0;
        dyx *= _k0;

        It valit = val.linearView().begin();
        for (int j=0;j<n;++j,x0+=dxy,y0+=dy) {
            double x = x0;
            double y = y0;
            for (int i=0;i<m;++i,x+=dx,y+=dyx) {
                double r = sqrt(x*x + y*y);
                *valit++ = _xnorm * _info->xValue(r);
            }
        }
    }

    void SBKolmogorov::SBKolmogorovImpl::fillKValue(tmv::MatrixView<std::complex<double> > val,
                                                    double kx0, double dkx, double dkxy,
                                                    double ky0, double dky, double dkyx) const
    {
        dbg<<"SBKolmogorov fillKValue\n";
        dbg<<"kx = "<<kx0<<" + i * "<<dkx<<" + j * "<<dkxy<<std::endl;
        dbg<<"ky = "<<ky0<<" + i * "<<dkyx<<" + j * "<<dky<<std::endl;
        assert(val.stepi() == 1);
        assert(val.canLinearize());
        const int m = val.colsize();
        const int n = val.rowsize();
        typedef tmv::VIt<std::complex<double>,1,tmv::NonConj> It;

        kx0 *= _inv_k0;
        dkx *= _inv_k0;
        dkxy *= _inv_k0;
        ky0 *= _inv_k0;
        dky *= _inv_k0;
        dkyx *= _inv_k0;

        It valit = val.linearView().begin();
        for (int j=0;j<n;++j,kx0+=dkxy,ky0+=dky) {
            double kx = kx0;
            double ky = ky0;
            for (int i=0;i<m;++i,kx+=dkx,ky+=dkyx) *valit++ = _flux * _info->kValue(kx*kx+ky*ky);
        }
    }

    // Set maxK to where kValue drops to maxk_threshold
    double SBKolmogorov::SBKolmogorovImpl::maxK() const
    { return _info->maxK() * _k0; }

    // The amount of flux missed in a circle of radius pi/stepk should be at
    // most folding_threshold of the flux.
    double SBKolmogorov::SBKolmogorovImpl::stepK() const
    { return _info->stepK() * _k0; }

    // f(k) = exp(-(k/k0)^5/3)
    // The input value should already be (k/k0)^2
    double KolmogorovInfo::kValue(double ksq) const
    { return exp(-std::pow(ksq,5./6.)); }

    // Integrand class for the Hankel transform of Kolmogorov
    class KolmIntegrand : public std::unary_function<double,double>
    {
    public:
        KolmIntegrand(double r) : _r(r) {}
        double operator()(double k) const
        { return k*std::exp(-std::pow(k, 5./3.))*j0(k*_r); }

    private:
        double _r;
    };

    // Perform the integral
    class KolmXValue : public std::unary_function<double,double>
    {
    public:
        KolmXValue(const GSParamsPtr& gsparams) : _gsparams(gsparams) {}

        double operator()(double r) const
        {
            const double integ_maxK = integ::MOCK_INF;
            KolmIntegrand I(r);
            return integ::int1d(I, 0., integ_maxK,
                                _gsparams->integration_relerr,
                                _gsparams->integration_abserr);
        }
    private:
        const GSParamsPtr& _gsparams;
    };

#ifdef SOLVE_FWHM_HLR
    // XValue - target  (used for solving for fwhm)
    class KolmTargetValue : public std::unary_function<double,double>
    {
    public:
        KolmTargetValue(double target, const GSParamsPtr& gsparams) :
            f(gsparams), _target(target) {}
        double operator()(double r) const { return f(r) - _target; }
    private:
        KolmXValue f;
        double _target;
    };

    class KolmXValueTimes2piR : public std::unary_function<double,double>
    {
    public:
        KolmXValueTimes2piR(const GSParamsPtr& gsparams) : f(gsparams) {}

        double operator()(double r) const
        { return f(r) * r; }
    private:
        KolmXValue f;
    };

    class KolmEnclosedFlux : public std::unary_function<double,double>
    {
    public:
        KolmEnclosedFlux(const GSParamsPtr& gsparams) :
            f(gsparams), _gsparams(gsparams) {}
        double operator()(double r) const
        {
            return integ::int1d(f, 0., r,
                                _gsparams->integration_relerr,
                                _gsparams->integration_abserr);
        }
    private:
        KolmXValueTimes2piR f;
        const GSParamsPtr& _gsparams;
    };

    class KolmTargetFlux : public std::unary_function<double,double>
    {
    public:
        KolmTargetFlux(double target, const GSParamsPtr& gsparams) :
            f(gsparams), _target(target) {}
        double operator()(double r) const { return f(r) - _target; }
    private:
        KolmEnclosedFlux f;
        double _target;
    };
#endif

    // Constructor to initialize Kolmogorov constants and xvalue lookup table
    KolmogorovInfo::KolmogorovInfo(const GSParamsPtr& gsparams) :
        _radial(TableDD::spline)
    {
        dbg<<"Initializing KolmogorovInfo\n";

        // Calculate maxK:
        // exp(-k^5/3) = kvalue_accuracy
        _maxk = std::pow(-std::log(gsparams->kvalue_accuracy),3./5.);
        dbg<<"maxK = "<<_maxk<<std::endl;

        // Build the table for the radial function.

        // Start with f(0), which is analytic:
        // According to Wolfram Alpha:
        // Integrate[k*exp(-k^5/3),{k,0,infinity}] = 3/5 Gamma(6/5)
        //    = 0.55090124543985636638457099311149824;
        double val = 0.55090124543985636638457099311149824 / (2.*M_PI);
        _radial.addEntry(0.,val);
        xdbg<<"f(0) = "<<val<<std::endl;

        // We use a cubic spline for the interpolation, which has an error of O(h^4) max(f'''').
        // I have no idea what range the fourth derivative can take for the f(r),
        // so let's take the completely arbitrary value of 10.  (This value was found to be
        // conservative for Sersic, but I haven't investigated here.)
        // 10 h^4 <= xvalue_accuracy
        // h = (xvalue_accuracy/10)^0.25
        double dr = gsparams->table_spacing * sqrt(sqrt(gsparams->xvalue_accuracy / 10.));

        // Along the way accumulate the flux integral to determine the radius
        // that encloses (1-folding_threshold) of the flux.
        double sum = 0.;
        double thresh0 = 0.5 / (2.*M_PI*dr);
        double thresh1 = (1.-gsparams->folding_threshold) / (2.*M_PI*dr);
        double thresh2 = (1.-gsparams->folding_threshold/5.) / (2.*M_PI*dr);
        double R = 0., hlr = 0.;
        // Continue until accumulate 0.999 of the flux
        KolmXValue xval_func(gsparams);

        for (double r = dr; sum < thresh2; r += dr) {
            val = xval_func(r) / (2.*M_PI);
            xdbg<<"f("<<r<<") = "<<val<<std::endl;
            _radial.addEntry(r,val);

            // Accumulate int(r*f(r)) / dr  (i.e. don't include 2*pi*dr factor as part of sum)
            sum += r * val;
            xdbg<<"sum = "<<sum<<"  thresh1 = "<<thresh1<<"  thesh2 = "<<thresh2<<std::endl;
            xdbg<<"sum*2*pi*dr "<<sum*2.*M_PI*dr<<std::endl;
            if (R == 0. && sum > thresh1) R = r;
            if (hlr == 0. && sum > thresh0) hlr = r;
        }
        dbg<<"Done loop to build radial function.\n";
        dbg<<"R = "<<R<<std::endl;
        dbg<<"hlr = "<<hlr<<std::endl;
        // Make sure it is at least 5 hlr
        R = std::max(R,gsparams->stepk_minimum_hlr*hlr);
        _stepk = M_PI / R;
        dbg<<"stepk = "<<_stepk<<std::endl;
        dbg<<"sum*2*pi*dr = "<<sum*2.*M_PI*dr<<"   (should ~= 0.999)\n";

        // Next, set up the sampler for photon shooting
        std::vector<double> range(2,0.);
        range[1] = _radial.argMax();
        _sampler.reset(new OneDimensionalDeviate(_radial, range, true, gsparams));

#ifdef SOLVE_FWHM_HLR
        // Improve upon the conversion between lam_over_r0 and fwhm:
        KolmTargetValue fwhm_func(0.55090124543985636638457099311149824 / 2., gsparams);
        double r1 = 1.4;
        double r2 = 1.5;
        Solve<KolmTargetValue> fwhm_solver(fwhm_func,r1,r2);
        fwhm_solver.setMethod(Brent);
        double rd = fwhm_solver.root();
        xdbg<<"Root is "<<rd<<std::endl;
        // This is in units of 1/k0.  k0 = 2.992934 / lam_over_r0
        // It's also the half-width hal-max, so * 2 to get fwhm.
        xdbg<<"fwhm = "<<rd * 2. / 2.992934<<" * lam_over_r0\n";

        // Confirm that flux function gets unit flux when integrated to infinity:
        KolmEnclosedFlux enc_flux;
        for(double rmax = 0.; rmax < 20.; rmax += 1.) {
            dbg<<"Flux enclosed by r="<<rmax<<" = "<<enc_flux(rmax)<<std::endl;
        }

        // Next find the conversion between lam_over_r0 and hlr:
        KolmTargetFlux hlr_func(0.5);
        r1 = 1.6;
        r2 = 1.7;
        Solve<KolmTargetFlux> hlr_solver(hlr_func,r1,r2);
        hlr_solver.setMethod(Brent);
        rd = hlr_solver.root();
        xdbg<<"Root is "<<rd<<std::endl;
        dbg<<"Flux enclosed by r="<<rd<<" = "<<enc_flux(rd)<<std::endl;
        // This is in units of 1/k0.  k0 = 2.992934 / lam_over_r0
        xdbg<<"hlr = "<<rd / 2.992934<<" * lam_over_r0\n";
#endif
    }

    boost::shared_ptr<PhotonArray> KolmogorovInfo::shoot(int N, UniformDeviate ud) const
    {
        dbg<<"KolmogorovInfo shoot: N = "<<N<<std::endl;
        dbg<<"Target flux = 1.0\n";
        assert(_sampler.get());
        boost::shared_ptr<PhotonArray> result = _sampler->shoot(N,ud);
        //result->scaleFlux(_norm);
        dbg<<"KolmogorovInfo Realized flux = "<<result->getTotalFlux()<<std::endl;
        return result;
    }

    boost::shared_ptr<PhotonArray> SBKolmogorov::SBKolmogorovImpl::shoot(
        int N, UniformDeviate ud) const
    {
        dbg<<"Kolmogorov shoot: N = "<<N<<std::endl;
        dbg<<"Target flux = "<<getFlux()<<std::endl;
        // Get photons from the KolmogorovInfo structure, rescale flux and size for this instance
        boost::shared_ptr<PhotonArray> result = _info->shoot(N,ud);
        result->scaleFlux(_flux);
        result->scaleXY(1./_k0);
        dbg<<"Kolmogorov Realized flux = "<<result->getTotalFlux()<<std::endl;
        return result;
    }
}
