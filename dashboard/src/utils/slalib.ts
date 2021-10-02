/* SLA LIB */
let SIN = Math.sin;
let COS = Math.cos;
let SQRT = Math.sqrt;
let ATAN2 = Math.atan2;
let ASIN = Math.asin;
let ABS = Math.abs;


export function sla_eqeqx(DATE) {
    /*
    *     - - - - - -
    *      E Q E Q X
    *     - - - - - -
    *
    *  Equation of the equinoxes  (IAU 1994, double precision)
    *
    *  Given:
    *     DATE    dp      TDB (loosely ET) as Modified Julian Date
    *                                          (JD-2400000.5)
    *
    *  The result is the equation of the equinoxes (double precision)
    *  in radians:
    *
    *     Greenwich apparent ST = GMST + sla_EQEQX
    *
    *  References:  IAU Resolution C7, Recommendation 3 (1994)
    *               Capitaine, N. & Gontier, A.-M., Astron. Astrophys.,
    *               275, 645-650 (1993)
    *
    *  Called:  sla_NUTC
    *
    *  Patrick Wallace   Starlink   23 August 1996
    *
    *  Copyright (C) 1996 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    //  Turns to arc seconds and arc seconds to radians
    let T2AS=1296000,
    AS2R=0.484813681109535994e-5;

    let T,OM,DPSI,EPS0;

    //  Interval between basic epoch J2000.0 and current epoch (JC)
    T=(DATE-51544.5)/36525.0;

    //  Longitude of the mean ascending node of the lunar orbit on the
    //   ecliptic, measured from the mean equinox of date
    OM=AS2R*(450160.280+(-5.0*T2AS-482890.539+(7.455+0.008*T)*T)*T);

    //  Nutation
    let result = sla_nutc(DATE);
    DPSI = result[0];
    // DEPS = result[1];
    EPS0 = result[2];

    //  Equation of the equinoxes
    return DPSI*COS(EPS0)+AS2R*(0.00264*SIN(OM)+0.000063*SIN(OM+OM));
}

export function sla_dat(UTC) {
    /*
    *     - - - -
    *      D A T
    *     - - - -
    *
    *  Increment to be applied to Coordinated Universal Time UTC to give
    *  International Atomic Time TAI (double precision)
    *
    *  Given:
    *     UTC      d      UTC date as a modified JD (JD-2400000.5)
    *
    *  Result:  TAI-UTC in seconds
    *
    *  Notes:
    *
    *  1  The UTC is specified to be a date rather than a time to indicate
    *     that care needs to be taken not to specify an instant which lies
    *     within a leap second.  Though in most cases UTC can include the
    *     fractional part, correct behaviour on the day of a leap second
    *     can only be guaranteed up to the end of the second 23:59:59.
    *
    *  2  For epochs from 1961 January 1 onwards, the expressions from the
    *     file ftp://maia.usno.navy.mil/ser7/tai-utc.dat are used.
    *
    *  3  The 5ms time step at 1961 January 1 is taken from 2.58.1 (p87) of
    *     the 1992 Explanatory Supplement.
    *
    *  4  UTC began at 1960 January 1.0 (JD 2436934.5) and it is improper
    *     to call the routine with an earlier epoch.  However, if this
    *     is attempted, the TAI-UTC expression for the year 1960 is used.
    *
    *
    *     :-----------------------------------------:
    *     :                                         :
    *     :                IMPORTANT                :
    *     :                                         :
    *     :  This routine must be updated on each   :
    *     :     occasion that a leap second is      :
    *     :                announced                :
    *     :                                         :
    *     :  Latest leap second:  2009 January 1    :
    *     :                                         :
    *     :-----------------------------------------:
    *
    *  Last revision:   11 July 2005
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let DT;

    if(false) {

    /* - - - - - - - - - - - - - - - - - - - - - - *
    *  Add new code here on each occasion that a  *
    *  leap second is announced, and update the   *
    *  preamble comments appropriately.           *
    * - - - - - - - - - - - - - - - - - - - - - - */

    }
    //  2012 July 1
    else if(UTC >= 56109) {
        DT=35.0;
    }

    //  2009 January 1
    else if(UTC >= 54832) {
        DT=34.0;
    }
    //  2006 January 1
    else if(UTC >= 53736) {
        DT=33.0;
    }
    //  1999 January 1
    else if(UTC >= 51179) {
        DT=32.0;
    }
    //  1997 July 1
    else if(UTC >= 50630) {
        DT=31.0;
    }
    //  1996 January 1
    else if(UTC >= 50083) {
        DT=30.0;
    }
    //  1994 July 1
    else if(UTC >= 49534) {
        DT=29.0;
    }
    //  1993 July 1
    else if(UTC >= 49169) {
        DT=28.0;
    }
    //  1992 July 1
    else if(UTC >= 48804) {
        DT=27.0;
    }
    //  1991 January 1
    else if(UTC >= 48257) {
        DT=26.0;
    }
    //  1990 January 1
    else if(UTC >= 47892) {
        DT=25.0;
    }
    //  1988 January 1
    else if(UTC >= 47161) {
        DT=24.0;
    }
    //  1985 July 1
    else if(UTC >= 46247) {
        DT=23.0;
    }
    //  1983 July 1
    else if(UTC >= 45516) {
        DT=22.0;
    }
    //  1982 July 1
    else if(UTC >= 45151) {
        DT=21.0;
    }
    //  1981 July 1
    else if(UTC >= 44786) {
        DT=20.0;
    }
    //  1980 January 1
    else if(UTC >= 44239) {
        DT=19.0;
    }
    //  1979 January 1
    else if(UTC >= 43874) {
        DT=18.0;
    }
    //  1978 January 1
    else if(UTC >= 43509) {
        DT=17.0;
    }
    //  1977 January 1
    else if(UTC >= 43144) {
        DT=16.0;
    }
    //  1976 January 1
    else if(UTC >= 42778) {
        DT=15.0;
    }
    //  1975 January 1
    else if(UTC >= 42413) {
        DT=14.0;
    }
    //  1974 January 1
    else if(UTC >= 42048) {
        DT=13.0;
    }
    //  1973 January 1
    else if(UTC >= 41683) {
        DT=12.0;
    }
    //  1972 July 1
    else if(UTC >= 41499) {
        DT=11.0;
    }
    //  1972 January 1
    else if(UTC >= 41317) {
        DT=10.0;
    }
    //  1968 February 1
    else if(UTC >= 39887) {
        DT=4.2131700+(UTC-39126)*0.002592;
    }
    //  1966 January 1
    else if(UTC >= 39126) {
        DT=4.3131700+(UTC-39126)*0.002592;
    }
    //  1965 September 1
    else if(UTC >= 39004) {
        DT=3.8401300+(UTC-38761)*0.001296;
    }
    //  1965 July 1
    else if(UTC >= 38942) {
        DT=3.7401300+(UTC-38761)*0.001296;
    }
    //  1965 March 1
    else if(UTC >= 38820) {
        DT=3.6401300+(UTC-38761)*0.001296;
    }
    //  1965 January 1
    else if(UTC >= 38761) {
        DT=3.5401300+(UTC-38761)*0.001296;
    }
    //  1964 September 1
    else if(UTC >= 38639) {
        DT=3.4401300+(UTC-38761)*0.001296;
    }
    //  1964 April 1
    else if(UTC >= 38486) {
        DT=3.3401300+(UTC-38761)*0.001296;
    }
    //  1964 January 1
    else if(UTC >= 38395) {
        DT=3.2401300+(UTC-38761)*0.001296;
    }
    //  1963 November 1
    else if(UTC >= 38334) {
        DT=1.9458580+(UTC-37665)*0.0011232;
    }
    //  1962 January 1
    else if(UTC >= 37665) {
        DT=1.8458580+(UTC-37665)*0.0011232;
    }
    //  1961 August 1
    else if(UTC >= 37512) {
        DT=1.3728180+(UTC-37300)*0.001296;
    }
    //  1961 January 1
    else if(UTC >= 37300) {
        DT=1.4228180+(UTC-37300)*0.001296;
    }
    //  Before that
    else {
        DT=1.4178180+(UTC-37300)*0.001296;
    }

    return DT;
}

export function sla_dtt(UTC) {
    /*
    *     - - - -
    *      D T T
    *     - - - -
    *
    *  Increment to be applied to Coordinated Universal Time UTC to give
    *  Terrestrial Time TT (formerly Ephemeris Time ET)
    *
    *  (double precision)
    *
    *  Given:
    *     UTC      d      UTC date as a modified JD (JD-2400000.5)
    *
    *  Result:  TT-UTC in seconds
    *
    *  Notes:
    *
    *  1  The UTC is specified to be a date rather than a time to indicate
    *     that care needs to be taken not to specify an instant which lies
    *     within a leap second.  Though in most cases UTC can include the
    *     fractional part, correct behaviour on the day of a leap second
    *     can only be guaranteed up to the end of the second 23:59:59.
    *
    *  2  Pre 1972 January 1 a fixed value of 10 + ET-TAI is returned.
    *
    *  3  See also the routine sla_DT, which roughly estimates ET-UT for
    *     historical epochs.
    *
    *  Called:  sla_DAT
    *
    *  P.T.Wallace   Starlink   6 December 1994
    *
    *  Copyright (C) 1995 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    return 32.184+sla_dat(UTC);     
}

export function MOD(a, b) {
    return a % b;
}

export function sla_dt(EPOCH) {
    /*
    *     - - -
    *      D T
    *     - - -
    *
    *  Estimate the offset between dynamical time and Universal Time
    *  for a given historical epoch.
    *
    *  Given:
    *     EPOCH       d        (Julian) epoch (e.g. 1850D0)
    *
    *  The result is a rough estimate of ET-UT (after 1984, TT-UT) at
    *  the given epoch, in seconds.
    *
    *  Notes:
    *
    *  1  Depending on the epoch, one of three parabolic approximations
    *     is used:
    *
    *      before 979    Stephenson & Morrison's 390 BC to AD 948 model
    *      979 to 1708   Stephenson & Morrison's 948 to 1600 model
    *      after 1708    McCarthy & Babcock's post-1650 model
    *
    *     The breakpoints are chosen to ensure continuity:  they occur
    *     at places where the adjacent models give the same answer as
    *     each other.
    *
    *  2  The accuracy is modest, with errors of up to 20 sec during
    *     the interval since 1650, rising to perhaps 30 min by 1000 BC.
    *     Comparatively accurate values from AD 1600 are tabulated in
    *     the Astronomical Almanac (see section K8 of the 1995 AA).
    *
    *  3  The use of double-precision for both argument and result is
    *     purely for compatibility with other SLALIB time routines.
    *
    *  4  The models used are based on a lunar tidal acceleration value
    *     of -26.00 arcsec per century.
    *
    *  Reference:  Explanatory Supplement to the Astronomical Almanac,
    *              ed P.K.Seidelmann, University Science Books (1992),
    *              section 2.553, p83.  This contains references to
    *              the Stephenson & Morrison and McCarthy & Babcock
    *              papers.
    *
    *  P.T.Wallace   Starlink   1 March 1995
    *
    *  Copyright (C) 1995 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let T,W,S;

    //  Centuries since 1800
    T=(EPOCH-1800.0)/100.0;

    //  Select model
    if(EPOCH >= 1708.185161980887) {
        //  Post-1708: use McCarthy & Babcock
        W=T-0.19;
        S=5.156+13.3066*W*W;
    }
    else if(EPOCH >= 979.0258204760233) {
        //  979-1708: use Stephenson & Morrison's 948-1600 model
        S=25.5*T*T;
    }
    else {
        //Pre-979: use Stephenson & Morrison's 390 BC to AD 948 model
        S=1360.0+(320.0+44.3*T)*T;
    }

    return S;
}

export function sla_gmst(UT1) {
    /*
    *     - - - - -
    *      G M S T
    *     - - - - -
    *
    *  Conversion from universal time to sidereal time (double precision)
    *
    *  Given:
    *    UT1    dp     universal time (strictly UT1) expressed as
    *                  modified Julian Date (JD-2400000.5)
    *
    *  The result is the Greenwich mean sidereal time (double
    *  precision, radians).
    *
    *  The IAU 1982 expression (see page S15 of 1984 Astronomical Almanac)
    *  is used, but rearranged to reduce rounding errors.  This expression
    *  is always described as giving the GMST at 0 hours UT.  In fact, it
    *  gives the difference between the GMST and the UT, which happens to
    *  equal the GMST (modulo 24 hours) at 0 hours UT each day.  In this
    *  routine, the entire UT is used directly as the argument for the
    *  standard formula, and the fractional part of the UT is added
    *  separately.  Note that the factor 1.0027379... does not appear in the
    *  IAU 1982 expression explicitly but in the form of the coefficient
    *  8640184.812866, which is 86400x36525x0.0027379...
    *
    *  See also the routine sla_GMSTA, which delivers better numerical
    *  precision by accepting the UT date and time as separate arguments.
    *
    *  Called:  sla_DRANRM
    *
    *  P.T.Wallace   Starlink   14 October 2001
    *
    *  Copyright (C) 2001 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */



    let D2PI=6.283185307179586476925286766559;
    let S2R=7.272205216643039903848711535369e-5;
    let TU;

    //  Julian centuries from fundamental epoch J2000 to this UT
    TU=(UT1-51544.5)/36525.0;

    //  GMST at this UT
    return sla_dranrm(MOD(UT1,1.0)*D2PI+(24110.54841+(8640184.812866+(0.093104-6.2e-6*TU)*TU)*TU)*S2R)
}

export function sla_planet(DATE, NP) {
    /*
    *     - - - - - - -
    *      P L A N E T
    *     - - - - - - -
    *
    *  Approximate heliocentric position and velocity of a specified
    *  major planet.
    *
    *  Given:
    *     DATE      d      Modified Julian Date (JD - 2400000.5)
    *     NP        i      planet (1=Mercury, 2=Venus, 3=EMB ... 9=Pluto)
    *
    *  Returned:
    *     PV        d(6)   heliocentric x,y,z,xdot,ydot,zdot, J2000
    *                                           equatorial triad (AU,AU/s)
    *     JSTAT     i      status: +1 = warning: date out of range
    *                               0 = OK
    *                              -1 = illegal NP (outside 1-9)
    *                              -2 = solution didn't converge
    *
    *  Called:  sla_PLANEL
    *
    *  Notes
    *
    *  1  The epoch, DATE, is in the TDB timescale and is a Modified
    *     Julian Date (JD-2400000.5).
    *
    *  2  The reference frame is equatorial and is with respect to the
    *     mean equinox and ecliptic of epoch J2000.
    *
    *  3  If an NP value outside the range 1-9 is supplied, an error
    *     status (JSTAT = -1) is returned and the PV vector set to zeroes.
    *
    *  4  The algorithm for obtaining the mean elements of the planets
    *     from Mercury to Neptune is due to J.L. Simon, P. Bretagnon,
    *     J. Chapront, M. Chapront-Touze, G. Francou and J. Laskar
    *     (Bureau des Longitudes, Paris).  The (completely different)
    *     algorithm for calculating the ecliptic coordinates of Pluto
    *     is by Meeus.
    *
    *  5  Comparisons of the present routine with the JPL DE200 ephemeris
    *     give the following RMS errors over the interval 1960-2025:
    *
    *                      position (km)     speed (metre/sec)
    *
    *        Mercury            334               0.437
    *        Venus             1060               0.855
    *        EMB               2010               0.815
    *        Mars              7690               1.98
    *        Jupiter          71700               7.70
    *        Saturn          199000              19.4
    *        Uranus          564000              16.4
    *        Neptune         158000              14.4
    *        Pluto            36400               0.137
    *
    *     From comparisons with DE102, Simon et al quote the following
    *     longitude accuracies over the interval 1800-2200:
    *
    *        Mercury                 4"
    *        Venus                   5"
    *        EMB                     6"
    *        Mars                   17"
    *        Jupiter                71"
    *        Saturn                 81"
    *        Uranus                 86"
    *        Neptune                11"
    *
    *     In the case of Pluto, Meeus quotes an accuracy of 0.6 arcsec
    *     in longitude and 0.2 arcsec in latitude for the period
    *     1885-2099.
    *
    *     For all except Pluto, over the period 1000-3000 the accuracy
    *     is better than 1.5 times that over 1800-2200.  Outside the
    *     period 1000-3000 the accuracy declines.  For Pluto the
    *     accuracy declines rapidly outside the period 1885-2099.
    *     Outside these ranges (1885-2099 for Pluto, 1000-3000 for
    *     the rest) a "date out of range" warning status (JSTAT=+1)
    *     is returned.
    *
    *  6  The algorithms for (i) Mercury through Neptune and (ii) Pluto
    *     are completely independent.  In the Mercury through Neptune
    *     case, the present SLALIB implementation differs from the
    *     original Simon et al Fortran code in the following respects.
    *
    *     *  The date is supplied as a Modified Julian Date rather
    *        than a Julian Date (MJD = JD - 2400000.5).
    *
    *     *  The result is returned only in equatorial Cartesian form;
    *        the ecliptic longitude, latitude and radius vector are not
    *        returned.
    *
    *     *  The velocity is in AU per second, not AU per day.
    *
    *     *  Different error/warning status values are used.
    *
    *     *  Kepler's equation is not solved inline.
    *
    *     *  Polynomials in T are nested to minimize rounding errors.
    *
    *     *  Explicit double-precision constants are used to avoid
    *        mixed-mode expressions.
    *
    *     *  There are other, cosmetic, changes to comply with
    *        Starlink/SLALIB style guidelines.
    *
    *     None of the above changes affects the result significantly.
    *
    *  7  For NP=3 the result is for the Earth-Moon Barycentre.  To
    *     obtain the heliocentric position and velocity of the Earth,
    *     either use the SLALIB routine sla_EVP (or sla_EPV) or call
    *     sla_DMOON and subtract 0.012150581 times the geocentric Moon
    *     vector from the EMB vector produced by the present routine.
    *     (The Moon vector should be precessed to J2000 first, but this
    *     can be omitted for modern epochs without introducing significant
    *     inaccuracy.)
    *
    *  References:  Simon et al., Astron. Astrophys. 282, 663 (1994).
    *               Meeus, Astronomical Algorithms, Willmann-Bell (1991).
    *
    *  This revision:  19 June 2004
    *
    *  Copyright (C) 2004 P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let PV = new Array();
    let JSTAT;

    //  2Pi, deg to radians, arcsec to radians
    let D2PI=6.283185307179586476925286766559,
        D2R=0.017453292519943295769236907684886,
        AS2R=4.848136811095359935899141023579e-6;

    //  Gaussian gravitational constant (exact)
    let GCON=0.01720209895;

    //  Seconds per Julian century
    let SPC=36525.0*86400.0;

    //  Sin and cos of J2000 mean obliquity (IAU 1976)
    let SE=0.3977771559319137,
        CE=0.9174820620691818;
        
    let WLBR = new Array(3);
    let WLBRD = new Array(3);

    let A, DLM, E, PI, DINC, OMEGA, DKP, CA, SA,
        DKQ, CLO, SLO,
        T,DA,DE,DPE,DI,DO,DMU,ARGA,ARGL,DM,
        DJ0,DS0,DP0,DL0,DLD0,DB0,DR0,
        DJ,DS,DP,DJD,DSD,DPD,
        WJ,WS,WP,AL,ALD,SAL,CAL,
        AC,BC,DL,DLD,DB,DBD,DR,DRD,
        SL,CL,SB,CB,SLCB,CLCB,X,Y,Z,XD,YD,ZD;

    /*  -----------------------
    *  Mercury through Neptune
    *  -----------------------*/

    //  Planetary inverse masses
    let AMAS = [6023600.0,408523.5,328900.5,3098710.0,1047.355,3498.5,22869,19314.0];

    /*
    *  Tables giving the mean Keplerian elements, limited to T**2 terms:
    *
    *         A       semi-major axis (AU)
    *         DLM     mean longitude (degree and arcsecond)
    *         E       eccentricity
    *         PI      longitude of the perihelion (degree and arcsecond)
    *         DINC    inclination (degree and arcsecond)
    *         OMEGA   longitude of the ascending node (degree and arcsecond)
    */
    A = [
         [  0.3870983098,             0,      0],
         [  0.7233298200,             0,      0],
         [  1.0000010178,             0,      0],
         [  1.5236793419,           3e-10,      0],
         [  5.2026032092,       19132e-10,  -39e-10],
         [  9.5549091915, -0.0000213896,  444e-10],
         [ 19.2184460618,       -3716e-10,  979e-10],
         [ 30.1103868694,      -16635e-10,  686e-10]];
    
    DLM = [
         [ 252.25090552, 5381016286.88982,  -1.92789],
         [ 181.97980085, 2106641364.33548,   0.59381],
         [ 100.46645683, 1295977422.83429,  -2.04411],
         [ 355.43299958,  689050774.93988,   0.94264],
         [  34.35151874,  109256603.77991, -30.60378],
         [  50.07744430,   43996098.55732,  75.61614],
         [ 314.05500511,   15424811.93933,  -1.75083],
         [ 304.34866548,    7865503.20744,   0.21103]];
    
    E = [
         [ 0.2056317526,  0.0002040653,      -28349e-10],
         [ 0.0067719164, -0.0004776521,       98127e-10],
         [ 0.0167086342, -0.0004203654, -0.0000126734],
         [ 0.0934006477,  0.0009048438,      -80641e-10],
         [ 0.0484979255,  0.0016322542, -0.0000471366],
         [ 0.0555481426, -0.0034664062, -0.0000643639],
         [ 0.0463812221, -0.0002729293,  0.0000078913],
         [ 0.0094557470,  0.0000603263,            0 ]];
   
    PI = [
         [  77.45611904,  5719.11590,   -4.83016],
         [ 131.56370300,   175.48640, -498.48184],
         [ 102.93734808, 11612.35290,   53.27577],
         [ 336.06023395, 15980.45908,  -62.32800],
         [  14.33120687,  7758.75163,  259.95938],
         [  93.05723748, 20395.49439,  190.25952],
         [ 173.00529106,  3215.56238,  -34.09288],
         [  48.12027554,  1050.71912,   27.39717]];
    
    DINC = [
         [ 7.00498625, -214.25629,   0.28977],
         [ 3.39466189,  -30.84437, -11.67836],
         [          0,  469.97289,  -3.35053],
         [ 1.84972648, -293.31722,  -8.11830],
         [ 1.30326698,  -71.55890,  11.95297],
         [ 2.48887878,   91.85195, -17.66225],
         [ 0.77319689,  -60.72723,   1.25759],
         [ 1.76995259,    8.12333,   0.08135]];
    
    OMEGA = [
         [  48.33089304,  -4515.21727,  -31.79892],
         [  76.67992019, -10008.48154,  -51.32614],
         [ 174.87317577,  -8679.27034,   15.34191],
         [  49.55809321, -10620.90088, -230.57416],
         [ 100.46440702,   6362.03561,  326.52178],
         [ 113.66550252,  -9240.19942,  -66.23743],
         [  74.00595701,   2669.15033,  145.93964],
         [ 131.78405702,   -221.94322,   -0.78728]],
    /*
    *  Tables for trigonometric terms to be added to the mean elements
    *  of the semi-major axes.
    */
    DKP = [
         [ 69613, 75645, 88306, 59899, 15746, 71087, 142173,  3086,    0],
         [ 21863, 32794, 26934, 10931, 26250, 43725,  53867, 28939,    0],
         [ 16002, 21863, 32004, 10931, 14529, 16368,  15318, 32794,    0],
         [ 6345,   7818, 15636,  7077,  8184, 14163,   1107,  4872,    0],
         [ 1760,   1454,  1167,   880,   287,  2640,     19,  2047, 1454],
         [  574,      0,   880,   287,    19,  1760,   1167,   306,  574],
         [  204,      0,   177,  1265,     4,   385,    200,   208,  204],
         [    0,    102,   106,     4,    98,  1367,    487,   204,    0]];
    
    CA = [
         [      4,    -13,    11,    -9,    -9,    -3,    -1,     4,    0],
         [   -156,     59,   -42,     6,    19,   -20,   -10,   -12,    0],
         [     64,   -152,    62,    -8,    32,   -41,    19,   -11,    0],
         [    124,    621,  -145,   208,    54,   -57,    30,    15,    0],
         [ -23437,  -2634,  6601,  6259, -1507, -1821,  2620, -2115,-1489],
         [  62911,-119919, 79336, 17814,-24241, 12068,  8306, -4893, 8902],
         [ 389061,-262125,-44088,  8387,-22976, -2093,  -615, -9720, 6633],
         [-412235,-157046,-31430, 37817, -9740,   -13, -7449,  9644,    0]];
    
    SA = [
         [     -29,    -1,     9,     6,    -6,     5,     4,     0,    0],
         [     -48,  -125,   -26,   -37,    18,   -13,   -20,    -2,    0],
         [    -150,   -46,    68,    54,    14,    24,   -28,    22,    0],
         [    -621,   532,  -694,   -20,   192,   -94,    71,   -73,    0],
         [  -14614,-19828, -5869,  1881, -4372, -2255,   782,   930,  913],
         [  139737,     0, 24667, 51123, -5102,  7429, -4095, -1976,-9566],
         [ -138081,     0, 37205,-49039,-41901,-33872,-27037,-12474,18797],
         [       0, 28492,133236, 69654, 52322,-49577,-26430, -3593,    0]];
    /*
    *  Tables giving the trigonometric terms to be added to the mean
    *  elements of the mean longitudes.
    */
    DKQ = [
         [  3086, 15746, 69613, 59899, 75645, 88306, 12661, 2658,  0,   0],
         [ 21863, 32794, 10931,    73,  4387, 26934,  1473, 2157,  0,   0],
         [    10, 16002, 21863, 10931,  1473, 32004,  4387,   73,  0,   0],
         [    10,  6345,  7818,  1107, 15636,  7077,  8184,  532, 10,   0],
         [    19,  1760,  1454,   287,  1167,   880,   574, 2640, 19,1454],
         [    19,   574,   287,   306,  1760,    12,    31,   38, 19, 574],
         [     4,   204,   177,     8,    31,   200,  1265,  102,  4, 204],
         [     4,   102,   106,     8,    98,  1367,   487,  204,  4, 102]];
    
    CLO = [
         [     21,   -95, -157,   41,   -5,   42,   23,   30,     0,    0],
         [   -160,  -313, -235,   60,  -74,  -76,  -27,   34,     0,    0],
         [   -325,  -322,  -79,  232,  -52,   97,   55,  -41,     0,    0],
         [   2268,  -979,  802,  602, -668,  -33,  345,  201,   -55,    0],
         [   7610, -4997,-7689,-5841,-2617, 1115, -748, -607,  6074,  354],
         [ -18549, 30125,20012, -730,  824,   23, 1289, -352,-14767,-2062],
         [-135245,-14594, 4197,-4030,-5630,-2898, 2540, -306,  2939, 1986],
         [  89948,  2103, 8963, 2695, 3682, 1648,  866, -154, -1963, -283]];
    
    SLO = [
         [   -342,   136,  -23,   62,   66,  -52,  -33,   17,     0,    0],
         [    524,  -149,  -35,  117,  151,  122,  -71,  -62,     0,    0],
         [   -105,  -137,  258,   35, -116,  -88, -112,  -80,     0,    0],
         [    854,  -205, -936, -240,  140, -341,  -97, -232,   536,    0],
         [ -56980,  8016, 1012, 1448,-3024,-3710,  318,  503,  3767,  577],
         [ 138606,-13478,-4964, 1441,-1319,-1482,  427, 1236, -9167,-1918],
         [  71234,-41116, 5334,-4935,-1848,   66,  434,-1748,  3780, -701],
         [ -47645, 11647, 2166, 3194,  679,    0, -244, -419, -2531,   48]];

    
    
    /*  -----
    *  Pluto
    *  -----

    *
    *  Coefficients for fundamental arguments:  mean longitudes
    *  (degrees) and mean rate of change of longitude (degrees per
    *  Julian century) for Jupiter, Saturn and Pluto
    */
    DJ0 = 34.35;
    DJD = 3034.9057;
    DS0 = 50.08;
    DSD = 1222.1138;
    DP0 = 238.96;
    DPD = 144.9600;

    //  Coefficients for latitude, longitude, radius vector
    DL0 = 238.956785;
    DLD0 = 144.96;
    DB0 = -3.908202;
    DR0 = 40.7247248;

    /*
    *  Coefficients for periodic terms (Meeus's Table 36.A)
    *
    *  The coefficients for term n in the series are:
    *
    *    IJSP(1,n)     J
    *    IJSP(2,n)     S
    *    IJSP(3,n)     P
    *    AB(1,1,n)     longitude sine (degrees)
    *    AB(2,1,n)     longitude cosine (degrees)
    *    AB(1,2,n)     latitude sine (degrees)
    *    AB(2,2,n)     latitude cosine (degrees)
    *    AB(1,3,n)     radius vector sine (AU)
    *    AB(2,3,n)     radius vector cosine (AU)
    */
    
    let IJSPAB = [
        [[                             0,  0,  1],
         [            -19798886e-6,  19848454e-6],
         [             -5453098e-6, -14974876e-6],
         [             66867334e-7,  68955876e-7]],
        [[                             0,  0,  2],
         [               897499e-6,  -4955707e-6],
         [              3527363e-6,   1672673e-6],
         [            -11826086e-7,   -333765e-7]],
        [[                             0,  0,  3],
         [               610820e-6,   1210521e-6],
         [             -1050939e-6,    327763e-6],
         [              1593657e-7,  -1439953e-7]],
        [[                             0,  0,  4],
         [              -341639e-6,   -189719e-6],
         [               178691e-6,   -291925e-6],
         [               -18948e-7,    482443e-7]],
        [[                             0,  0,  5],
         [               129027e-6,    -34863e-6],
         [                18763e-6,    100448e-6],
         [               -66634e-7,    -85576e-7]],
        [[                             0,  0,  6],
         [               -38215e-6,     31061e-6],
         [               -30594e-6,    -25838e-6],
         [                30841e-7,     -5765e-7]],
        [[                             0,  1, -1],
         [                20349e-6,     -9886e-6],
         [                 4965e-6,     11263e-6],
         [                -6140e-7,     22254e-7]],
        [[                             0,  1,  0],
         [                -4045e-6,     -4904e-6],
         [                  310e-6,      -132e-6],
         [                 4434e-7,      4443e-7]],
        [[                             0,  1,  1],
         [                -5885e-6,     -3238e-6],
         [                 2036e-6,      -947e-6],
         [                -1518e-7,       641e-7]],
        [[                             0,  1,  2],
         [                -3812e-6,      3011e-6],
         [                   -2e-6,      -674e-6],
         [                   -5e-7,       792e-7]],
        [[                             0,  1,  3],
         [                 -601e-6,      3468e-6],
         [                 -329e-6,      -563e-6],
         [                  518e-7,       518e-7]],
        [[                             0,  2, -2],
         [                 1237e-6,       463e-6],
         [                  -64e-6,        39e-6],
         [                  -13e-7,      -221e-7]],
        [[                             0,  2, -1],
         [                 1086e-6,      -911e-6],
         [                  -94e-6,       210e-6],
         [                  837e-7,      -494e-7]],
        [[                             0,  2,  0],
         [                  595e-6,     -1229e-6],
         [                   -8e-6,      -160e-6],
         [                 -281e-7,       616e-7]],
        [[                             1, -1,  0],
         [                 2484e-6,      -485e-6],
         [                 -177e-6,       259e-6],
         [                  260e-7,      -395e-7]],
        [[                             1, -1,  1],
         [                  839e-6,     -1414e-6],
         [                   17e-6,       234e-6],
         [                 -191e-7,      -396e-7]],
        [[                             1,  0, -3],
         [                 -964e-6,      1059e-6],
         [                  582e-6,      -285e-6],
         [                -3218e-7,       370e-7]],
        [[                             1,  0, -2],
         [                -2303e-6,     -1038e-6],
         [                 -298e-6,       692e-6],
         [                 8019e-7,     -7869e-7]],
        [[                             1,  0, -1],
         [                 7049e-6,       747e-6],
         [                  157e-6,       201e-6],
         [                  105e-7,     45637e-7]],
        [[                             1,  0,  0],
         [                 1179e-6,      -358e-6],
         [                  304e-6,       825e-6],
         [                 8623e-7,      8444e-7]],
        [[                             1,  0,  1],
         [                  393e-6,       -63e-6],
         [                 -124e-6,       -29e-6],
         [                 -896e-7,      -801e-7]],
        [[                             1,  0,  2],
         [                  111e-6,      -268e-6],
         [                   15e-6,         8e-6],
         [                  208e-7,      -122e-7]],
        [[                             1,  0,  3],
         [                  -52e-6,      -154e-6],
         [                    7e-6,        15e-6],
         [                 -133e-7,        65e-7]],
        [[                             1,  0,  4],
         [                  -78e-6,       -30e-6],
         [                    2e-6,         2e-6],
         [                  -16e-7,         1e-7]],
        [[                             1,  1, -3],
         [                  -34e-6,       -26e-6],
         [                    4e-6,         2e-6],
         [                  -22e-7,         7e-7]],
        [[                             1,  1, -2],
         [                  -43e-6,         1e-6],
         [                    3e-6,         0e-6],
         [                   -8e-7,        16e-7]],
        [[                             1,  1, -1],
         [                  -15e-6,        21e-6],
         [                    1e-6,        -1e-6],
         [                    2e-7,         9e-7]],
        [[                             1,  1,  0],
         [                   -1e-6,        15e-6],
         [                    0e-6,        -2e-6],
         [                   12e-7,         5e-7]],
        [[                             1,  1,  1],
         [                    4e-6,         7e-6],
         [                    1e-6,         0e-6],
         [                    1e-7,        -3e-7]],
        [[                             1,  1,  3],
         [                    1e-6,         5e-6],
         [                    1e-6,        -1e-6],
         [                    1e-7,         0e-7]],
        [[                             2,  0, -6],
         [                    8e-6,         3e-6],
         [                   -2e-6,        -3e-6],
         [                    9e-7,         5e-7]],
        [[                             2,  0, -5],
         [                   -3e-6,         6e-6],
         [                    1e-6,         2e-6],
         [                    2e-7,        -1e-7]],
        [[                             2,  0, -4],
         [                    6e-6,       -13e-6],
         [                   -8e-6,         2e-6],
         [                   14e-7,        10e-7]],
        [[                             2,  0, -3],
         [                   10e-6,        22e-6],
         [                   10e-6,        -7e-6],
         [                  -65e-7,        12e-7]],
        [[                             2,  0, -2],
         [                  -57e-6,       -32e-6],
         [                    0e-6,        21e-6],
         [                  126e-7,      -233e-7]],
        [[                             2,  0, -1],
         [                  157e-6,       -46e-6],
         [                    8e-6,         5e-6],
         [                  270e-7,      1068e-7]],
        [[                             2,  0,  0],
         [                   12e-6,       -18e-6],
         [                   13e-6,        16e-6],
         [                  254e-7,       155e-7]],
        [[                             2,  0,  1],
         [                   -4e-6,         8e-6],
         [                   -2e-6,        -3e-6],
         [                  -26e-7,        -2e-7]],
        [[                             2,  0,  2],
         [                   -5e-6,         0e-6],
         [                    0e-6,         0e-6],
         [                    7e-7,         0e-7]],
        [[                             2,  0,  3],
         [                    3e-6,         4e-6],
         [                    0e-6,         1e-6],
         [                  -11e-7,         4e-7]],
        [[                             3,  0, -2],
         [                   -1e-6,        -1e-6],
         [                    0e-6,         1e-6],
         [                    4e-7,       -14e-7]],
        [[                             3,  0, -1],
         [                    6e-6,        -3e-6],
         [                    0e-6,         0e-6],
         [                   18e-7,        35e-7]],
        [[                             3,  0,  0],
         [                   -1e-6,        -2e-6],
         [                    0e-6,         1e-6],
         [                   13e-7,         3e-7]]];

    //  Validate the planet number.
    if(NP < 1 || NP > 9) {
        JSTAT = -1;
        for(let i=0; i<6; i++) {
            PV[i] = 0.0;
        }
    }
    else {


        //     Separate algorithms for Pluto and the rest.
        if(NP != 9) {
        
            /* -----------------------
            *   Mercury through Neptune
            *  -----------------------*/

            //  Time: Julian millennia since J2000.
            T=(DATE-51544.5)/365250

            //  OK status unless remote epoch.
            if(ABS(T) <= 1.0) {
                JSTAT = 0;
            }
            else {
                JSTAT = 1;
            }

            //subtract one from NP to make it an index
            
            
            NP = NP -1;
            //  Compute the mean elements.
            DA=A[NP][0]+(A[NP][1]+A[NP][2]*T)*T;
            DL=(3600*DLM[NP][0]+(DLM[NP][1]+DLM[NP][2]*T)*T)*AS2R;
            DE=E[NP][0]+(E[NP][1]+E[NP][2]*T)*T;
            DPE=MOD((3600*PI[NP][0]+(PI[NP][1]+PI[NP][2]*T)*T)*AS2R,D2PI);
            DI=(3600*DINC[NP][0]+(DINC[NP][1]+DINC[NP][2]*T)*T)*AS2R;
            DO=MOD((3600*OMEGA[NP][0]+(OMEGA[NP][1]+OMEGA[NP][2]*T)*T)*AS2R,D2PI);
            
            
            
            //  Apply the trigonometric terms.
            DMU=0.35953620*T;
            for(let j=0; j<8; j++) {
               ARGA=DKP[NP][j]*DMU;
               ARGL=DKQ[NP][j]*DMU;
               DA=DA+(CA[NP][j]*COS(ARGA)+SA[NP][j]*SIN(ARGA))*1e-7;
               DL=DL+(CLO[NP][j]*COS(ARGL)+SLO[NP][j]*SIN(ARGL))*1e-7;
            }
            
            ARGA=DKP[NP][8]*DMU;
            DA=DA+T*(CA[NP][8]*COS(ARGA)+SA[NP][8]*SIN(ARGA))*1e-7;
            
            for(let j=8; j<9; j++) {
               ARGL=DKQ[NP][j]*DMU;
               DL=DL+T*(CLO[NP][j]*COS(ARGL)+SLO[NP][j]*SIN(ARGL))*1e-7;
            }
            DL=MOD(DL,D2PI);
            
               

            //  Daily motion.
            DM=GCON*SQRT((1+1/AMAS[NP])/(DA*DA*DA));

            //  Make the prediction.
            let result = sla_planel(DATE,1,DATE,DI,DO,DPE,DA,DE,DL,DM);
            PV = result[0];
            
            
            
            let J = result[1];
            if(J < 0) {
                JSTAT=-2;
            }
        }
        else {
            

            /*        -----
            *        Pluto
            *        -----*/

            //  Time: Julian centuries since J2000.
            T=(DATE-51544.5)/36525.0;

            // OK status unless remote epoch.
            if(T >= -1.15 && T <= 1.0) {
                JSTAT = 0;
            }
            else {
                JSTAT = 1;
            }
            
            // Fundamental arguments (radians).
            DJ=(DJ0+DJD*T)*D2R;
            DS=(DS0+DSD*T)*D2R;
            DP=(DP0+DPD*T)*D2R;

            //Initialize coefficients and derivatives.
            for(let i=0; i<3; i++) {
                WLBR[i]=0.0;
                WLBRD[i]=0.0;
            }

            //Term by term through Meeus Table 36.A.
            for(let j=0; j<IJSPAB.length; j++) {

                //  Argument and derivative (radians, radians per century).
                WJ=IJSPAB[j][0][0];
                WS=IJSPAB[j][0][1];
                WP=IJSPAB[j][0][2];
                AL=WJ*DJ+WS*DS+WP*DP;
                ALD=(WJ*DJD+WS*DSD+WP*DPD)*D2R;


                //  Functions of argument.
                SAL=SIN(AL);
                CAL=COS(AL);

                //  Periodic terms in longitude, latitude, radius vector.
                for(let i=0; i<3; i++) {

                    //  A and B coefficients (deg, AU).
                    AC=IJSPAB[j][i+1][0];
                    BC=IJSPAB[j][i+1][1];

                    //  Periodic terms (deg, AU, deg/Jc, AU/Jc).
                    WLBR[i]=WLBR[i]+AC*SAL+BC*CAL;
                    WLBRD[i]=WLBRD[i]+(AC*CAL-BC*SAL)*ALD;
                }
            }

            // Heliocentric longitude and derivative (radians, radians/sec).
            DL=(DL0+DLD0*T+WLBR[0])*D2R;
            DLD=(DLD0+WLBRD[0])*D2R/SPC;

            // Heliocentric latitude and derivative (radians, radians/sec).
            DB=(DB0+WLBR[1])*D2R;
            DBD=WLBRD[1]*D2R/SPC;

            // Heliocentric radius vector and derivative (AU, AU/sec).
            DR=DR0+WLBR[2];
            DRD=WLBRD[2]/SPC;

            // Functions of latitude, longitude, radius vector.
            SL=SIN(DL);
            CL=COS(DL);
            SB=SIN(DB);
            CB=COS(DB);
            SLCB=SL*CB;
            CLCB=CL*CB;

            // Heliocentric vector and derivative, J2000 ecliptic and equinox.
            X=DR*CLCB;
            Y=DR*SLCB;
            Z=DR*SB;
            XD=DRD*CLCB-DR*(CL*SB*DBD+SLCB*DLD);
            YD=DRD*SLCB+DR*(-SL*SB*DBD+CLCB*DLD);
            ZD=DRD*SB+DR*CB*DBD;

            // Transform to J2000 equator and equinox.
            PV[0]=X;
            PV[1]=Y*CE-Z*SE;
            PV[2]=Y*SE+Z*CE;
            PV[3]=XD;
            PV[4]=YD*CE-ZD*SE;
            PV[5]=YD*SE+ZD*CE;
        }
    }
    
    return [PV, JSTAT];
}

export function sla_planel(DATE, JFORM, EPOCH, ORBINC, ANODE, PERIH, AORQ, E, AORL, DM) {
    /*
    *     - - - - - - -
    *      P L A N E L
    *     - - - - - - -
    *
    *  Heliocentric position and velocity of a planet, asteroid or comet,
    *  starting from orbital elements.
    *
    *  Given:
    *     DATE     d     date, Modified Julian Date (JD - 2400000.5, Note 1)
    *     JFORM    i     choice of element set (1-3; Note 3)
    *     EPOCH    d     epoch of elements (TT MJD, Note 4)
    *     ORBINC   d     inclination (radians)
    *     ANODE    d     longitude of the ascending node (radians)
    *     PERIH    d     longitude or argument of perihelion (radians)
    *     AORQ     d     mean distance or perihelion distance (AU)
    *     E        d     eccentricity
    *     AORL     d     mean anomaly or longitude (radians, JFORM=1,2 only)
    *     DM       d     daily motion (radians, JFORM=1 only)
    *
    *  Returned:
    *     PV       d(6)  heliocentric x,y,z,xdot,ydot,zdot of date,
    *                                     J2000 equatorial triad (AU,AU/s)
    *     JSTAT    i     status:  0 = OK
    *                            -1 = illegal JFORM
    *                            -2 = illegal E
    *                            -3 = illegal AORQ
    *                            -4 = illegal DM
    *                            -5 = numerical error
    *
    *  Called:  sla_EL2UE, sla_UE2PV
    *
    *  Notes
    *
    *  1  DATE is the instant for which the prediction is required.  It is
    *     in the TT timescale (formerly Ephemeris Time, ET) and is a
    *     Modified Julian Date (JD-2400000.5).
    *
    *  2  The elements are with respect to the J2000 ecliptic and equinox.
    *
    *  3  A choice of three different element-set options is available:
    *
    *     Option JFORM = 1, suitable for the major planets:
    *
    *       EPOCH  = epoch of elements (TT MJD)
    *       ORBINC = inclination i (radians)
    *       ANODE  = longitude of the ascending node, big omega (radians)
    *       PERIH  = longitude of perihelion, curly pi (radians)
    *       AORQ   = mean distance, a (AU)
    *       E      = eccentricity, e (range 0 to <1)
    *       AORL   = mean longitude L (radians)
    *       DM     = daily motion (radians)
    *
    *     Option JFORM = 2, suitable for minor planets:
    *
    *       EPOCH  = epoch of elements (TT MJD)
    *       ORBINC = inclination i (radians)
    *       ANODE  = longitude of the ascending node, big omega (radians)
    *       PERIH  = argument of perihelion, little omega (radians)
    *       AORQ   = mean distance, a (AU)
    *       E      = eccentricity, e (range 0 to <1)
    *       AORL   = mean anomaly M (radians)
    *
    *     Option JFORM = 3, suitable for comets:
    *
    *       EPOCH  = epoch of elements and perihelion (TT MJD)
    *       ORBINC = inclination i (radians)
    *       ANODE  = longitude of the ascending node, big omega (radians)
    *       PERIH  = argument of perihelion, little omega (radians)
    *       AORQ   = perihelion distance, q (AU)
    *       E      = eccentricity, e (range 0 to 10)
    *
    *     Unused arguments (DM for JFORM=2, AORL and DM for JFORM=3) are not
    *     accessed.
    *
    *  4  Each of the three element sets defines an unperturbed heliocentric
    *     orbit.  For a given epoch of observation, the position of the body
    *     in its orbit can be predicted from these elements, which are
    *     called "osculating elements", using standard two-body analytical
    *     solutions.  However, due to planetary perturbations, a given set
    *     of osculating elements remains usable for only as long as the
    *     unperturbed orbit that it describes is an adequate approximation
    *     to reality.  Attached to such a set of elements is a date called
    *     the "osculating epoch", at which the elements are, momentarily,
    *     a perfect representation of the instantaneous position and
    *     velocity of the body.
    *
    *     Therefore, for any given problem there are up to three different
    *     epochs in play, and it is vital to distinguish clearly between
    *     them:
    *
    *     . The epoch of observation:  the moment in time for which the
    *       position of the body is to be predicted.
    *
    *     . The epoch defining the position of the body:  the moment in time
    *       at which, in the absence of purturbations, the specified
    *       position (mean longitude, mean anomaly, or perihelion) is
    *       reached.
    *
    *     . The osculating epoch:  the moment in time at which the given
    *       elements are correct.
    *
    *     For the major-planet and minor-planet cases it is usual to make
    *     the epoch that defines the position of the body the same as the
    *     epoch of osculation.  Thus, only two different epochs are
    *     involved:  the epoch of the elements and the epoch of observation.
    *
    *     For comets, the epoch of perihelion fixes the position in the
    *     orbit and in general a different epoch of osculation will be
    *     chosen.  Thus, all three types of epoch are involved.
    *
    *     For the present routine:
    *
    *     . The epoch of observation is the argument DATE.
    *
    *     . The epoch defining the position of the body is the argument
    *       EPOCH.
    *
    *     . The osculating epoch is not used and is assumed to be close
    *       enough to the epoch of observation to deliver adequate accuracy.
    *       If not, a preliminary call to sla_PERTEL may be used to update
    *       the element-set (and its associated osculating epoch) by
    *       applying planetary perturbations.
    *
    *  5  The reference frame for the result is with respect to the mean
    *     equator and equinox of epoch J2000.
    *
    *  6  The algorithm was originally adapted from the EPHSLA program of
    *     D.H.P.Jones (private communication, 1996).  The method is based
    *     on Stumpff's Universal Variables.
    *
    *  Reference:  Everhart, E. & Pitkin, E.T., Am.J.Phys. 51, 712, 1983.
    *
    *  P.T.Wallace   Starlink   31 December 2002
    *
    *  Copyright (C) 2002 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */
    
    let PV, U, J, JSTAT;

    //  Validate elements and convert to "universal variables" parameters.
    let result = sla_el2ue(DATE, JFORM, EPOCH,ORBINC,ANODE,PERIH,AORQ,E,AORL,DM);

    U = result[0];
    J = result[1];

    //  Determine the position and velocity.
    if(J==0) {
        result = sla_ue2pv(DATE,U);
        U = result[0];
        PV = result[1];
        J = result[2];
        
        if(J != 0) {J=-5;}
    }
          
    JSTAT = J
    
    return [PV, JSTAT];
    
}

export function sla_el2ue(DATE, JFORM, EPOCH, ORBINC, ANODE, PERIH, AORQ, E, AORL, DM) {
    /*
    *     - - - - - -
    *      E L 2 U E
    *     - - - - - -
    *
    *  Transform conventional osculating orbital elements into "universal"
    *  form.
    *
    *  Given:
    *     DATE    d      epoch (TT MJD) of osculation (Note 3)
    *     JFORM   i      choice of element set (1-3, Note 6)
    *     EPOCH   d      epoch (TT MJD) of the elements
    *     ORBINC  d      inclination (radians)
    *     ANODE   d      longitude of the ascending node (radians)
    *     PERIH   d      longitude or argument of perihelion (radians)
    *     AORQ    d      mean distance or perihelion distance (AU)
    *     E       d      eccentricity
    *     AORL    d      mean anomaly or longitude (radians, JFORM=1,2 only)
    *     DM      d      daily motion (radians, JFORM=1 only)
    *
    *  Returned:
    *     U       d(13)  universal orbital elements (Note 1)
    *
    *               (1)  combined mass (M+m)
    *               (2)  total energy of the orbit (alpha)
    *               (3)  reference (osculating) epoch (t0)
    *             (4-6)  position at reference epoch (r0)
    *             (7-9)  velocity at reference epoch (v0)
    *              (10)  heliocentric distance at reference epoch
    *              (11)  r0.v0
    *              (12)  date (t)
    *              (13)  universal eccentric anomaly (psi) of date, approx
    *
    *     JSTAT   i      status:  0 = OK
    *                            -1 = illegal JFORM
    *                            -2 = illegal E
    *                            -3 = illegal AORQ
    *                            -4 = illegal DM
    *                            -5 = numerical error
    *
    *  Called:  sla_UE2PV, sla_PV2UE
    *
    *  Notes
    *
    *  1  The "universal" elements are those which define the orbit for the
    *     purposes of the method of universal variables (see reference).
    *     They consist of the combined mass of the two bodies, an epoch,
    *     and the position and velocity vectors (arbitrary reference frame)
    *     at that epoch.  The parameter set used here includes also various
    *     quantities that can, in fact, be derived from the other
    *     information.  This approach is taken to avoiding unnecessary
    *     computation and loss of accuracy.  The supplementary quantities
    *     are (i) alpha, which is proportional to the total energy of the
    *     orbit, (ii) the heliocentric distance at epoch, (iii) the
    *     outwards component of the velocity at the given epoch, (iv) an
    *     estimate of psi, the "universal eccentric anomaly" at a given
    *     date and (v) that date.
    *
    *  2  The companion routine is sla_UE2PV.  This takes the set of numbers
    *     that the present routine outputs and uses them to derive the
    *     object's position and velocity.  A single prediction requires one
    *     call to the present routine followed by one call to sla_UE2PV;
    *     for convenience, the two calls are packaged as the routine
    *     sla_PLANEL.  Multiple predictions may be made by again calling the
    *     present routine once, but then calling sla_UE2PV multiple times,
    *     which is faster than multiple calls to sla_PLANEL.
    *
    *  3  DATE is the epoch of osculation.  It is in the TT timescale
    *     (formerly Ephemeris Time, ET) and is a Modified Julian Date
    *     (JD-2400000.5).
    *
    *  4  The supplied orbital elements are with respect to the J2000
    *     ecliptic and equinox.  The position and velocity parameters
    *     returned in the array U are with respect to the mean equator and
    *     equinox of epoch J2000, and are for the perihelion prior to the
    *     specified epoch.
    *
    *  5  The universal elements returned in the array U are in canonical
    *     units (solar masses, AU and canonical days).
    *
    *  6  Three different element-format options are available:
    *
    *     Option JFORM=1, suitable for the major planets:
    *
    *     EPOCH  = epoch of elements (TT MJD)
    *     ORBINC = inclination i (radians)
    *     ANODE  = longitude of the ascending node, big omega (radians)
    *     PERIH  = longitude of perihelion, curly pi (radians)
    *     AORQ   = mean distance, a (AU)
    *     E      = eccentricity, e (range 0 to <1)
    *     AORL   = mean longitude L (radians)
    *     DM     = daily motion (radians)
    *
    *     Option JFORM=2, suitable for minor planets:
    *
    *     EPOCH  = epoch of elements (TT MJD)
    *     ORBINC = inclination i (radians)
    *     ANODE  = longitude of the ascending node, big omega (radians)
    *     PERIH  = argument of perihelion, little omega (radians)
    *     AORQ   = mean distance, a (AU)
    *     E      = eccentricity, e (range 0 to <1)
    *     AORL   = mean anomaly M (radians)
    *
    *     Option JFORM=3, suitable for comets:
    *
    *     EPOCH  = epoch of perihelion (TT MJD)
    *     ORBINC = inclination i (radians)
    *     ANODE  = longitude of the ascending node, big omega (radians)
    *     PERIH  = argument of perihelion, little omega (radians)
    *     AORQ   = perihelion distance, q (AU)
    *     E      = eccentricity, e (range 0 to 10)
    *
    *  7  Unused elements (DM for JFORM=2, AORL and DM for JFORM=3) are
    *     not accessed.
    *
    *  8  The algorithm was originally adapted from the EPHSLA program of
    *     D.H.P.Jones (private communication, 1996).  The method is based
    *     on Stumpff's Universal Variables.
    *
    *  Reference:  Everhart & Pitkin, Am.J.Phys. 51, 712 (1983).
    *
    *  Last revision:   8 September 2005
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let U = new Array();
    let JSTAT;

    // Gaussian gravitational constant (exact)
    let GCON=0.01720209895;

    //  Sin and cos of J2000 mean obliquity (IAU 1976)
    let SE=0.3977771559319137,
        CE=0.9174820620691818;

    let PHT,ARGPH,Q,W,CM,ALPHA,PHS,SW,CW,SI,CI,SO,CO,
        X,Y,Z,PX,PY,PZ,VX,VY,VZ,DT,FC,FP,PSI;
        
    let UL = new Array();
    let PV = new Array();

    //  Validate arguments.
    if(JFORM < 1 || JFORM > 3) {
        JSTAT = -1;
        return [U, JSTAT];
    }
    if(E < 0.0 || E > 10.0 || (E >= 1.0 && JFORM != 3) ) {
        JSTAT = -2;
        return [U, JSTAT];
    }
    if(AORQ <= 0.0) {
        JSTAT = -3;
        return [U, JSTAT];
    }
    if(JFORM == 1.0 && DM <= 0.0) {
        JSTAT = -4;
        return [U, JSTAT];
    }

    /*
    *  Transform elements into standard form:
    *
    *  PHT   = epoch of perihelion passage
    *  ARGPH = argument of perihelion (little omega)
    *  Q     = perihelion distance (q)
    *  CM    = combined mass, M+m (mu)*/

    if(JFORM == 1) {

        //  Major planet.
        PHT = EPOCH-(AORL-PERIH)/DM;
        ARGPH = PERIH-ANODE;
        Q = AORQ*(1.0-E);
        W = DM/GCON;
        CM = W*W*AORQ*AORQ*AORQ;
    }
    else if(JFORM == 2) {

        //  Minor planet.
        PHT = EPOCH-AORL*SQRT(AORQ*AORQ*AORQ)/GCON;
        ARGPH = PERIH;
        Q = AORQ*(1.0-E);
        CM = 1.0;
    }
    else {
        //  Comet.
        PHT = EPOCH;
        ARGPH = PERIH;
        Q = AORQ;
        CM = 1.0;
    }

    /*  The universal variable alpha.  This is proportional to the total
    *  energy of the orbit:  -ve for an ellipse, zero for a parabola,
    *  +ve for a hyperbola.*/

    ALPHA = CM*(E-1.0)/Q;

    //  Speed at perihelion.

    PHS = SQRT(ALPHA+2.0*CM/Q);

    /*  In a Cartesian coordinate system which has the x-axis pointing
    *  to perihelion and the z-axis normal to the orbit (such that the
    *  object orbits counter-clockwise as seen from +ve z), the
    *  perihelion position and velocity vectors are:
    *
    *    position   [Q,0,0]
    *    velocity   [0,PHS,0]
    *
    *  To express the results in J2000 equatorial coordinates we make a
    *  series of four rotations of the Cartesian axes:
    *
    *           axis      Euler angle
    *
    *     1      z        argument of perihelion (little omega)
    *     2      x        inclination (i)
    *     3      z        longitude of the ascending node (big omega)
    *     4      x        J2000 obliquity (epsilon)
    *
    *  In each case the rotation is clockwise as seen from the +ve end of
    *  the axis concerned.*/

    //  Functions of the Euler angles.
    SW = SIN(ARGPH);
    CW = COS(ARGPH);
    SI = SIN(ORBINC);
    CI = COS(ORBINC);
    SO = SIN(ANODE);
    CO = COS(ANODE);
    


    //  Position at perihelion (AU).
    X = Q*CW;
    Y = Q*SW;
    Z = Y*SI;
    Y = Y*CI;
    PX = X*CO-Y*SO;
    Y = X*SO+Y*CO;
    PY = Y*CE-Z*SE;
    PZ = Y*SE+Z*CE;

    //  Velocity at perihelion (AU per canonical day).
    X = -PHS*SW;
    Y = PHS*CW;
    Z = Y*SI;
    Y = Y*CI;
    VX = X*CO-Y*SO;
    Y = X*SO+Y*CO;
    VY = Y*CE-Z*SE;
    VZ = Y*SE+Z*CE;

    //  Time from perihelion to date (in Canonical Days: a canonical day
    //  is 58.1324409... days, defined as 1/GCON).

    DT = (DATE-PHT)*GCON;

    //  First approximation to the Universal Eccentric Anomaly, PSI,
    //  based on the circle (FC) and parabola (FP) values.

    FC = DT/Q;
    W = Math.pow((3.0*DT+SQRT(9.0*DT*DT+8.0*Q*Q*Q)),(1.0/3.0))
    FP = W-2.0*Q/W;
    PSI = (1.0-E)*FC+E*FP;

    //  Assemble local copy of element set.
    UL[0] = CM;
    UL[1] = ALPHA;
    UL[2] = PHT;
    UL[3] = PX;
    UL[4] = PY;
    UL[5] = PZ;
    UL[6] = VX;
    UL[7] = VY;
    UL[8] = VZ;
    UL[9] = Q;
    UL[10] = 0.0;
    UL[11] = DATE;
    UL[12] = PSI;

    //  Predict position+velocity at epoch of osculation.
    let result;
    result  = sla_ue2pv(DATE,UL);
    UL = result[0];
    PV = result[1];
    let J = result[2];
    
    if(J != 0) {
        JSTAT = -5;
        return [U, JSTAT];
    }

    //  Convert back to universal elements.
    result = sla_pv2ue(PV,DATE,CM-1.0);
    U = result[0];
    J = result[1];
    
    if(J != 0) {
        JSTAT = -5;
        return [U, JSTAT];
    }
    
    JSTAT = 0;
    return [U, JSTAT];
}

export function sla_pv2ue(PV, DATE, PMASS) {
    /*
    *     - - - - - -
    *      P V 2 U E
    *     - - - - - -
    *
    *  Construct a universal element set based on an instantaneous position
    *  and velocity.
    *
    *  Given:
    *     PV        d(6)   heliocentric x,y,z,xdot,ydot,zdot of date,
    *                      (AU,AU/s; Note 1)
    *     DATE      d      date (TT Modified Julian Date = JD-2400000.5)
    *     PMASS     d      mass of the planet (Sun=1; Note 2)
    *
    *  Returned:
    *     U         d(13)  universal orbital elements (Note 3)
    *
    *                 (1)  combined mass (M+m)
    *                 (2)  total energy of the orbit (alpha)
    *                 (3)  reference (osculating) epoch (t0)
    *               (4-6)  position at reference epoch (r0)
    *               (7-9)  velocity at reference epoch (v0)
    *                (10)  heliocentric distance at reference epoch
    *                (11)  r0.v0
    *                (12)  date (t)
    *                (13)  universal eccentric anomaly (psi) of date, approx
    *
    *     JSTAT     i      status:  0 = OK
    *                              -1 = illegal PMASS
    *                              -2 = too close to Sun
    *                              -3 = too slow
    *
    *  Notes
    *
    *  1  The PV 6-vector can be with respect to any chosen inertial frame,
    *     and the resulting universal-element set will be with respect to
    *     the same frame.  A common choice will be mean equator and ecliptic
    *     of epoch J2000.
    *
    *  2  The mass, PMASS, is important only for the larger planets.  For
    *     most purposes (e.g. asteroids) use 0D0.  Values less than zero
    *     are illegal.
    *
    *  3  The "universal" elements are those which define the orbit for the
    *     purposes of the method of universal variables (see reference).
    *     They consist of the combined mass of the two bodies, an epoch,
    *     and the position and velocity vectors (arbitrary reference frame)
    *     at that epoch.  The parameter set used here includes also various
    *     quantities that can, in fact, be derived from the other
    *     information.  This approach is taken to avoiding unnecessary
    *     computation and loss of accuracy.  The supplementary quantities
    *     are (i) alpha, which is proportional to the total energy of the
    *     orbit, (ii) the heliocentric distance at epoch, (iii) the
    *     outwards component of the velocity at the given epoch, (iv) an
    *     estimate of psi, the "universal eccentric anomaly" at a given
    *     date and (v) that date.
    *
    *  Reference:  Everhart, E. & Pitkin, E.T., Am.J.Phys. 51, 712, 1983.
    *
    *  P.T.Wallace   Starlink   18 March 1999
    *
    *  Copyright (C) 1999 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let U = new Array();
    let JSTAT;

    //  Gaussian gravitational constant (exact)
    let GCON=0.01720209895;

    //  Canonical days to seconds
    let CD2S=GCON/86400.0;

    //  Minimum allowed distance (AU) and speed (AU per canonical day)
    let RMIN=1e-3;
    let VMIN=1e-3;

    let T0,CM,X,Y,Z,XD,YD,ZD,R,V2,V,ALPHA,RDV;


    //  Reference epoch.
    T0 = DATE;

    //  Combined mass (mu=M+m).
    if(PMASS < 0.0) {
        JSTAT = -1
        return [U, JSTAT];
    }
    
    CM = 1.0+PMASS;

    //  Unpack the state vector, expressing velocity in AU per canonical day.
    X = PV[0];
    Y = PV[1];
    Z = PV[2];
    XD = PV[3]/CD2S;
    YD = PV[4]/CD2S;
    ZD = PV[5]/CD2S;
    

    //  Heliocentric distance, and speed.
    R = SQRT(X*X+Y*Y+Z*Z);
    V2 = XD*XD+YD*YD+ZD*ZD;
    V = SQRT(V2);
    

    //  Reject unreasonably small values.
    if(R < RMIN) {
        JSTAT = -2
        return [U, JSTAT];
    }
    if(V < VMIN) {
        JSTAT = -3
        return [U, JSTAT];
    }

    //  Total energy of the orbit.
    ALPHA = V2-2.0*CM/R;

    //  Outward component of velocity.
    RDV = X*XD+Y*YD+Z*ZD;

    //  Construct the universal-element set.
    U[0] = CM;
    U[1] = ALPHA;
    U[2] = T0;
    U[3] = X;
    U[4] = Y;
    U[5] = Z;
    U[6] = XD;
    U[7] = YD;
    U[8] = ZD;
    U[9] = R;
    U[10] = RDV;
    U[11] = T0;
    U[12] = 0.0;

    JSTAT = 0
    return [U, JSTAT];

}

export function sla_ue2pv( DATE, U) {
    /*
    *     - - - - - -
    *      U E 2 P V
    *     - - - - - -
    *
    *  Heliocentric position and velocity of a planet, asteroid or comet,
    *  starting from orbital elements in the "universal variables" form.
    *
    *  Given:
    *     DATE     d       date, Modified Julian Date (JD-2400000.5)
    *
    *  Given and returned:
    *     U        d(13)   universal orbital elements (updated; Note 1)
    *
    *       given    (1)   combined mass (M+m)
    *         "      (2)   total energy of the orbit (alpha)
    *         "      (3)   reference (osculating) epoch (t0)
    *         "    (4-6)   position at reference epoch (r0)
    *         "    (7-9)   velocity at reference epoch (v0)
    *         "     (10)   heliocentric distance at reference epoch
    *         "     (11)   r0.v0
    *     returned  (12)   date (t)
    *         "     (13)   universal eccentric anomaly (psi) of date
    *
    *  Returned:
    *     PV       d(6)    position (AU) and velocity (AU/s)
    *     JSTAT    i       status:  0 = OK
    *                              -1 = radius vector zero
    *                              -2 = failed to converge
    *
    *  Notes
    *
    *  1  The "universal" elements are those which define the orbit for the
    *     purposes of the method of universal variables (see reference).
    *     They consist of the combined mass of the two bodies, an epoch,
    *     and the position and velocity vectors (arbitrary reference frame)
    *     at that epoch.  The parameter set used here includes also various
    *     quantities that can, in fact, be derived from the other
    *     information.  This approach is taken to avoiding unnecessary
    *     computation and loss of accuracy.  The supplementary quantities
    *     are (i) alpha, which is proportional to the total energy of the
    *     orbit, (ii) the heliocentric distance at epoch, (iii) the
    *     outwards component of the velocity at the given epoch, (iv) an
    *     estimate of psi, the "universal eccentric anomaly" at a given
    *     date and (v) that date.
    *
    *  2  The companion routine is sla_EL2UE.  This takes the conventional
    *     orbital elements and transforms them into the set of numbers
    *     needed by the present routine.  A single prediction requires one
    *     one call to sla_EL2UE followed by one call to the present routine;
    *     for convenience, the two calls are packaged as the routine
    *     sla_PLANEL.  Multiple predictions may be made by again
    *     calling sla_EL2UE once, but then calling the present routine
    *     multiple times, which is faster than multiple calls to sla_PLANEL.
    *
    *     It is not obligatory to use sla_EL2UE to obtain the parameters.
    *     However, it should be noted that because sla_EL2UE performs its
    *     own validation, no checks on the contents of the array U are made
    *     by the present routine.
    *
    *  3  DATE is the instant for which the prediction is required.  It is
    *     in the TT timescale (formerly Ephemeris Time, ET) and is a
    *     Modified Julian Date (JD-2400000.5).
    *
    *  4  The universal elements supplied in the array U are in canonical
    *     units (solar masses, AU and canonical days).  The position and
    *     velocity are not sensitive to the choice of reference frame.  The
    *     sla_EL2UE routine in fact produces coordinates with respect to the
    *     J2000 equator and equinox.
    *
    *  5  The algorithm was originally adapted from the EPHSLA program of
    *     D.H.P.Jones (private communication, 1996).  The method is based
    *     on Stumpff's Universal Variables.
    *
    *  Reference:  Everhart, E. & Pitkin, E.T., Am.J.Phys. 51, 712, 1983.
    *
    *  P.T.Wallace   Starlink   22 October 2005
    *
    *  Copyright (C) 2005 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */


    let PV = new Array(6);
    //let PV = [];

    
    
    let JSTAT;

    //  Gaussian gravitational constant (exact)
    let GCON=0.01720209895;

    //  Canonical days to seconds
    let CD2S=GCON/86400.0;

    //  Test value for solution and maximum number of iterations
    let TEST = 1e-13;
    let NITMAX = 25;

    let NIT,N;

    let CM,ALPHA,T0,R0,SIGMA0,T,PSI,DT,W,
        TOL,PSJ,PSJ2,BETA,S0,S1,S2,S3,
        FF,R,FLAST,PLAST,F,G,FD,GD;
        
    let P0 = new Array();
    let V0 = new Array();

    //Unpack the parameters.
    CM = U[0];
    ALPHA = U[1];
    T0 = U[2];
    for(let i=0; i<3; i++) {
        P0[i] = U[i+3];
        V0[i] = U[i+6];
    }
    R0 = U[9];
    SIGMA0 = U[10];
    T = U[11];
    PSI = U[12];
    
    
    

    //  Approximately update the universal eccentric anomaly.
    PSI = PSI+(DATE-T)*GCON/R0;

    //  Time from reference epoch to date (in Canonical Days: a canonical
    //  day is 58.1324409... days, defined as 1/GCON).
    DT = (DATE-T0)*GCON;

    //  Refine the universal eccentric anomaly, psi.
    NIT = 1;
    W = 1.0;
    TOL = 0.0;
    while(ABS(W) >= TOL) {
    //     Form half angles until BETA small enough.
        N = 0;
        PSJ = PSI;
        PSJ2 = PSJ*PSJ;
        BETA = ALPHA*PSJ2;
        while( ABS(BETA) > 0.7 ) {
            N = N+1;
            BETA = BETA/4.0;
            PSJ = PSJ/2.0;
            PSJ2 = PSJ2/4.0;
        }

    //     Calculate Universal Variables S0,S1,S2,S3 by nested series.
        S3 = PSJ*PSJ2*((((((BETA/210.0+1.0)*BETA/156.0+1.0)*BETA/110.0+1.0)*BETA/72.0+1.0)*BETA/42.0+1.0)*BETA/20.0+1.0)/6.0;
        S2 = PSJ2*((((((BETA/182.0+1.0)*BETA/132.0+1.0)*BETA/90.0+1.0)*BETA/56.0+1.0)*BETA/30.0+1.0)*BETA/12.0+1.0)/2.0;
        S1 = PSJ+ALPHA*S3;
        S0 = 1.0+ALPHA*S2;

    //     Undo the angle-halving.
        TOL = TEST
        while(N > 0) {
            S3 = 2.0*(S0*S3+PSJ*S2);
            S2 = 2.0*S1*S1;
            S1 = 2.0*S0*S1;
            S0 = 2.0*S0*S0-1.0;
            PSJ = PSJ+PSJ;
            TOL = TOL+TOL;
            N = N-1;
        }

        //  Values of F and F' corresponding to the current value of psi.
        FF = R0*S1+SIGMA0*S2+CM*S3-DT;
        R = R0*S0+SIGMA0*S1+CM*S2;

        //  If first iteration, create dummy "last F".
        if(NIT == 1) {FLAST = FF;}

        //  Check for sign change.
        if(FF*FLAST < 0.0) {
            // Sign change:  get psi adjustment using secant method.
            W = FF*(PLAST-PSI)/(FLAST-FF);
        }
        else {
            //No sign change:  use Newton-Raphson method instead.
            if(R == 0.0) {
                JSTAT = -1
                return [U, PV, JSTAT];
            }
            W = FF/R;
        }

        //  Save the last psi and F values.
        PLAST = PSI;
        FLAST = FF;

        //  Apply the Newton-Raphson or secant adjustment to psi.
        PSI = PSI-W;

        // Next iteration, unless too many already.
        if(NIT > NITMAX) {
            JSTAT = -2
            return [U, PV, JSTAT];
        }
        
        NIT = NIT+1;
    }

    //  Project the position and velocity vectors (scaling velocity to AU/s).
    W = CM*S2;
    F = 1.0-W/R0;
    G = DT-CM*S3;
    FD = -CM*S1/(R0*R);
    GD = 1.0-W/R;
    
    
    
    //console.log(W, F, G, FD, GD);
    
    //console.log("BEFORE:", PV);
    for(let i=0; i<3; i++) {
        //console.log("P",i,": ", P0[i]*F+V0[i]*G);
        //console.log("P",i+3,": ", CD2S*(P0[i]*FD+V0[i]*GD));
        PV[i] = P0[i]*F+V0[i]*G;
        PV[i+3] = CD2S*(P0[i]*FD+V0[i]*GD);
    }


    //  Update the parameters to allow speedy prediction of PSI next time.
    U[11] = DATE;
    U[12] = PSI;

    JSTAT = 0
    return [U, PV, JSTAT]
}

export function sla_dmxm(A, B) {
    /*
    *     - - - - -
    *      D M X M
    *     - - - - -
    *
    *  Product of two 3x3 matrices:
    *
    *      matrix C  =  matrix A  x  matrix B
    *
    *  (double precision)
    *
    *  Given:
    *      A      dp(3,3)        matrix
    *      B      dp(3,3)        matrix
    *
    *  Returned:
    *      C      dp(3,3)        matrix result
    *
    *  To comply with the ANSI Fortran 77 standard, A, B and C must
    *  be different arrays.  However, the routine is coded so as to
    *  work properly on many platforms even if this rule is violated.
    *
    *  Last revision:   26 December 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let C = new Array();
    let WM = new Array();
    for(let i=0; i<3; i++) {
        C[i] = new Array();
        WM[i] = new Array();
    }
    
    let W;

    //  Multiply into scratch matrix
    for(let i=0; i<3; i++) {
        for(let j=0; j<3; j++) {
            W=0.0;
            for(let k=0; k<3; k++) {
                W=W+A[i][k]*B[k][j];
            }
            WM[i][j]=W;
        }
    }

    //  Return the result
    for(let j=0; j<3; j++) {
        for(let i=0; i<3; i++) {
            C[i][j]=WM[i][j];
        }
    }

   return C;
}

export function sla_prec(EP0, EP1) {
    /*
    *     - - - - -
    *      P R E C
    *     - - - - -
    *
    *  Form the matrix of precession between two epochs (IAU 1976, FK5)
    *  (double precision)
    *
    *  Given:
    *     EP0    dp         beginning epoch
    *     EP1    dp         ending epoch
    *
    *  Returned:
    *     RMATP  dp(3,3)    precession matrix
    *
    *  Notes:
    *
    *     1)  The epochs are TDB (loosely ET) Julian epochs.
    *
    *     2)  The matrix is in the sense   V(EP1)  =  RMATP * V(EP0)
    *
    *     3)  Though the matrix method itself is rigorous, the precession
    *         angles are expressed through canonical polynomials which are
    *         valid only for a limited time span.  There are also known
    *         errors in the IAU precession rate.  The absolute accuracy
    *         of the present formulation is better than 0.1 arcsec from
    *         1960AD to 2040AD, better than 1 arcsec from 1640AD to 2360AD,
    *         and remains below 3 arcsec for the whole of the period
    *         500BC to 3000AD.  The errors exceed 10 arcsec outside the
    *         range 1200BC to 3900AD, exceed 100 arcsec outside 4200BC to
    *         5600AD and exceed 1000 arcsec outside 6800BC to 8200AD.
    *         The SLALIB routine sla_PRECL implements a more elaborate
    *         model which is suitable for problems spanning several
    *         thousand years.
    *
    *  References:
    *     Lieske,J.H., 1979. Astron.Astrophys.,73,282.
    *      equations (6) & (7), p283.
    *     Kaplan,G.H., 1981. USNO circular no. 163, pA2.
    *
    *  Called:  sla_DEULER
    *
    *  P.T.Wallace   Starlink   23 August 1996
    *
    *  Copyright (C) 1996 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    //  Arc seconds to radians
    let AS2R=0.484813681109535994e-5;
    let T0,T,TAS2R,W,ZETA,Z,THETA;

    //  Interval between basic epoch J2000.0 and beginning epoch (JC)
    T0 = (EP0-2000.0)/100.0;

    //  Interval over which precession required (JC)
    T = (EP1-EP0)/100.0;

    //  Euler angles
    TAS2R = T*AS2R;
    W = 2306.2181+(1.39656-0.000139*T0)*T0;

    ZETA = (W+((0.30188-0.000344*T0)+0.017998*T)*T)*TAS2R;
    Z = (W+((1.09468+0.000066*T0)+0.018203*T)*T)*TAS2R;
    THETA = ((2004.3109+(-0.85330-0.000217*T0)*T0)+((-0.42665-0.000217*T0)-0.041833*T)*T)*TAS2R;

    //  Rotation matrix
    let RMATP = sla_deuler('ZYZ',-ZETA,THETA,-Z);
    
    return RMATP;
}


export function sla_epj(DATE) {
    /*
    *     - - - -
    *      E P J
    *     - - - -
    *
    *  Conversion of Modified Julian Date to Julian Epoch (double precision)
    *
    *  Given:
    *     DATE     dp       Modified Julian Date (JD - 2400000.5)
    *
    *  The result is the Julian Epoch.
    *
    *  Reference:
    *     Lieske,J.H., 1979. Astron.Astrophys.,73,282.
    *
    *  P.T.Wallace   Starlink   February 1984
    *
    *  Copyright (C) 1995 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    return 2000.0 + (DATE-51544.5)/365.25;
}

export function sla_dranrm(ANGLE) {
    /*
    *     - - - - - - -
    *      D R A N R M
    *     - - - - - - -
    *
    *  Normalize angle into range 0-2 pi  (double precision)
    *
    *  Given:
    *     ANGLE     dp      the angle in radians
    *
    *  The result is ANGLE expressed in the range 0-2 pi.
    *
    *  Last revision:   22 July 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let D2PI=6.283185307179586476925286766559;

    let result = MOD(ANGLE,D2PI)
    if(result < 0.0) {result = result+D2PI;}
    
    return result;
}

export function sla_prenut(EPOCH, DATE) {
    /*
    *     - - - - - - -
    *      P R E N U T
    *     - - - - - - -
    *
    *  Form the matrix of precession and nutation (SF2001)
    *  (double precision)
    *
    *  Given:
    *     EPOCH   dp         Julian Epoch for mean coordinates
    *     DATE    dp         Modified Julian Date (JD-2400000.5)
    *                        for true coordinates
    *
    *  Returned:
    *     RMATPN  dp(3,3)    combined precession/nutation matrix
    *
    *  Called:  sla_PREC, sla_EPJ, sla_NUT, sla_DMXM
    *
    *  Notes:
    *
    *  1)  The epoch and date are TDB (loosely ET).  TT will do, or even
    *      UTC.
    *
    *  2)  The matrix is in the sense   V(true) = RMATPN * V(mean)
    *
    *  Last revision:   3 December 2005
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    


    //  Precession
    let RMATP = sla_prec(EPOCH,sla_epj(DATE));

    //  Nutation
    let RMATN = sla_nut(DATE);

    //  Combine the matrices:  PN = N x P
    return sla_dmxm(RMATN,RMATP);
}

export function sla_dcc2s(V) {
    /*
    *     - - - - - -
    *      D C C 2 S
    *     - - - - - -
    *
    *  Cartesian to spherical coordinates (double precision)
    *
    *  Given:
    *     V     d(3)   x,y,z vector
    *
    *  Returned:
    *     A,B   d      spherical coordinates in radians
    *
    *  The spherical coordinates are longitude (+ve anticlockwise looking
    *  from the +ve latitude pole) and latitude.  The Cartesian coordinates
    *  are right handed, with the x axis at zero longitude and latitude, and
    *  the z axis at the +ve latitude pole.
    *
    *  If V is null, zero A and B are returned.  At either pole, zero A is
    *  returned.
    *
    *  Last revision:   22 July 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let A,B;
    let X,Y,Z,R;


    X = V[0];
    Y = V[1];
    Z = V[2];
    R = SQRT(X*X+Y*Y);

    if(R==0.0) {
        A = 0.0;
    }
    else {
        A = ATAN2(Y,X);
    }
    
    if(Z==0.0) {
        B = 0.0;
    }
    else {
        B = ATAN2(Z,R);
    }

    return [A,B];
}

export function sla_geoc(P, H) {
    /*
    *     - - - - -
    *      G E O C
    *     - - - - -
    *
    *  Convert geodetic position to geocentric (double precision)
    *
    *  Given:
    *     P     dp     latitude (geodetic, radians)
    *     H     dp     height above reference spheroid (geodetic, metres)
    *
    *  Returned:
    *     R     dp     distance from Earth axis (AU)
    *     Z     dp     distance from plane of Earth equator (AU)
    *
    *  Notes:
    *
    *  1  Geocentric latitude can be obtained by evaluating ATAN2(Z,R).
    *
    *  2  IAU 1976 constants are used.
    *
    *  Reference:
    *
    *     Green,R.M., Spherical Astronomy, CUP 1985, p98.
    *
    *  Last revision:   22 July 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let R,Z;

    let A0=6378140.0;

    let F=1.0/298.257,B=Math.pow((1.0-F),2.0);

    //  Astronomical unit in metres
    let AU=1.49597870e11;

    let SP,CP,C,S;



    //  Geodetic to geocentric conversion
    SP = SIN(P);
    CP = COS(P);
    C = 1.0/SQRT(CP*CP+B*SP*SP);
    S = B*C;
    R = (A0*C+H)*CP/AU;
    Z = (A0*S+H)*SP/AU;

    return [R, Z];
}

export function sla_pvobs(P, H, STL) {
    /*
    *     - - - - - -
    *      P V O B S
    *     - - - - - -
    *
    *  Position and velocity of an observing station (double precision)
    *
    *  Given:
    *     P     dp     latitude (geodetic, radians)
    *     H     dp     height above reference spheroid (geodetic, metres)
    *     STL   dp     local apparent sidereal time (radians)
    *
    *  Returned:
    *     PV    dp(6)  position/velocity 6-vector (AU, AU/s, true equator
    *                                              and equinox of date)
    *
    *  Called:  sla_GEOC
    *
    *  IAU 1976 constants are used.
    *
    *  P.T.Wallace   Starlink   14 November 1994
    *
    *  Copyright (C) 1995 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let PV = new Array();

    let R,Z,S,C,V;

    let SR=7.292115855306589e-5;



    //  Geodetic to geocentric conversion
    let result = sla_geoc(P,H)
    R = result[0];
    Z = result[1];

    //  Functions of ST
    S=SIN(STL);
    C=COS(STL);

    //  Speed
    V=SR*R;

    //  Position
    PV[0]=R*C;
    PV[1]=R*S;
    PV[2]=Z;

    //  Velocity
    PV[3]=-V*S;
    PV[4]=V*C;
    PV[5]=0.0;

    return PV;
}

export function sla_dmxv(DM, VA) {
    /*
    *     - - - - -
    *      D M X V
    *     - - - - -
    *
    *  Performs the 3-D forward unitary transformation:
    *
    *     vector VB = matrix DM * vector VA
    *
    *  (double precision)
    *
    *  Given:
    *     DM       dp(3,3)    matrix
    *     VA       dp(3)      vector
    *
    *  Returned:
    *     VB       dp(3)      result vector
    *
    *  To comply with the ANSI Fortran 77 standard, VA and VB must be
    *  different arrays.  However, the routine is coded so as to work
    *  properly on many platforms even if this rule is violated.
    *
    *  Last revision:   26 December 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let VW = new Array();
    let VB = new Array();
    let W;

    //  Matrix DM * vector VA -> vector VW
    for(let j=0; j<3; j++) {
        W=0.0;
        for(let i=0; i<3; i++) {
            W=W+DM[j][i]*VA[i];
        }
        VW[j]=W;
    }

    //  Vector VW -> vector VB
    for(let j=0; j<3; j++) {
        VB[j]=VW[j];
    }
    
    return VB;
    
    
}

export function sla_deuler(ORDER, PHI, THETA, PSI) {
    /*
    *     - - - - - - -
    *      D E U L E R
    *     - - - - - - -
    *
    *  Form a rotation matrix from the Euler angles - three successive
    *  rotations about specified Cartesian axes (double precision)
    *
    *  Given:
    *    ORDER   c*(*)   specifies about which axes the rotations occur
    *    PHI     d       1st rotation (radians)
    *    THETA   d       2nd rotation (   "   )
    *    PSI     d       3rd rotation (   "   )
    *
    *  Returned:
    *    RMAT    d(3,3)  rotation matrix
    *
    *  A rotation is positive when the reference frame rotates
    *  anticlockwise as seen looking towards the origin from the
    *  positive region of the specified axis.
    *
    *  The characters of ORDER define which axes the three successive
    *  rotations are about.  A typical value is 'ZXZ', indicating that
    *  RMAT is to become the direction cosine matrix corresponding to
    *  rotations of the reference frame through PHI radians about the
    *  old Z-axis, followed by THETA radians about the resulting X-axis,
    *  then PSI radians about the resulting Z-axis.
    *
    *  The axis names can be any of the following, in any order or
    *  combination:  X, Y, Z, uppercase or lowercase, 1, 2, 3.  Normal
    *  axis labelling/numbering conventions apply;  the xyz (=123)
    *  triad is right-handed.  Thus, the 'ZXZ' example given above
    *  could be written 'zxz' or '313' (or even 'ZxZ' or '3xZ').  ORDER
    *  is terminated by length or by the first unrecognized character.
    *
    *  Fewer than three rotations are acceptable, in which case the later
    *  angle arguments are ignored.  If all rotations are zero, the
    *  identity matrix is produced.
    *
    *  P.T.Wallace   Starlink   23 May 1997
    *
    *  Copyright (C) 1997 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */


    let RMAT = new Array();
    let RESULT = new Array();
    let ROTN = new Array();
    let WM = new Array();
    for(let i=0; i<3; i++) {
        RMAT[i] = new Array();
        RESULT[i] = new Array();
        ROTN[i] = new Array();
        WM[i] = new Array();
    }
    
    let ANGLE,S,C,W;


    //  Initialize result matrix
    for(let j=0; j<3; j++) {
        for(let i=0; i<3; i++) {
            if(i != j) {
                RESULT[i][j] = 0.0;
            }
            else {
                RESULT[i][j] = 1.0;
            }
        }
    }
    

    //  Establish length of axis string
    let L = ORDER.length;

    //  Look at each character of axis string until finished
    for(let n=0; n<3; n++) {
        if(n < L) {

            //  Initialize rotation matrix for the current rotation
            for(let j=0; j<3; j++) {
               for(let i=0; i<3; i++) {
                  if(i!=j) {
                     ROTN[i][j] = 0.0;
                  }
                  else {
                     ROTN[i][j] = 1.0;
                  }
               }
            }

            //  Pick up the appropriate Euler angle and take sine & cosine
            if(n==0) {
                ANGLE = PHI;
            }
            else if(n==1) {       
                ANGLE = THETA;
            }
            else {
                ANGLE = PSI;
            }
            S = SIN(ANGLE);
            C = COS(ANGLE);

            //  Identify the axis
            let AXIS = ORDER[n];
            if(AXIS=='X' || AXIS=='x' || AXIS=='1') {
                //  Matrix for x-rotation
                ROTN[1][1] = C;
                ROTN[1][2] = S;
                ROTN[2][1] = -S;
                ROTN[2][2] = C;
            }
            else if(AXIS=='Y' || AXIS=='y' || AXIS=='2') {
                //  Matrix for y-rotation
                ROTN[0][0] = C
                ROTN[0][2] = -S
                ROTN[2][0] = S
                ROTN[2][2] = C
            }
            else if(AXIS=='Z' || AXIS=='z' || AXIS=='3') {
                //  Matrix for z-rotation
                ROTN[0][0] = C
                ROTN[0][1] = S
                ROTN[1][0] = -S
                ROTN[1][1] = C

            }
            else {
                //  Unrecognized character - fake end of string
                L = -1;
            }

            //  Apply the current rotation (matrix ROTN x matrix RESULT)
            for(let i=0; i<3; i++) {
                for(let j=0; j<3; j++) {
                    W = 0.0;
                    for(let k=0; k<3; k++) {
                        W = W+ROTN[i][k]*RESULT[k][j];
                    }
                    WM[i][j] = W;
                }
            }
            
            for(let j=0; j<3; j++) {
                for(let i=0; i<3; i++) {
                    RESULT[i][j] = WM[i][j];
                }
            }
        }
    }
    
    // Copy the result
    for(let j=0; j<3; j++) {
        for(let i=0; i<3; i++) {
            RMAT[i][j] = RESULT[i][j];
        }
    }

    return RMAT;
}

export function sla_nutc(mjd) {
    /*
    *     - - - - -
    *      N U T C
    *     - - - - -
    *
    *  Nutation:  longitude & obliquity components and mean obliquity,
    *  using the Shirai & Fukushima (2001) theory.
    *
    *  Given:
    *     DATE        d    TDB (loosely ET) as Modified Julian Date
    *                                            (JD-2400000.5)
    *  Returned:
    *     DPSI,DEPS   d    nutation in longitude,obliquity
    *     EPS0        d    mean obliquity
    *
    *  Notes:
    *
    *  1  The routine predicts forced nutation (but not free core nutation)
    *     plus corrections to the IAU 1976 precession model.
    *
    *  2  Earth attitude predictions made by combining the present nutation
    *     model with IAU 1976 precession are accurate to 1 mas (with respect
    *     to the ICRF) for a few decades around 2000.
    *
    *  3  The sla_NUTC80 routine is the equivalent of the present routine
    *     but using the IAU 1980 nutation theory.  The older theory is less
    *     accurate, leading to errors as large as 350 mas over the interval
    *     1900-2100, mainly because of the error in the IAU 1976 precession.
    *
    *  References:
    *
    *     Shirai, T. & Fukushima, T., Astron.J. 121, 3270-3283 (2001).
    *
    *     Fukushima, T., Astron.Astrophys. 244, L11 (1991).
    *
    *     Simon, J. L., Bretagnon, P., Chapront, J., Chapront-Touze, M.,
    *     Francou, G. & Laskar, J., Astron.Astrophys. 282, 663 (1994).
    *
    *  This revision:   24 November 2005
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */


    //  Degrees to radians
    let DD2R=1.745329251994329576923691e-2;

    //  Arc seconds to radians
    let DAS2R=4.848136811095359935899141e-6;

    //  Arc seconds in a full circle
    let TURNAS=1296000;

    //  Reference epoch (J2000), MJD
    let DJM0=51544.5;

    //  Days per Julian century
    let DJC=36525;

    // let I,J;
    let T,EL,ELP,F,D,OM,VE,MA,JU,SA,THETA,C,S,DP,DE;

    //  Number of terms in the nutation model
    // let NTERMS=194;

    //  The SF2001 forced nutation model
    
    //  Coefficients of fundamental angles
    let NA = [
               [0,   0,   0,   0,  -1,   0,   0,   0,   0],
               [0,   0,   2,  -2,   2,   0,   0,   0,   0],
               [0,   0,   2,   0,   2,   0,   0,   0,   0],
               [0,   0,   0,   0,  -2,   0,   0,   0,   0],
               [0,   1,   0,   0,   0,   0,   0,   0,   0],
               [0,   1,   2,  -2,   2,   0,   0,   0,   0],
               [1,   0,   0,   0,   0,   0,   0,   0,   0],
               [0,   0,   2,   0,   1,   0,   0,   0,   0],
               [1,   0,   2,   0,   2,   0,   0,   0,   0],
               [0,  -1,   2,  -2,   2,   0,   0,   0,   0],
               [0,   0,   2,  -2,   1,   0,   0,   0,   0],
               [1,   0,   2,   0,   2,   0,   0,   0,   0],
               [1,   0,   0,   2,   0,   0,   0,   0,   0],
               [1,   0,   0,   0,   1,   0,   0,   0,   0],
               [1,   0,   0,   0,  -1,   0,   0,   0,   0],
               [1,   0,   2,   2,   2,   0,   0,   0,   0],
               [1,   0,   2,   0,   1,   0,   0,   0,   0],
               [2,   0,   2,   0,   1,   0,   0,   0,   0],
               [0,   0,   0,   2,   0,   0,   0,   0,   0],
               [0,   0,   2,   2,   2,   0,   0,   0,   0],
               [2,   0,   0,  -2,   0,   0,   0,   0,   0],
               [2,   0,   2,   0,   2,   0,   0,   0,   0],
               [1,   0,   2,  -2,   2,   0,   0,   0,   0],
               [1,   0,   2,   0,   1,   0,   0,   0,   0],
               [2,   0,   0,   0,   0,   0,   0,   0,   0],
               [0,   0,   2,   0,   0,   0,   0,   0,   0],
               [0,   1,   0,   0,   1,   0,   0,   0,   0],
               [1,   0,   0,   2,   1,   0,   0,   0,   0],
               [0,   2,   2,  -2,   2,   0,   0,   0,   0],
               [0,   0,   2,  -2,   0,   0,   0,   0,   0],
               [1,   0,   0,   2,  -1,   0,   0,   0,   0],
               [0,   1,   0,   0,  -1,   0,   0,   0,   0],
               [0,   2,   0,   0,   0,   0,   0,   0,   0],
               [1,   0,   2,   2,   1,   0,   0,   0,   0],
               [1,   0,   2,   2,   2,   0,   0,   0,   0],
               [0,   1,   2,   0,   2,   0,   0,   0,   0],
               [2,   0,   2,   0,   0,   0,   0,   0,   0],
               [0,   0,   2,   2,   1,   0,   0,   0,   0],
               [0,  -1,   2,   0,   2,   0,   0,   0,   0],
               [0,   0,   0,   2,   1,   0,   0,   0,   0],
               [1,   0,   2,  -2,   1,   0,   0,   0,   0],
               [2,   0,   0,  -2,  -1,   0,   0,   0,   0],
               [2,   0,   2,  -2,   2,   0,   0,   0,   0],
               [2,   0,   2,   0,   1,   0,   0,   0,   0],
               [0,   0,   0,   2,  -1,   0,   0,   0,   0],
               [0,  -1,   2,  -2,   1,   0,   0,   0,   0],
               [1,  -1,   0,   2,   0,   0,   0,   0,   0],
               [2,   0,   0,  -2,   1,   0,   0,   0,   0],
               [1,   0,   0,   2,   0,   0,   0,   0,   0],
               [0,   1,   2,  -2,   1,   0,   0,   0,   0],
               [1,  -1,   0,   0,   0,   0,   0,   0,   0],
               [2,   0,   2,   0,   2,   0,   0,   0,   0],
               [0,  -1,   0,   2,   0,   0,   0,   0,   0],
               [3,   0,   2,   0,   2,   0,   0,   0,   0],
               [0,   0,   0,   1,   0,   0,   0,   0,   0],
               [1,  -1,   2,   0,   2,   0,   0,   0,   0],
               [1,   0,   0,  -1,   0,   0,   0,   0,   0],
               [1,  -1,   2,   2,   2,   0,   0,   0,   0],
               [1,   0,   2,   0,   0,   0,   0,   0,   0],
               [2,   0,   0,   0,  -1,   0,   0,   0,   0],
               [0,  -1,   2,   2,   2,   0,   0,   0,   0],
               [1,   1,   2,   0,   2,   0,   0,   0,   0],
               [2,   0,   0,   0,   1,   0,   0,   0,   0],
               [1,   1,   0,   0,   0,   0,   0,   0,   0],
               [1,   0,  -2,   2,  -1,   0,   0,   0,   0],
               [1,   0,   2,   0,   0,   0,   0,   0,   0],
               [1,   1,   0,   1,   0,   0,   0,   0,   0],
               [1,   0,   0,   0,   2,   0,   0,   0,   0],
               [1,   0,   1,   0,   1,   0,   0,   0,   0],
               [0,   0,   2,   1,   2,   0,   0,   0,   0],
               [1,   1,   0,   1,   1,   0,   0,   0,   0],
               [1,   0,   2,   4,   2,   0,   0,   0,   0],
               [0,  -2,   2,  -2,   1,   0,   0,   0,   0],
               [1,   0,   2,   2,   1,   0,   0,   0,   0],
               [1,   0,   0,   0,  -2,   0,   0,   0,   0],
               [2,   0,   2,   2,   2,   0,   0,   0,   0],
               [1,   1,   2,  -2,   2,   0,   0,   0,   0],
               [2,   0,   2,   4,   2,   0,   0,   0,   0],
               [1,   0,   4,   0,   2,   0,   0,   0,   0],
               [2,   0,   2,  -2,   1,   0,   0,   0,   0],
               [1,   0,   0,  -1,  -1,   0,   0,   0,   0],
               [2,   0,   2,   2,   2,   0,   0,   0,   0],
               [1,   0,   0,   2,   1,   0,   0,   0,   0],
               [3,   0,   0,   0,   0,   0,   0,   0,   0],
               [0,   0,   2,  -2,  -1,   0,   0,   0,   0],
               [3,   0,   2,  -2,   2,   0,   0,   0,   0],
               [0,   0,   4,  -2,   2,   0,   0,   0,   0],
               [1,   0,   0,   4,   0,   0,   0,   0,   0],
               [0,   1,   2,   0,   1,   0,   0,   0,   0],
               [0,   0,   2,  -2,   3,   0,   0,   0,   0],
               [2,   0,   0,   4,   0,   0,   0,   0,   0],
               [1,  -1,   0,   2,   1,   0,   0,   0,   0],
               [2,   0,   2,   0,  -1,   0,   0,   0,   0],
               [0,   0,   2,   0,  -1,   0,   0,   0,   0],
               [0,  -1,   2,   0,   1,   0,   0,   0,   0],
               [0,   1,   0,   0,   2,   0,   0,   0,   0],
               [0,   0,   2,  -1,   2,   0,   0,   0,   0],
               [2,   1,   0,  -2,   0,   0,   0,   0,   0],
               [0,   0,   2,   4,   2,   0,   0,   0,   0],
               [1,  -1,   0,   2,  -1,   0,   0,   0,   0],
               [1,   1,   0,   2,   0,   0,   0,   0,   0],
               [1,  -1,   0,   0,   1,   0,   0,   0,   0],
               [0,  -1,   2,  -2,   0,   0,   0,   0,   0],
               [0,   1,   0,   0,  -2,   0,   0,   0,   0],
               [1,  -1,   2,   2,   2,   0,   0,   0,   0],
               [1,   0,   0,   2,  -1,   0,   0,   0,   0],
               [1,   1,   2,   2,   2,   0,   0,   0,   0],
               [3,   0,   2,   0,   1,   0,   0,   0,   0],
               [0,   1,   2,   2,   2,   0,   0,   0,   0],
               [1,   0,   2,  -2,   0,   0,   0,   0,   0],
               [1,   0,  -2,   4,  -1,   0,   0,   0,   0],
               [1,  -1,   2,   2,   1,   0,   0,   0,   0],
               [0,  -1,   2,   2,   1,   0,   0,   0,   0],
               [2,  -1,   2,   0,   2,   0,   0,   0,   0],
               [0,   0,   0,   2,   2,   0,   0,   0,   0],
               [1,  -1,   2,   0,   1,   0,   0,   0,   0],
               [1,   1,   2,   0,   2,   0,   0,   0,   0],
               [0,   1,   0,   2,   0,   0,   0,   0,   0],
               [0,   1,   2,  -2,   0,   0,   0,   0,   0],
               [0,   3,   2,  -2,   2,   0,   0,   0,   0],
               [0,   0,   0,   1,   1,   0,   0,   0,   0],
               [1,   0,   2,   2,   0,   0,   0,   0,   0],
               [2,   1,   2,   0,   2,   0,   0,   0,   0],
               [1,   1,   0,   0,   1,   0,   0,   0,   0],
               [2,   0,   0,   2,   0,   0,   0,   0,   0],
               [1,   1,   2,   0,   1,   0,   0,   0,   0],
               [1,   0,   0,   2,   2,   0,   0,   0,   0],
               [1,   0,  -2,   2,   0,   0,   0,   0,   0],
               [0,  -1,   0,   2,  -1,   0,   0,   0,   0],
               [1,   0,   1,   0,   2,   0,   0,   0,   0],
               [0,   1,   0,   1,   0,   0,   0,   0,   0],
               [1,   0,  -2,   2,  -2,   0,   0,   0,   0],
               [0,   0,   0,   1,  -1,   0,   0,   0,   0],
               [1,  -1,   0,   0,  -1,   0,   0,   0,   0],
               [0,   0,   0,   4,   0,   0,   0,   0,   0],
               [1,  -1,   0,   2,   0,   0,   0,   0,   0],
               [1,   0,   2,   1,   2,   0,   0,   0,   0],
               [1,   0,   2,  -1,   2,   0,   0,   0,   0],
               [1,   0,   0,   2,  -2,   0,   0,   0,   0],
               [0,   0,   2,   1,   1,   0,   0,   0,   0],
               [1,   0,   2,   0,  -1,   0,   0,   0,   0],
               [1,   0,   2,   4,   1,   0,   0,   0,   0],
               [0,   0,   2,   2,   0,   0,   0,   0,   0],
               [1,   1,   2,  -2,   1,   0,   0,   0,   0],
               [0,   0,   1,   0,   1,   0,   0,   0,   0],
               [1,   0,   2,  -1,   1,   0,   0,   0,   0],
               [2,   0,   2,   2,   1,   0,   0,   0,   0],
               [2,  -1,   0,   0,   0,   0,   0,   0,   0],
               [4,   0,   2,   0,   2,   0,   0,   0,   0],
               [2,   1,   2,  -2,   2,   0,   0,   0,   0],
               [0,   1,   2,   1,   2,   0,   0,   0,   0],
               [1,   0,   4,  -2,   2,   0,   0,   0,   0],
               [1,   1,   0,   0,  -1,   0,   0,   0,   0],
               [2,   0,   2,   4,   1,   0,   0,   0,   0],
               [2,   0,   2,   0,   0,   0,   0,   0,   0],
               [1,   0,   1,   0,   0,   0,   0,   0,   0],
               [1,   0,   0,   1,   0,   0,   0,   0,   0],
               [0,   1,   0,   2,   1,   0,   0,   0,   0],
               [1,   0,   4,   0,   1,   0,   0,   0,   0],
               [1,   0,   0,   4,   1,   0,   0,   0,   0],
               [2,   0,   2,   2,   1,   0,   0,   0,   0],
               [2,   1,   0,   0,   0,   0,   0,   0,   0],
               [0,   0,   5,  -5,   5,  -3,   0,   0,   0],
               [0,   0,   0,   0,   0,   0,   0,   2,   0],
               [0,   0,   1,  -1,   1,   0,   0,  -1,   0],
               [0,   0,  -1,   1,  -1,   1,   0,   0,   0],
               [0,   0,  -1,   1,   0,   0,   2,   0,   0],
               [0,   0,   3,  -3,   3,   0,   0,  -1,   0],
               [0,   0,  -8,   8,  -7,   5,   0,   0,   0],
               [0,   0,  -1,   1,  -1,   0,   2,   0,   0],
               [0,   0,  -2,   2,  -2,   2,   0,   0,   0],
               [0,   0,  -6,   6,  -6,   4,   0,   0,   0],
               [0,   0,  -2,   2,  -2,   0,   8,  -3,   0],
               [0,   0,   6,  -6,   6,   0,  -8,   3,   0],
               [0,   0,   4,  -4,   4,  -2,   0,   0,   0],
               [0,   0,  -3,   3,  -3,   2,   0,   0,   0],
               [0,   0,   4,  -4,   3,   0,  -8,   3,   0],
               [0,   0,  -4,   4,  -5,   0,   8,  -3,   0],
               [0,   0,   0,   0,   0,   2,   0,   0,   0],
               [0,   0,  -4,   4,  -4,   3,   0,   0,   0],
               [0,   1,  -1,   1,  -1,   0,   0,   1,   0],
               [0,   0,   0,   0,   0,   0,   0,   1,   0],
               [0,   0,   1,  -1,   1,   1,   0,   0,   0],
               [0,   0,   2,  -2,   2,   0,  -2,   0,   0],
               [0,  -1,  -7,   7,  -7,   5,   0,   0,   0],
               [2,   0,   2,   0,   2,   0,   0,  -2,   0],
               [2,   0,   2,   0,   1,   0,   0,  -3,   0],
               [0,   0,   2,  -2,   2,   0,   0,  -2,   0],
               [0,   0,   1,  -1,   1,   0,   0,   1,   0],
               [0,   0,   0,   0,   0,   0,   0,   0,   2],
               [0,   0,   0,   0,   0,   0,   0,   0,   1],
               [2,   0,  -2,   0,  -2,   0,   0,   3,   0],
               [0,   0,   1,  -1,   1,   0,   0,  -2,   0],
               [0,   0,  -7,   7,  -7,   5,   0,   0,   0]];

    
    //  Nutation series: longitude
    let PSI = [
                [  3341.5, 17206241.8,  3.1, 17409.5],
                [ -1716.8, -1317185.3,  1.4,  -156.8],
                [   285.7,  -227667.0,  0.3,   -23.5],
                [   -68.6,  -207448.0,  0.0,   -21.4],
                [   950.3,   147607.9, -2.3,  -355.0],
                [   -66.7,   -51689.1,  0.2,   122.6],
                [  -108.6,    71117.6,  0.0,     7.0],
                [    35.6,   -38740.2,  0.1,   -36.2],
                [    85.4,   -30127.6,  0.0,    -3.1],
                [     9.0,    21583.0,  0.1,   -50.3],
                [    22.1,    12822.8,  0.0,    13.3],
                [     3.4,    12350.8,  0.0,     1.3],
                [   -21.1,    15699.4,  0.0,     1.6],
                [     4.2,     6313.8,  0.0,     6.2],
                [   -22.8,     5796.9,  0.0,     6.1],
                [    15.7,    -5961.1,  0.0,    -0.6],
                [    13.1,    -5159.1,  0.0,    -4.6],
                [     1.8,     4592.7,  0.0,     4.5],
                [   -17.5,     6336.0,  0.0,     0.7],
                [    16.3,    -3851.1,  0.0,    -0.4],
                [    -2.8,     4771.7,  0.0,     0.5],
                [    13.8,    -3099.3,  0.0,    -0.3],
                [     0.2,     2860.3,  0.0,     0.3],
                [     1.4,     2045.3,  0.0,     2.0],
                [    -8.6,     2922.6,  0.0,     0.3],
                [    -7.7,     2587.9,  0.0,     0.2],
                [     8.8,    -1408.1,  0.0,     3.7],
                [     1.4,     1517.5,  0.0,     1.5],
                [    -1.9,    -1579.7,  0.0,     7.7],
                [     1.3,    -2178.6,  0.0,    -0.2],
                [    -4.8,     1286.8,  0.0,     1.3],
                [     6.3,     1267.2,  0.0,    -4.0],
                [    -1.0,     1669.3,  0.0,    -8.3],
                [     2.4,    -1020.0,  0.0,    -0.9],
                [     4.5,     -766.9,  0.0,     0.0],
                [    -1.1,      756.5,  0.0,    -1.7],
                [    -1.4,    -1097.3,  0.0,    -0.5],
                [     2.6,     -663.0,  0.0,    -0.6],
                [     0.8,     -714.1,  0.0,     1.6],
                [     0.4,     -629.9,  0.0,    -0.6],
                [     0.3,      580.4,  0.0,     0.6],
                [    -1.6,      577.3,  0.0,     0.5],
                [    -0.9,      644.4,  0.0,     0.0],
                [     2.2,     -534.0,  0.0,    -0.5],
                [    -2.5,      493.3,  0.0,     0.5],
                [    -0.1,     -477.3,  0.0,    -2.4],
                [    -0.9,      735.0,  0.0,    -1.7],
                [     0.7,      406.2,  0.0,     0.4],
                [    -2.8,      656.9,  0.0,     0.0],
                [     0.6,      358.0,  0.0,     2.0],
                [    -0.7,      472.5,  0.0,    -1.1],
                [    -0.1,     -300.5,  0.0,     0.0],
                [    -1.2,      435.1,  0.0,    -1.0],
                [     1.8,     -289.4,  0.0,     0.0],
                [     0.6,     -422.6,  0.0,     0.0],
                [     0.8,     -287.6,  0.0,     0.6],
                [   -38.6,     -392.3,  0.0,     0.0],
                [     0.7,     -281.8,  0.0,     0.6],
                [     0.6,     -405.7,  0.0,     0.0],
                [    -1.2,      229.0,  0.0,     0.2],
                [     1.1,     -264.3,  0.0,     0.5],
                [    -0.7,      247.9,  0.0,    -0.5],
                [    -0.2,      218.0,  0.0,     0.2],
                [     0.6,     -339.0,  0.0,     0.8],
                [    -0.7,      198.7,  0.0,     0.2],
                [    -1.5,      334.0,  0.0,     0.0],
                [     0.1,      334.0,  0.0,     0.0],
                [    -0.1,     -198.1,  0.0,     0.0],
                [  -106.6,        0.0,  0.0,     0.0],
                [    -0.5,      165.8,  0.0,     0.0],
                [     0.0,      134.8,  0.0,     0.0],
                [     0.9,     -151.6,  0.0,     0.0],
                [     0.0,     -129.7,  0.0,     0.0],
                [     0.8,     -132.8,  0.0,    -0.1],
                [     0.5,     -140.7,  0.0,     0.0],
                [    -0.1,      138.4,  0.0,     0.0],
                [     0.0,      129.0,  0.0,    -0.3],
                [     0.5,     -121.2,  0.0,     0.0],
                [    -0.3,      114.5,  0.0,     0.0],
                [    -0.1,      101.8,  0.0,     0.0],
                [    -3.6,     -101.9,  0.0,     0.0],
                [     0.8,     -109.4,  0.0,     0.0],
                [     0.2,      -97.0,  0.0,     0.0],
                [    -0.7,      157.3,  0.0,     0.0],
                [     0.2,      -83.3,  0.0,     0.0],
                [    -0.3,       93.3,  0.0,     0.0],
                [    -0.1,       92.1,  0.0,     0.0],
                [    -0.5,      133.6,  0.0,     0.0],
                [    -0.1,       81.5,  0.0,     0.0],
                [     0.0,      123.9,  0.0,     0.0],
                [    -0.3,      128.1,  0.0,     0.0],
                [     0.1,       74.1,  0.0,    -0.3],
                [    -0.2,      -70.3,  0.0,     0.0],
                [    -0.4,       66.6,  0.0,     0.0],
                [     0.1,      -66.7,  0.0,     0.0],
                [    -0.7,       69.3,  0.0,    -0.3],
                [     0.0,      -70.4,  0.0,     0.0],
                [    -0.1,      101.5,  0.0,     0.0],
                [     0.5,      -69.1,  0.0,     0.0],
                [    -0.2,       58.5,  0.0,     0.2],
                [     0.1,      -94.9,  0.0,     0.2],
                [     0.0,       52.9,  0.0,    -0.2],
                [     0.1,       86.7,  0.0,    -0.2],
                [    -0.1,      -59.2,  0.0,     0.2],
                [     0.3,      -58.8,  0.0,     0.1],
                [    -0.3,       49.0,  0.0,     0.0],
                [    -0.2,       56.9,  0.0,    -0.1],
                [     0.3,      -50.2,  0.0,     0.0],
                [    -0.2,       53.4,  0.0,    -0.1],
                [     0.1,      -76.5,  0.0,     0.0],
                [    -0.2,       45.3,  0.0,     0.0],
                [     0.1,      -46.8,  0.0,     0.0],
                [     0.2,      -44.6,  0.0,     0.0],
                [     0.2,      -48.7,  0.0,     0.0],
                [     0.1,      -46.8,  0.0,     0.0],
                [     0.1,      -42.0,  0.0,     0.0],
                [     0.0,       46.4,  0.0,    -0.1],
                [     0.2,      -67.3,  0.0,     0.1],
                [     0.0,      -65.8,  0.0,     0.2],
                [    -0.1,      -43.9,  0.0,     0.3],
                [     0.0,      -38.9,  0.0,     0.0],
                [    -0.3,       63.9,  0.0,     0.0],
                [    -0.2,       41.2,  0.0,     0.0],
                [     0.0,      -36.1,  0.0,     0.2],
                [    -0.3,       58.5,  0.0,     0.0],
                [    -0.1,       36.1,  0.0,     0.0],
                [     0.0,      -39.7,  0.0,     0.0],
                [     0.1,      -57.7,  0.0,     0.0],
                [    -0.2,       33.4,  0.0,     0.0],
                [    36.4,        0.0,  0.0,     0.0],
                [    -0.1,       55.7,  0.0,    -0.1],
                [     0.1,      -35.4,  0.0,     0.0],
                [     0.1,      -31.0,  0.0,     0.0],
                [    -0.1,       30.1,  0.0,     0.0],
                [    -0.3,       49.2,  0.0,     0.0],
                [    -0.2,       49.1,  0.0,     0.0],
                [    -0.1,       33.6,  0.0,     0.0],
                [     0.1,      -33.5,  0.0,     0.0],
                [     0.1,      -31.0,  0.0,     0.0],
                [    -0.1,       28.0,  0.0,     0.0],
                [     0.1,      -25.2,  0.0,     0.0],
                [     0.1,      -26.2,  0.0,     0.0],
                [    -0.2,       41.5,  0.0,     0.0],
                [     0.0,       24.5,  0.0,     0.1],
                [   -16.2,        0.0,  0.0,     0.0],
                [     0.0,      -22.3,  0.0,     0.0],
                [     0.0,       23.1,  0.0,     0.0],
                [    -0.1,       37.5,  0.0,     0.0],
                [     0.2,      -25.7,  0.0,     0.0],
                [     0.0,       25.2,  0.0,     0.0],
                [     0.1,      -24.5,  0.0,     0.0],
                [    -0.1,       24.3,  0.0,     0.0],
                [     0.1,      -20.7,  0.0,     0.0],
                [     0.1,      -20.8,  0.0,     0.0],
                [    -0.2,       33.4,  0.0,     0.0],
                [    32.9,        0.0,  0.0,     0.0],
                [     0.1,      -32.6,  0.0,     0.0],
                [     0.0,       19.9,  0.0,     0.0],
                [    -0.1,       19.6,  0.0,     0.0],
                [     0.0,      -18.7,  0.0,     0.0],
                [     0.1,      -19.0,  0.0,     0.0],
                [     0.1,      -28.6,  0.0,     0.0],
                [     4.0,      178.8,-11.8,     0.3],
                [    39.8,     -107.3, -5.6,    -1.0],
                [     9.9,      164.0, -4.1,     0.1],
                [    -4.8,     -135.3, -3.4,    -0.1],
                [    50.5,       75.0,  1.4,    -1.2],
                [    -1.1,      -53.5,  1.3,     0.0],
                [   -45.0,       -2.4, -0.4,     6.6],
                [   -11.5,      -61.0, -0.9,     0.4],
                [     4.4,      -68.4, -3.4,     0.0],
                [     7.7,      -47.1, -4.7,    -1.0],
                [   -42.9,      -12.6, -1.2,     4.2],
                [   -42.8,       12.7, -1.2,    -4.2],
                [    -7.6,      -44.1,  2.1,    -0.5],
                [   -64.1,        1.7,  0.2,     4.5],
                [    36.4,      -10.4,  1.0,     3.5],
                [    35.6,       10.2,  1.0,    -3.5],
                [    -1.7,       39.5,  2.0,     0.0],
                [    50.9,       -8.2, -0.8,    -5.0],
                [     0.0,       52.3,  1.2,     0.0],
                [   -42.9,      -17.8,  0.4,     0.0],
                [     2.6,       34.3,  0.8,     0.0],
                [    -0.8,      -48.6,  2.4,    -0.1],
                [    -4.9,       30.5,  3.7,     0.7],
                [     0.0,      -43.6,  2.1,     0.0],
                [     0.0,      -25.4,  1.2,     0.0],
                [     2.0,       40.9, -2.0,     0.0],
                [    -2.1,       26.1,  0.6,     0.0],
                [    22.6,       -3.2, -0.5,    -0.5],
                [    -7.6,       24.9, -0.4,    -0.2],
                [    -6.2,       34.9,  1.7,     0.3],
                [     2.0,       17.4, -0.4,     0.1],
                [    -3.9,       20.5,  2.4,     0.6]];

    
    //  Nutation series: obliquity
    let EPS = [
                [ 9205365.8, -1506.2,  885.7, -0.2],
                [  573095.9,  -570.2, -305.0, -0.3],
                [   97845.5,   147.8,  -48.8, -0.2],
                [  -89753.6,    28.0,   46.9,  0.0],
                [    7406.7,  -327.1,  -18.2,  0.8],
                [   22442.3,   -22.3,  -67.6,  0.0],
                [    -683.6,    46.8,    0.0,  0.0],
                [   20070.7,    36.0,    1.6,  0.0],
                [   12893.8,    39.5,   -6.2,  0.0],
                [   -9593.2,    14.4,   30.2, -0.1],
                [   -6899.5,     4.8,   -0.6,  0.0],
                [   -5332.5,    -0.1,    2.7,  0.0],
                [    -125.2,    10.5,    0.0,  0.0],
                [   -3323.4,    -0.9,   -0.3,  0.0],
                [    3142.3,     8.9,    0.3,  0.0],
                [    2552.5,     7.3,   -1.2,  0.0],
                [    2634.4,     8.8,    0.2,  0.0],
                [   -2424.4,     1.6,   -0.4,  0.0],
                [    -123.3,     3.9,    0.0,  0.0],
                [    1642.4,     7.3,   -0.8,  0.0],
                [      47.9,     3.2,    0.0,  0.0],
                [    1321.2,     6.2,   -0.6,  0.0],
                [   -1234.1,    -0.3,    0.6,  0.0],
                [   -1076.5,    -0.3,    0.0,  0.0],
                [     -61.6,     1.8,    0.0,  0.0],
                [     -55.4,     1.6,    0.0,  0.0],
                [     856.9,    -4.9,   -2.1,  0.0],
                [    -800.7,    -0.1,    0.0,  0.0],
                [     685.1,    -0.6,   -3.8,  0.0],
                [     -16.9,    -1.5,    0.0,  0.0],
                [     695.7,     1.8,    0.0,  0.0],
                [     642.2,    -2.6,   -1.6,  0.0],
                [      13.3,     1.1,   -0.1,  0.0],
                [     521.9,     1.6,    0.0,  0.0],
                [     325.8,     2.0,   -0.1,  0.0],
                [    -325.1,    -0.5,    0.9,  0.0],
                [      10.1,     0.3,    0.0,  0.0],
                [     334.5,     1.6,    0.0,  0.0],
                [     307.1,     0.4,   -0.9,  0.0],
                [     327.2,     0.5,    0.0,  0.0],
                [    -304.6,    -0.1,    0.0,  0.0],
                [     304.0,     0.6,    0.0,  0.0],
                [    -276.8,    -0.5,    0.1,  0.0],
                [     268.9,     1.3,    0.0,  0.0],
                [     271.8,     1.1,    0.0,  0.0],
                [     271.5,    -0.4,   -0.8,  0.0],
                [      -5.2,     0.5,    0.0,  0.0],
                [    -220.5,     0.1,    0.0,  0.0],
                [     -20.1,     0.3,    0.0,  0.0],
                [    -191.0,     0.1,    0.5,  0.0],
                [      -4.1,     0.3,    0.0,  0.0],
                [     130.6,    -0.1,    0.0,  0.0],
                [       3.0,     0.3,    0.0,  0.0],
                [     122.9,     0.8,    0.0,  0.0],
                [       3.7,    -0.3,    0.0,  0.0],
                [     123.1,     0.4,   -0.3,  0.0],
                [     -52.7,    15.3,    0.0,  0.0],
                [     120.7,     0.3,   -0.3,  0.0],
                [       4.0,    -0.3,    0.0,  0.0],
                [     126.5,     0.5,    0.0,  0.0],
                [     112.7,     0.5,   -0.3,  0.0],
                [    -106.1,    -0.3,    0.3,  0.0],
                [    -112.9,    -0.2,    0.0,  0.0],
                [       3.6,    -0.2,    0.0,  0.0],
                [     107.4,     0.3,    0.0,  0.0],
                [     -10.9,     0.2,    0.0,  0.0],
                [      -0.9,     0.0,    0.0,  0.0],
                [      85.4,     0.0,    0.0,  0.0],
                [       0.0,   -88.8,    0.0,  0.0],
                [     -71.0,    -0.2,    0.0,  0.0],
                [     -70.3,     0.0,    0.0,  0.0],
                [      64.5,     0.4,    0.0,  0.0],
                [      69.8,     0.0,    0.0,  0.0],
                [      66.1,     0.4,    0.0,  0.0],
                [     -61.0,    -0.2,    0.0,  0.0],
                [     -59.5,    -0.1,    0.0,  0.0],
                [     -55.6,     0.0,    0.2,  0.0],
                [      51.7,     0.2,    0.0,  0.0],
                [     -49.0,    -0.1,    0.0,  0.0],
                [     -52.7,    -0.1,    0.0,  0.0],
                [     -49.6,     1.4,    0.0,  0.0],
                [      46.3,     0.4,    0.0,  0.0],
                [      49.6,     0.1,    0.0,  0.0],
                [      -5.1,     0.1,    0.0,  0.0],
                [     -44.0,    -0.1,    0.0,  0.0],
                [     -39.9,    -0.1,    0.0,  0.0],
                [     -39.5,    -0.1,    0.0,  0.0],
                [      -3.9,     0.1,    0.0,  0.0],
                [     -42.1,    -0.1,    0.0,  0.0],
                [     -17.2,     0.1,    0.0,  0.0],
                [      -2.3,     0.1,    0.0,  0.0],
                [     -39.2,     0.0,    0.0,  0.0],
                [     -38.4,     0.1,    0.0,  0.0],
                [      36.8,     0.2,    0.0,  0.0],
                [      34.6,     0.1,    0.0,  0.0],
                [     -32.7,     0.3,    0.0,  0.0],
                [      30.4,     0.0,    0.0,  0.0],
                [       0.4,     0.1,    0.0,  0.0],
                [      29.3,     0.2,    0.0,  0.0],
                [      31.6,     0.1,    0.0,  0.0],
                [       0.8,    -0.1,    0.0,  0.0],
                [     -27.9,     0.0,    0.0,  0.0],
                [       2.9,     0.0,    0.0,  0.0],
                [     -25.3,     0.0,    0.0,  0.0],
                [      25.0,     0.1,    0.0,  0.0],
                [      27.5,     0.1,    0.0,  0.0],
                [     -24.4,    -0.1,    0.0,  0.0],
                [      24.9,     0.2,    0.0,  0.0],
                [     -22.8,    -0.1,    0.0,  0.0],
                [       0.9,    -0.1,    0.0,  0.0],
                [      24.4,     0.1,    0.0,  0.0],
                [      23.9,     0.1,    0.0,  0.0],
                [      22.5,     0.1,    0.0,  0.0],
                [      20.8,     0.1,    0.0,  0.0],
                [      20.1,     0.0,    0.0,  0.0],
                [      21.5,     0.1,    0.0,  0.0],
                [     -20.0,     0.0,    0.0,  0.0],
                [       1.4,     0.0,    0.0,  0.0],
                [      -0.2,    -0.1,    0.0,  0.0],
                [      19.0,     0.0,   -0.1,  0.0],
                [      20.5,     0.0,    0.0,  0.0],
                [      -2.0,     0.0,    0.0,  0.0],
                [     -17.6,    -0.1,    0.0,  0.0],
                [      19.0,     0.0,    0.0,  0.0],
                [      -2.4,     0.0,    0.0,  0.0],
                [     -18.4,    -0.1,    0.0,  0.0],
                [      17.1,     0.0,    0.0,  0.0],
                [       0.4,     0.0,    0.0,  0.0],
                [      18.4,     0.1,    0.0,  0.0],
                [       0.0,    17.4,    0.0,  0.0],
                [      -0.6,     0.0,    0.0,  0.0],
                [     -15.4,     0.0,    0.0,  0.0],
                [     -16.8,    -0.1,    0.0,  0.0],
                [      16.3,     0.0,    0.0,  0.0],
                [      -2.0,     0.0,    0.0,  0.0],
                [      -1.5,     0.0,    0.0,  0.0],
                [     -14.3,    -0.1,    0.0,  0.0],
                [      14.4,     0.0,    0.0,  0.0],
                [     -13.4,     0.0,    0.0,  0.0],
                [     -14.3,    -0.1,    0.0,  0.0],
                [     -13.7,     0.0,    0.0,  0.0],
                [      13.1,     0.1,    0.0,  0.0],
                [      -1.7,     0.0,    0.0,  0.0],
                [     -12.8,     0.0,    0.0,  0.0],
                [       0.0,   -14.4,    0.0,  0.0],
                [      12.4,     0.0,    0.0,  0.0],
                [     -12.0,     0.0,    0.0,  0.0],
                [      -0.8,     0.0,    0.0,  0.0],
                [      10.9,     0.1,    0.0,  0.0],
                [     -10.8,     0.0,    0.0,  0.0],
                [      10.5,     0.0,    0.0,  0.0],
                [     -10.4,     0.0,    0.0,  0.0],
                [     -11.2,     0.0,    0.0,  0.0],
                [      10.5,     0.1,    0.0,  0.0],
                [      -1.4,     0.0,    0.0,  0.0],
                [       0.0,     0.1,    0.0,  0.0],
                [       0.7,     0.0,    0.0,  0.0],
                [     -10.3,     0.0,    0.0,  0.0],
                [     -10.0,     0.0,    0.0,  0.0],
                [       9.6,     0.0,    0.0,  0.0],
                [       9.4,     0.1,    0.0,  0.0],
                [       0.6,     0.0,    0.0,  0.0],
                [     -87.7,     4.4,   -0.4, -6.3],
                [      46.3,    22.4,    0.5, -2.4],
                [      15.6,    -3.4,    0.1,  0.4],
                [       5.2,     5.8,    0.2, -0.1],
                [     -30.1,    26.9,    0.7,  0.0],
                [      23.2,    -0.5,    0.0,  0.6],
                [       1.0,    23.2,    3.4,  0.0],
                [     -12.2,    -4.3,    0.0,  0.0],
                [      -2.1,    -3.7,   -0.2,  0.1],
                [     -18.6,    -3.8,   -0.4,  1.8],
                [       5.5,   -18.7,   -1.8, -0.5],
                [      -5.5,   -18.7,    1.8, -0.5],
                [      18.4,    -3.6,    0.3,  0.9],
                [      -0.6,     1.3,    0.0,  0.0],
                [      -5.6,   -19.5,    1.9,  0.0],
                [       5.5,   -19.1,   -1.9,  0.0],
                [     -17.3,    -0.8,    0.0,  0.9],
                [      -3.2,    -8.3,   -0.8,  0.3],
                [      -0.1,     0.0,    0.0,  0.0],
                [      -5.4,     7.8,   -0.3,  0.0],
                [     -14.8,     1.4,    0.0,  0.3],
                [      -3.8,     0.4,    0.0, -0.2],
                [      12.6,     3.2,    0.5, -1.5],
                [       0.1,     0.0,    0.0,  0.0],
                [     -13.6,     2.4,   -0.1,  0.0],
                [       0.9,     1.2,    0.0,  0.0],
                [     -11.9,    -0.5,    0.0,  0.3],
                [       0.4,    12.0,    0.3, -0.2],
                [       8.3,     6.1,   -0.1,  0.1],
                [       0.0,     0.0,    0.0,  0.0],
                [       0.4,   -10.8,    0.3,  0.0],
                [       9.6,     2.2,    0.3, -1.2]];



    //  Interval between fundamental epoch J2000.0 and given epoch (JC).
    T = (mjd-DJM0)/DJC;

    //  Mean anomaly of the Moon.
    EL  = 134.96340251*DD2R+MOD(T*(1717915923.2178+T*(31.8792+T*(0.051635+T*(-0.00024470)))),TURNAS)*DAS2R;

    //  Mean anomaly of the Sun.
    ELP = 357.52910918*DD2R+MOD(T*(129596581.0481+T*(-0.5532+T*(0.000136+T*(-0.00001149)))),TURNAS)*DAS2R;

    //  Mean argument of the latitude of the Moon.
    F   =  93.27209062*DD2R+MOD(T*(1739527262.8478+T*(-12.7512+T*(-0.001037+T*(0.00000417)))),TURNAS)*DAS2R;

    //  Mean elongation of the Moon from the Sun.
    D   = 297.85019547*DD2R+MOD(T*(1602961601.2090+T*(-6.3706+T*(0.006539+T*(-0.00003169)))),TURNAS)*DAS2R;

    //  Mean longitude of the ascending node of the Moon.
    OM  = 125.04455501*DD2R+MOD(T*(-6962890.5431+T*(7.4722+T*(0.007702+T*(-0.00005939)))),TURNAS)*DAS2R;

    //  Mean longitude of Venus.
    VE = 181.97980085*DD2R+MOD(210664136.433548*T,TURNAS)*DAS2R;

    //  Mean longitude of Mars.
    MA    = 355.43299958*DD2R+MOD( 68905077.493988*T,TURNAS)*DAS2R;

    //  Mean longitude of Jupiter.
    JU    =  34.35151874*DD2R+MOD( 10925660.377991*T,TURNAS)*DAS2R;

    //  Mean longitude of Saturn.
    SA    =  50.07744430*DD2R+MOD(  4399609.855732*T,TURNAS)*DAS2R;

    //  Geodesic nutation (Fukushima 1991) in microarcsec.
    DP = -153.1*SIN(ELP)-1.9*SIN(2*ELP);
    DE = 0;
    
        

    //  Shirai & Fukushima (2001) nutation series.
    for(let i=0; i<NA.length; i=i+1) {
        THETA = NA[i][0]*EL+
                NA[i][1]*ELP+
                NA[i][2]*F+  
                NA[i][3]*D+  
                NA[i][4]*OM+ 
                NA[i][5]*VE+ 
                NA[i][6]*MA+ 
                NA[i][7]*JU+ 
                NA[i][8]*SA;
        C = COS(THETA);
        S = SIN(THETA);
        DP = DP+(PSI[i][0]+PSI[i][2]*T)*C+(PSI[i][1]+PSI[i][3]*T)*S;
        DE = DE+(EPS[i][0]+EPS[i][2]*T)*C+(EPS[i][1]+EPS[i][3]*T)*S;
    }

    //  Change of units, and addition of the precession correction.
    let DPSI = (DP * 1.0e-6 - 0.042888 - 0.29856 * T)*DAS2R;
    let DEPS = (DE * 1.0e-6 - 0.005171 - 0.02408 * T)*DAS2R;

    //  Mean obliquity of date (Simon et al. 1994).
    let EPS0 = (84381.412+(-46.80927+(-0.000152+(0.0019989+(-0.00000051+(-0.000000025)*T)*T)*T)*T)*T)*DAS2R;
    return [DPSI, DEPS, EPS0];

}


export function sla_nut(mjd) {

    /*  Form the matrix of nutation for a given date - Shirai & Fukushima
    *  2001 theory (double precision)
    *
    *  Reference:
    *     Shirai, T. & Fukushima, T., Astron.J. 121, 3270-3283 (2001).
    *
    *  Given:
    *     DATE    d          TDB (loosely ET) as Modified Julian Date
    *                                           (=JD-2400000.5)
    *  Returned:
    *     RMATN   d(3,3)     nutation matrix
    *
    *  Notes:
    *
    *  1  The matrix is in the sense  v(true) = rmatn * v(mean) .
    *     where v(true) is the star vector relative to the true equator and
    *     equinox of date and v(mean) is the star vector relative to the
    *     mean equator and equinox of date.
    *
    *  2  The matrix represents forced nutation (but not free core
    *     nutation) plus corrections to the IAU~1976 precession model.
    *
    *  3  Earth attitude predictions made by combining the present nutation
    *     matrix with IAU~1976 precession are accurate to 1~mas (with
    *     respect to the ICRS) for a few decades around 2000.
    *
    *  4  The distinction between the required TDB and TT is always
    *     negligible.  Moreover, for all but the most critical applications
    *     UTC is adequate.
    *
    *  Called:   sla_NUTC, sla_DEULER
    *
    *  Last revision:   1 December 2005
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let DPSI,DEPS,EPS0;

    //  Nutation components and mean obliquity
    let result = sla_nutc(mjd);
    //console.log("sla_nutc(", mjd, ") : ", result);
    DPSI = result[0];
    DEPS = result[1];
    EPS0 = result[2];

    //  Rotation matrix
    let RMAIN = sla_deuler('XZX',EPS0,-DPSI,-(EPS0+DEPS));
    return RMAIN;
}

export function sla_dmoon(mjd) {

    /*  Approximate geocentric position and velocity of the Moon
    *  (double precision)
    *
    *  Given:
    *     DATE       D       TDB (loosely ET) as a Modified Julian Date
    *                                                    (JD-2400000.5)
    *
    *  Returned:
    *     PV         D(6)    Moon x,y,z,xdot,ydot,zdot, mean equator and
    *                                         equinox of date (AU, AU/s)
    *
    *  Notes:
    *
    *  1  This routine is a full implementation of the algorithm
    *     published by Meeus (see reference).
    *
    *  2  Meeus quotes accuracies of 10 arcsec in longitude, 3 arcsec in
    *     latitude and 0.2 arcsec in HP (equivalent to about 20 km in
    *     distance).  Comparison with JPL DE200 over the interval
    *     1960-2025 gives RMS errors of 3.7 arcsec and 83 mas/hour in
    *     longitude, 2.3 arcsec and 48 mas/hour in latitude, 11 km
    *     and 81 mm/s in distance.  The maximum errors over the same
    *     interval are 18 arcsec and 0.50 arcsec/hour in longitude,
    *     11 arcsec and 0.24 arcsec/hour in latitude, 40 km and 0.29 m/s
    *     in distance. 
    *
    *  3  The original algorithm is expressed in terms of the obsolete
    *     timescale Ephemeris Time.  Either TDB or TT can be used, but
    *     not UT without incurring significant errors (30 arcsec at
    *     the present time) due to the Moon's 0.5 arcsec/sec movement.
    *
    *  4  The algorithm is based on pre IAU 1976 standards.  However,
    *     the result has been moved onto the new (FK5) equinox, an
    *     adjustment which is in any case much smaller than the
    *     intrinsic accuracy of the procedure.
    *
    *  5  Velocity is obtained by a complete analytical differentiation
    *     of the Meeus model.
    *
    *  Reference:
    *     Meeus, l'Astronomie, June 1984, p348.
    *
    *  P.T.Wallace   Starlink   22 January 1998
    *
    *  Copyright (C) 1998 Rutherford Appleton Laboratory
    *  Copyright (C) 1995 Association of Universities for Research in Astronomy Inc.
    */

    //  Degrees, arcseconds and seconds of time to radians
    let D2R=0.0174532925199432957692369,
        DAS2R=4.848136811095359935899141e-6,
        DS2R=7.272205216643039903848712e-5;

    //  Seconds per Julian century (86400*36525)
    let CJ=3155760000;

    //  Julian epoch of B1950
    let B1950=1949.9997904423;

    //  Earth equatorial radius in AU ( = 6378.137 / 149597870 )
    let ERADAU=4.2635212653763e-5;

    let THETA,SINOM,COSOM,DOMCOM,WA,DWA,WB,DWB,WOM,
        DWOM,SINWOM,COSWOM,V,DV,COEFF,EMN,EMPN,DN,FN,EN,
        DEN,DTHETA,FTHETA,EL,DEL,B,DB,BF,DBF,P,DP,SP,R,
        DR,X,Y,Z,XD,YD,ZD,SEL,CEL,SB,CB,RCB,RBD,W,EPJ,
        EQCOR,EPS,SINEPS,COSEPS,ES,EC;



    //  Moon's mean longitude
    let ELP0=270.434164,
        ELP1=481267.8831,
        ELP2=-0.001133,
        ELP3=0.0000019;

    //  Sun's mean anomaly
    let EM0=358.475833,
        EM1=35999.0498,
        EM2=-0.000150,
        EM3=-0.0000033;

    //  Moon's mean anomaly
    let EMP0=296.104608,
        EMP1=477198.8491,
        EMP2=0.009192,
        EMP3=0.0000144;

    //  Moon's mean elongation
    let D0=350.737486,
        D1=445267.1142,
        D2=-0.001436,
        D3=0.0000019;

    //  Mean distance of the Moon from its ascending node
    let F0=11.250889,
        F1=483202.0251,
        F2=-0.003211,
        F3=-0.0000003;

    //  Longitude of the Moon's ascending node
    let OM0=259.183275,
        OM1=-1934.1420,
        OM2=0.002078,
        OM3=0.0000022;

    //  Coefficients for (dimensionless) E factor
    let E1=-0.002495,E2=-0.00000752;

    //  Coefficients for periodic variations etc
    let PAC=0.000233,PA0=51.2,PA1=20.2;
    let PBC=-0.001778;
    let PCC=0.000817;
    let PDC=0.002011;
    let PEC=0.003964,
        PE0=346.560,PE1=132.870,PE2=-0.0091731;
    let PFC=0.001964;
    let PGC=0.002541;
    let PHC=0.001964;
    let PIC=-0.024691;
    let PJC=-0.004328,PJ0=275.05,PJ1=-2.30;
    let CW1=0.0004664;
    let CW2=0.0000754;

    /*
    *  Coefficients for Moon position
    *
    *   Tx(N)       = coefficient of L, B or P term (deg)
    *   ITx(N,1-5)  = coefficients of M, M', D, F, E**n in argument
    */
    // let NL=50,NB=45,NP=31;
    /*
    *  Longitude
                                             M   M'  D   F   n*/
                                             
    let TL = [
          [+6.288750, +0, +1, +0, +0,  0],
          [+1.274018, +0, -1, +2, +0,  0],
          [+0.658309, +0, +0, +2, +0,  0],
          [+0.213616, +0, +2, +0, +0,  0],
          [-0.185596, +1, +0, +0, +0,  1],
          [-0.114336, +0, +0, +0, +2,  0],
          [+0.058793, +0, -2, +2, +0,  0],
          [+0.057212, -1, -1, +2, +0,  1],
          [+0.053320, +0, +1, +2, +0,  0],
          [+0.045874, -1, +0, +2, +0,  1],
          [+0.041024, -1, +1, +0, +0,  1],
          [-0.034718, +0, +0, +1, +0,  0],
          [-0.030465, +1, +1, +0, +0,  1],
          [+0.015326, +0, +0, +2, -2,  0],
          [-0.012528, +0, +1, +0, +2,  0],
          [-0.010980, +0, -1, +0, +2,  0],
          [+0.010674, +0, -1, +4, +0,  0],
          [+0.010034, +0, +3, +0, +0,  0],
          [+0.008548, +0, -2, +4, +0,  0],
          [-0.007910, +1, -1, +2, +0,  1],
          [-0.006783, +1, +0, +2, +0,  1],
          [+0.005162, +0, +1, -1, +0,  0],
          [+0.005000, +1, +0, +1, +0,  1],
          [+0.004049, -1, +1, +2, +0,  1],
          [+0.003996, +0, +2, +2, +0,  0],
          [+0.003862, +0, +0, +4, +0,  0],
          [+0.003665, +0, -3, +2, +0,  0],
          [+0.002695, -1, +2, +0, +0,  1],
          [+0.002602, +0, +1, -2, -2,  0],
          [+0.002396, -1, -2, +2, +0,  1],
          [-0.002349, +0, +1, +1, +0,  0],
          [+0.002249, -2, +0, +2, +0,  2],
          [-0.002125, +1, +2, +0, +0,  1],
          [-0.002079, +2, +0, +0, +0,  2],
          [+0.002059, -2, -1, +2, +0,  2],
          [-0.001773, +0, +1, +2, -2,  0],
          [-0.001595, +0, +0, +2, +2,  0],
          [+0.001220, -1, -1, +4, +0,  1],
          [-0.001110, +0, +2, +0, +2,  0],
          [+0.000892, +0, +1, -3, +0,  0],
          [-0.000811, +1, +1, +2, +0,  1],
          [+0.000761, -1, -2, +4, +0,  1],
          [+0.000717, -2, +1, +0, +0,  2],
          [+0.000704, -2, +1, -2, +0,  2],
          [+0.000693, +1, -2, +2, +0,  1],
          [+0.000598, -1, +0, +2, -2,  1],
          [+0.000550, +0, +1, +4, +0,  0],
          [+0.000538, +0, +4, +0, +0,  0],
          [+0.000521, -1, +0, +4, +0,  1],
          [+0.000486, +0, +2, -1, +0,  0]];
    
    /*
    *  Latitude
                                             M   M'  D   F   n*/
    let TB = [
          [+5.128189, +0, +0, +0, +1,  0],
          [+0.280606, +0, +1, +0, +1,  0],
          [+0.277693, +0, +1, +0, -1,  0],
          [+0.173238, +0, +0, +2, -1,  0],
          [+0.055413, +0, -1, +2, +1,  0],
          [+0.046272, +0, -1, +2, -1,  0],
          [+0.032573, +0, +0, +2, +1,  0],
          [+0.017198, +0, +2, +0, +1,  0],
          [+0.009267, +0, +1, +2, -1,  0],
          [+0.008823, +0, +2, +0, -1,  0],
          [+0.008247, -1, +0, +2, -1,  1],
          [+0.004323, +0, -2, +2, -1,  0],
          [+0.004200, +0, +1, +2, +1,  0],
          [+0.003372, -1, +0, -2, +1,  1],
          [+0.002472, -1, -1, +2, +1,  1],
          [+0.002222, -1, +0, +2, +1,  1],
          [+0.002072, -1, -1, +2, -1,  1],
          [+0.001877, -1, +1, +0, +1,  1],
          [+0.001828, +0, -1, +4, -1,  0],
          [-0.001803, +1, +0, +0, +1,  1],
          [-0.001750, +0, +0, +0, +3,  0],
          [+0.001570, -1, +1, +0, -1,  1],
          [-0.001487, +0, +0, +1, +1,  0],
          [-0.001481, +1, +1, +0, +1,  1],
          [+0.001417, -1, -1, +0, +1,  1],
          [+0.001350, -1, +0, +0, +1,  1],
          [+0.001330, +0, +0, -1, +1,  0],
          [+0.001106, +0, +3, +0, +1,  0],
          [+0.001020, +0, +0, +4, -1,  0],
          [+0.000833, +0, -1, +4, +1,  0],
          [+0.000781, +0, +1, +0, -3,  0],
          [+0.000670, +0, -2, +4, +1,  0],
          [+0.000606, +0, +0, +2, -3,  0],
          [+0.000597, +0, +2, +2, -1,  0],
          [+0.000492, -1, +1, +2, -1,  1],
          [+0.000450, +0, +2, -2, -1,  0],
          [+0.000439, +0, +3, +0, -1,  0],
          [+0.000423, +0, +2, +2, +1,  0],
          [+0.000422, +0, -3, +2, -1,  0],
          [-0.000367, +1, -1, +2, +1,  1],
          [-0.000353, +1, +0, +2, +1,  1],
          [+0.000331, +0, +0, +4, +1,  0],
          [+0.000317, -1, +1, +2, +1,  1],
          [+0.000306, -2, +0, +2, -1,  2],
          [-0.000283, +0, +1, +0, +3,  0]];
    /*
    *  Parallax
    *                                         M   M'  D   F   n*/
    let TP = [
          [+0.950724, +0, +0, +0, +0,  0],
          [+0.051818, +0, +1, +0, +0,  0],
          [+0.009531, +0, -1, +2, +0,  0],
          [+0.007843, +0, +0, +2, +0,  0],
          [+0.002824, +0, +2, +0, +0,  0],
          [+0.000857, +0, +1, +2, +0,  0],
          [+0.000533, -1, +0, +2, +0,  1],
          [+0.000401, -1, -1, +2, +0,  1],
          [+0.000320, -1, +1, +0, +0,  1],
          [-0.000271, +0, +0, +1, +0,  0],
          [-0.000264, +1, +1, +0, +0,  1],
          [-0.000198, +0, -1, +0, +2,  0],
          [+0.000173, +0, +3, +0, +0,  0],
          [+0.000167, +0, -1, +4, +0,  0],
          [-0.000111, +1, +0, +0, +0,  1],
          [+0.000103, +0, -2, +4, +0,  0],
          [-0.000084, +0, +2, -2, +0,  0],
          [-0.000083, +1, +0, +2, +0,  1],
          [+0.000079, +0, +2, +2, +0,  0],
          [+0.000072, +0, +0, +4, +0,  0],
          [+0.000064, -1, +1, +2, +0,  1],
          [-0.000063, +1, -1, +2, +0,  1],
          [+0.000041, +1, +0, +1, +0,  1],
          [+0.000035, -1, +2, +0, +0,  1],
          [-0.000033, +0, +3, -2, +0,  0],
          [-0.000030, +0, +1, +1, +0,  0],
          [-0.000029, +0, +0, -2, +2,  0],
          [-0.000029, +1, +2, +0, +0,  1],
          [+0.000026, -2, +0, +2, +0,  2],
          [-0.000023, +0, +1, -2, +2,  0],
          [+0.000019, -1, -1, +4, +0,  1]];



    //  Centuries since J1900
    let T=(mjd-15019.5)/36525;

    /*
    *  Fundamental arguments (radians) and derivatives (radians per
    *  Julian century) for the current epoch
    */

    
    //  Moon's mean longitude
    let ELP=D2R*MOD(ELP0+(ELP1+(ELP2+ELP3*T)*T)*T,360),
    DELP=D2R*(ELP1+(2*ELP2+3*ELP3*T)*T);

    //  Sun's mean anomaly
    let EM=D2R*MOD(EM0+(EM1+(EM2+EM3*T)*T)*T,360),
    DEM=D2R*(EM1+(2*EM2+3*EM3*T)*T);

    //  Moon's mean anomaly
    let EMP=D2R*MOD(EMP0+(EMP1+(EMP2+EMP3*T)*T)*T,360),
    DEMP=D2R*(EMP1+(2*EMP2+3*EMP3*T)*T);

    //  Moon's mean elongation
    let D=D2R*MOD(D0+(D1+(D2+D3*T)*T)*T,360),
    DD=D2R*(D1+(2*D2+3*D3*T)*T);

    //  Mean distance of the Moon from its ascending node
    let F=D2R*MOD(F0+(F1+(F2+F3*T)*T)*T,360),
    DF=D2R*(F1+(2*F2+3*F3*T)*T);

    //  Longitude of the Moon's ascending node
    let OM=D2R*MOD(OM0+(OM1+(OM2+OM3*T)*T)*T,360),
    DOM=D2R*(OM1+(2*OM2+3*OM3*T)*T);
    SINOM=SIN(OM),
    COSOM=COS(OM),
    DOMCOM=DOM*COSOM;

    //  Add the periodic variations
    THETA=D2R*(PA0+PA1*T),
    WA=SIN(THETA),
    DWA=D2R*PA1*COS(THETA),
    THETA=D2R*(PE0+(PE1+PE2*T)*T),
    WB=PEC*SIN(THETA),
    DWB=D2R*PEC*(PE1+2*PE2*T)*COS(THETA),
    ELP=ELP+D2R*(PAC*WA+WB+PFC*SINOM),
    DELP=DELP+D2R*(PAC*DWA+DWB+PFC*DOMCOM),
    EM=EM+D2R*PBC*WA,
    DEM=DEM+D2R*PBC*DWA,
    EMP=EMP+D2R*(PCC*WA+WB+PGC*SINOM),
    DEMP=DEMP+D2R*(PCC*DWA+DWB+PGC*DOMCOM),
    D=D+D2R*(PDC*WA+WB+PHC*SINOM),
    DD=DD+D2R*(PDC*DWA+DWB+PHC*DOMCOM),
    WOM=OM+D2R*(PJ0+PJ1*T),
    DWOM=DOM+D2R*PJ1,
    SINWOM=SIN(WOM),
    COSWOM=COS(WOM),
    F=F+D2R*(WB+PIC*SINOM+PJC*SINWOM),
    DF=DF+D2R*(DWB+PIC*DOMCOM+PJC*DWOM*COSWOM);

    //  E-factor, and square
    let E=1+(E1+E2*T)*T,
    DE=E1+2*E2*T,
    ESQ=E*E,
    DESQ=2*E*DE;

    /*
    *  Series expansions
    */

    //  Longitude
    V=0,
    DV=0;
    for(let N=0; N < TL.length; N=N+1) {
        COEFF=TL[N][0];
        EMN=TL[N][1];
        EMPN=TL[N][2];
        DN=TL[N][3];
        FN=TL[N][4];
        let I=TL[N][5];
             
        if(I==0) {
            EN=1;
            DEN=0;
        }
        else if(I==1) {
            EN=E;
            DEN=DE;
        }
        else {
            EN=ESQ;
            DEN=DESQ;
        }
        
        THETA=EMN*EM+EMPN*EMP+DN*D+FN*F;
        DTHETA=EMN*DEM+EMPN*DEMP+DN*DD+FN*DF;
        FTHETA=SIN(THETA);
        V=V+COEFF*FTHETA*EN;
        DV=DV+COEFF*(COS(THETA)*DTHETA*EN+FTHETA*DEN);
    }
    
    EL=ELP+D2R*V;
    DEL=(DELP+D2R*DV)/CJ;


    // Latitude
    V=0;
    DV=0;
    for(let N=0; N < TB.length; N=N+1) {
        COEFF=TB[N][0];
        EMN=TB[N][1];
        EMPN=TB[N][2];
        DN=TB[N][3];
        FN=TB[N][4];
        let I=TB[N][5];
        
        if(I==0) {
            EN=1;
            DEN=0;
        }
        else if(I==1) {
            EN=E;
            DEN=DE;
        }
        else {
            EN=ESQ;
            DEN=DESQ;
        }

        THETA=EMN*EM+EMPN*EMP+DN*D+FN*F;
        DTHETA=EMN*DEM+EMPN*DEMP+DN*DD+FN*DF;
        FTHETA=SIN(THETA);
        V=V+COEFF*FTHETA*EN;
        DV=DV+COEFF*(COS(THETA)*DTHETA*EN+FTHETA*DEN);
    }
    
    BF=1-CW1*COSOM-CW2*COSWOM;
    DBF=CW1*DOM*SINOM+CW2*DWOM*SINWOM;
    B=D2R*V*BF;
    DB=D2R*(DV*BF+V*DBF)/CJ;

    //  Parallax
    V=0;
    DV=0;
    for(let N=0; N < TP.length; N=N+1) {
        COEFF=TP[N][0];
        EMN=TP[N][1];
        EMPN=TP[N][2];
        DN=TP[N][3];
        FN=TP[N][4];
        let I=TP[N][5];

        if(I==0) {
            EN=1;
            DEN=0;
        }
        else if(I==1) {
            EN=E;
            DEN=DE;
        }
        else {
            EN=ESQ;
            DEN=DESQ;
        }
        
             
        THETA=EMN*EM+EMPN*EMP+DN*D+FN*F;
        DTHETA=EMN*DEM+EMPN*DEMP+DN*DD+FN*DF;
        FTHETA=COS(THETA);
        V=V+COEFF*FTHETA*EN;
        DV=DV+COEFF*(-SIN(THETA)*DTHETA*EN+FTHETA*DEN);
    }
    
    P=D2R*V;
    DP=D2R*DV/CJ;

    /*
    *  Transformation into final form
    */

    //  Parallax to distance (AU, AU/sec)
    SP=SIN(P);
    R=ERADAU/SP;
    DR=-R*DP*COS(P)/SP;

    //  Longitude, latitude to x,y,z (AU)
    SEL=SIN(EL);
    CEL=COS(EL);
    SB=SIN(B);
    CB=COS(B);
    RCB=R*CB;
    RBD=R*DB;
    W=RBD*SB-CB*DR;
    X=RCB*CEL;
    Y=RCB*SEL;
    Z=R*SB;
    XD=-Y*DEL-W*CEL;
    YD=X*DEL-W*SEL;
    ZD=RBD*CB+SB*DR;

    //  Julian centuries since J2000
    T=(mjd-51544.5)/36525;

    //  Fricke equinox correction
    EPJ=2000+T*100;
    EQCOR=DS2R*(0.035+0.00085*(EPJ-B1950));

    //  Mean obliquity (IAU 1976)
    EPS=DAS2R*(84381.448+(-46.8150+(-0.00059+0.001813*T)*T)*T);

    //  To the equatorial system, mean of date, FK5 system
    SINEPS=SIN(EPS);
    COSEPS=COS(EPS);
    ES=EQCOR*SINEPS;
    EC=EQCOR*COSEPS;
    
    let PV = new Array();
    
    PV[0]=X-EC*Y+ES*Z;
    PV[1]=EQCOR*X+Y*COSEPS-Z*SINEPS;
    PV[2]=Y*SINEPS+Z*COSEPS;
    PV[3]=XD-EC*YD+ES*ZD;
    PV[4]=EQCOR*XD+YD*COSEPS-ZD*SINEPS;
    PV[5]=YD*SINEPS+ZD*COSEPS;
    
    return PV;

}

export function sla_rdplan(mjd, NP, ELONG, PHI) {


    /*  Approximate topocentric apparent RA,Dec of a planet, and its
    *  angular diameter.
    *
    *  Given:
    *     DATE        d       MJD of observation (JD - 2400000.5)
    *     NP          i       planet: 1 = Mercury
    *                                 2 = Venus
    *                                 3 = Moon
    *                                 4 = Mars
    *                                 5 = Jupiter
    *                                 6 = Saturn
    *                                 7 = Uranus
    *                                 8 = Neptune
    *                                 9 = Pluto
    *                              else = Sun
    *     ELONG,PHI   d       observer's east longitude and geodetic
    *                                               latitude (radians)
    *
    *  Returned:
    *     RA,DEC      d        RA, Dec (topocentric apparent, radians)
    *     DIAM        d        angular diameter (equatorial, radians)
    *
    *  Notes:
    *
    *  1  The date is in a dynamical timescale (TDB, formerly ET) and is
    *     in the form of a Modified Julian Date (JD-2400000.5).  For all
    *     practical purposes, TT can be used instead of TDB, and for many
    *     applications UT will do (except for the Moon).
    *
    *  2  The longitude and latitude allow correction for geocentric
    *     parallax.  This is a major effect for the Moon, but in the
    *     context of the limited accuracy of the present routine its
    *     effect on planetary positions is small (negligible for the
    *     outer planets).  Geocentric positions can be generated by
    *     appropriate use of the routines sla_DMOON and sla_PLANET.
    *
    *  3  The direction accuracy (arcsec, 1000-3000AD) is of order:
    *
    *            Sun              5
    *            Mercury          2
    *            Venus           10
    *            Moon            30
    *            Mars            50
    *            Jupiter         90
    *            Saturn          90
    *            Uranus          90
    *            Neptune         10
    *            Pluto            1   (1885-2099AD only)
    *
    *     The angular diameter accuracy is about 0.4% for the Moon,
    *     and 0.01% or better for the Sun and planets.
    *
    *  See the sla_PLANET routine for references.
    *
    *  Called: sla_GMST, sla_DT, sla_EPJ, sla_DMOON, sla_PVOBS, sla_PRENUT,
    *          sla_PLANET, sla_DMXV, sla_DCC2S, sla_DRANRM
    *
    *  P.T.Wallace   Starlink   26 May 1997
    *
    *  Copyright (C) 1997 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the 
    *    Free Software Foundation, Inc., 59 Temple Place, Suite 330, 
    *    Boston, MA  02111-1307  USA
    *
    */

    let RA,DEC,DIAM;

    //  AU in km
    let AUKM=1.49597870e8;

    //  Light time for unit distance (sec)
    let TAU=499.004782;

    let IP;
    let STL;
    let DX,DY,DZ,R,TL;

    let VSG = new Array();
    
    //  Equatorial radii (km)
    let EQRAU = [696000.0,2439.7,6051.9,1738.0,3397.0,71492.0,60268.0,25559.0,24764.0,1151.0];
    
    

    //  Classify NP
    IP=NP;
    if(IP < 0 || IP > 9) {IP=0;}

    //  Approximate local ST
    //let jd = mjdToJd(mjd);
    //STL = radians(gmst(jd)*15.0);
    STL=sla_gmst(mjd-sla_dt(sla_epj(mjd))/86400)+ELONG;

    //  Geocentre to Moon (mean of date)
    let V = sla_dmoon(mjd)
    let V1 = V.slice(0,3);
    let V2 = V.slice(3,6);

    //  Nutation to true of date
    let RMAT = sla_nut(mjd);
    let VGM1 = sla_dmxv(RMAT,V1);
    let VGM2 = sla_dmxv(RMAT,V2);
    let VGM = VGM1.concat(VGM2);
    
    // Moon?
    if(IP==3) {
        //  Yes: geocentre to Moon (true of date)
        for(let i=0; i<6; i++) {
            V[i]=VGM[i];
        }
    }
    else {
        // No: precession/nutation matrix, J2000 to date
        RMAT = sla_prenut(2000,mjd);

        //     Sun to Earth-Moon Barycentre (J2000)
        let result = sla_planet(mjd,3);
        
        V = result[0];
        V1 = V.slice(0,3);
        V2 = V.slice(3,6);
        // let J = result[1];

        // Precession and nutation to date
        let VSE1 = sla_dmxv(RMAT,V1);
        let VSE2 = sla_dmxv(RMAT,V2);
        let VSE = VSE1.concat(VSE2);
        

        // Sun to geocentre (true of date)
        for(let i=0; i<6; i++) {
            VSG[i]=VSE[i]-0.012150581*VGM[i];
        }

        // Sun?
        if(IP==0) {
            // Yes: geocentre to Sun
            for(let i=0; i<6; i++) {
                V[i]=-VSG[i];
            }
        }
        else {

            // No: Sun to Planet (J2000)
            let result = sla_planet(mjd,IP);
            V = result[0];
            V1 = V.slice(0,3);
            V2 = V.slice(3,6);
            // let J = result[1];

            // Precession and nutation to date
            let VSP1 = sla_dmxv(RMAT,V1);
            let VSP2 = sla_dmxv(RMAT,V2);
            let VSP = VSP1.concat(VSP2);
            

            //Geocentre to planet
            for(let i=0; i<6; i++) {
                V[i]=VSP[i]-VSG[i];
            }
        }
    }
    
    //  Refer to origin at the observer
    let VGO = sla_pvobs(PHI,0,STL);
    for(let i=0; i<6; i++) {
        V[i]=V[i]-VGO[i];
    }

    //  Geometric distance (AU)
    DX=V[0];
    DY=V[1];
    DZ=V[2];
    R=SQRT(DX*DX+DY*DY+DZ*DZ);

    //  Light time (sec)
    TL=TAU*R;

    //  Correct position for planetary aberration
    for(let i=0; i<3; i++) {
        V[i]=V[i]-TL*V[i+3];
    }

    //  To RA,Dec
    let raDec = sla_dcc2s(V);
    RA = raDec[0];
    DEC = raDec[1];
    
    RA=sla_dranrm(RA);

    //  Angular diameter (radians)
    DIAM=2*ASIN(EQRAU[IP]/(R*AUKM));

    return [RA, DEC, DIAM];
}


/*****************************/

export function sla_dvdv(VA, VB) {
    /*+
    *     - - - - -
    *      D V D V
    *     - - - - -
    *
    *  Scalar product of two 3-vectors  (double precision)
    *
    *  Given:
    *      VA      dp(3)     first vector
    *      VB      dp(3)     second vector
    *
    *  The result is the scalar product VA.VB (double precision)
    *
    *  P.T.Wallace   Starlink   November 1984
    *
    *  Copyright (C) 1995 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the
    *    Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
    *    Boston, MA  02110-1301  USA
    *
    *-*/


    return VA[0]*VB[0]+VA[1]*VB[1]+VA[2]*VB[2];
      
}

export function sla_dvxv(VA, VB) {
    /*+
    *     - - - - -
    *      D V X V
    *     - - - - -
    *
    *  Vector product of two 3-vectors  (double precision)
    *
    *  Given:
    *      VA      dp(3)     first vector
    *      VB      dp(3)     second vector
    *
    *  Returned:
    *      VC      dp(3)     vector result
    *
    *  P.T.Wallace   Starlink   March 1986
    *
    *  Copyright (C) 1995 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the
    *    Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
    *    Boston, MA  02110-1301  USA
    *
    *-*/

      
    let VW = new Array();
    let VC = new Array();
    // let I;


    /*  Form the vector product VA cross VB*/
    VW[0]=VA[1]*VB[2]-VA[2]*VB[1];
    VW[1]=VA[2]*VB[0]-VA[0]*VB[2];
    VW[2]=VA[0]*VB[1]-VA[1]*VB[0];

    /*  Return the result */
    for(let I=0; I<3; I++) {
        VC[I]=VW[I];
    }
    
    return VC;
      
}

export function sla_dvn(V) {
    /**+
    *     - - - -
    *      D V N
    *     - - - -
    *
    *  Normalizes a 3-vector also giving the modulus (double precision)
    *
    *  Given:
    *     V       d(3)      vector
    *
    *  Returned:
    *     UV      d(3)      unit vector in direction of V
    *     VM      d         modulus of V
    *
    *  Notes:
    *
    *  1  If the modulus of V is zero, UV is set to zero as well.
    *
    *  2  To comply with the ANSI Fortran 77 standard, V and UV must be
    *     different arrays.  However, the routine is coded so as to work
    *     properly on most platforms even if this rule is violated.
    *
    *  Last revision:   22 July 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the
    *    Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
    *    Boston, MA  02110-1301  USA
    *
    *-*/


    /*  Modulus.*/
    let W1 = 0.0;
    for(let I=0; I<3; I++) {
        let W2 = V[I];
        W1 = W1 + W2*W2;
    }
    W1 = Math.sqrt(W1);
    let VM = W1;

    /*  Normalize the vector.*/
    if(W1 <= 0.0) {
        W1 = 1.0;
    }
    
    let UV = new Array();
    for(let I=0; I<3; I++) {
        UV[I] = V[I]/W1;
    }
    
    return [UV, VM];
}

export function sla_dsepv(V1, V2) {
    /*+
    *     - - - - - -
    *      D S E P V
    *     - - - - - -
    *
    *  Angle between two vectors.
    *
    *  (double precision)
    *
    *  Given:
    *     V1      d(3)    first vector
    *     V2      d(3)    second vector
    *
    *  The result is the angle, in radians, between the two vectors.  It
    *  is always positive.
    *
    *  Notes:
    *
    *  1  There is no requirement for the vectors to be unit length.
    *
    *  2  If either vector is null, zero is returned.
    *
    *  3  The simplest formulation would use dot product alone.  However,
    *     this would reduce the accuracy for angles near zero and pi.  The
    *     algorithm uses both cross product and dot product, which maintains
    *     accuracy for all sizes of angle.
    *
    *  Called:  sla_DVXV, sla_DVN, sla_DVDV
    *
    *  Last revision:   14 June 2005
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the
    *    Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
    *    Boston, MA  02110-1301  USA
    *
    *-*/

    let S, C;


    /*  Modulus of cross product = sine multiplied by the two moduli.*/
    let V1XV2 = sla_dvxv(V1,V2);
    
    
    let result = sla_dvn(V1XV2);
    // WV = result[0];
    S = result[1];

    /*  Dot product = cosine multiplied by the two moduli.*/
    C = sla_dvdv(V1,V2);

    /*  Angle between the vectors.*/
    if(S != 0.0 || C != 0.0) {
        return Math.atan2(S,C);
    }
    else {
        return 0.0;
    }
    
}

export function sla_dcs2c(A, B) {
    /*+
    *     - - - - - -
    *      D C S 2 C
    *     - - - - - -
    *
    *  Spherical coordinates to direction cosines (double precision)
    *
    *  Given:
    *     A,B       d      spherical coordinates in radians
    *                         (RA,Dec), (long,lat) etc.
    *
    *  Returned:
    *     V         d(3)   x,y,z unit vector
    *
    *  The spherical coordinates are longitude (+ve anticlockwise looking
    *  from the +ve latitude pole) and latitude.  The Cartesian coordinates
    *  are right handed, with the x axis at zero longitude and latitude, and
    *  the z axis at the +ve latitude pole.
    *
    *  Last revision:   26 December 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the
    *    Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
    *    Boston, MA  02110-1301  USA
    *
    *-*/
    
    let V = new Array();
    let COSB = Math.cos(B);
    V[0] = Math.cos(A)*COSB;
    V[1] = Math.sin(A)*COSB;
    V[2] = Math.sin(B);
    
    return V;
}

export function sla_dsep(A1, B1, A2, B2) {
    /*
    *     - - - - -
    *      D S E P
    *     - - - - -
    *
    *  Angle between two points on a sphere.
    *
    *  (double precision)
    *
    *  Given:
    *     A1,B1    d     spherical coordinates of one point
    *     A2,B2    d     spherical coordinates of the other point
    *
    *  (The spherical coordinates are [RA,Dec], [Long,Lat] etc, in radians.)
    *
    *  The result is the angle, in radians, between the two points.  It
    *  is always positive.
    *
    *  Called:  sla_DCS2C, sla_DSEPV
    *
    *  Last revision:   7 May 2000
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the
    *    Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
    *    Boston, MA  02110-1301  USA
    *
    *-*/

    
    /*  Convert coordinates from spherical to Cartesian.*/
    let V1 = sla_dcs2c(A1, B1);
    let V2 = sla_dcs2c(A2, B2);

    /*  Angle between the vectors.*/
    return sla_dsepv(V1,V2);
}



export function sla_pa(HA, DEC, PHI) {
    /*+
    *     - - -
    *      P A
    *     - - -
    *
    *  HA, Dec to Parallactic Angle (double precision)
    *
    *  Given:
    *     HA     d     hour angle in radians (geocentric apparent)
    *     DEC    d     declination in radians (geocentric apparent)
    *     PHI    d     observatory latitude in radians (geodetic)
    *
    *  The result is in the range -pi to +pi
    *
    *  Notes:
    *
    *  1)  The parallactic angle at a point in the sky is the position
    *      angle of the vertical, i.e. the angle between the direction to
    *      the pole and to the zenith.  In precise applications care must
    *      be taken only to use geocentric apparent HA,Dec and to consider
    *      separately the effects of atmospheric refraction and telescope
    *      mount errors.
    *
    *  2)  At the pole a zero result is returned.
    *
    *  P.T.Wallace   Starlink   16 August 1994
    *
    *  Copyright (C) 1995 Rutherford Appleton Laboratory
    *
    *  License:
    *    This program is free software; you can redistribute it and/or modify
    *    it under the terms of the GNU General Public License as published by
    *    the Free Software Foundation; either version 2 of the License, or
    *    (at your option) any later version.
    *
    *    This program is distributed in the hope that it will be useful,
    *    but WITHOUT ANY WARRANTY; without even the implied warranty of
    *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    *    GNU General Public License for more details.
    *
    *    You should have received a copy of the GNU General Public License
    *    along with this program (see SLA_CONDITIONS); if not, write to the
    *    Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
    *    Boston, MA  02110-1301  USA
    *
    *-*/

      
    let CP = Math.cos(PHI);
    let SQSZ = CP*Math.sin(HA);
    let CQSZ = Math.sin(PHI)*Math.cos(DEC)-CP*Math.sin(DEC)*Math.cos(HA);
    if (SQSZ == 0.0 && CQSZ == 0.0) CQSZ=1.0;
    
    return Math.atan2(SQSZ,CQSZ);
}