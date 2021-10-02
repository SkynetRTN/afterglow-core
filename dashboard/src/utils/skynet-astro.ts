/* Utility functions that are useful for doing astronomy */

import { sprintf } from 'sprintf-js';
import { sla_rdplan, sla_eqeqx, sla_dtt, sla_dsep, sla_pa } from './slalib';

let gmas000 = 2451545.0; /* Epoch gmas000 in julian days */
export let J2000 = 2451545.0; /* Epoch J2000 in julian days */

function truncFloat(f, decimals) {
    /*
    Truncate a floating point number to some number of digits after 
    the decimal point.

    Examples:
        >>> print truncFloat(3.14159, 2)
        3.14
        >>> print truncFloat(3.14159, 2)
        3.14
        >>> print truncFloat(-2.99999999, 2)
        -2.99
        >>> print truncFloat(-2.99999999, 0)
        -2.0
        >>> print truncFloat(123.001, 3)
        123.001
    */

    /*assert type(f) in (int, long, float), "f arg must be numeric"
    assert type(decimals) == int, "decimals arg must be int"*/

    var shift = Math.pow(10.0,decimals)

    return Math.floor(f * shift) / shift;
}

export function degToDms(value) {
    /*
    Convert a number (which may or may not be in degrees) to a sexagesimal
    representation.

    @param value: The decimal number to convert
    @return: A tuple (sign, degrees, minutes, seconds).
             Note that sign is 1 if value is positive, -1 if negative.
    */

    let sign = 1;
    if(value < 0) {
        sign = -1;
        value = -value;
    }

    let degrees = Math.floor(value);
    value = 60*(value - degrees);
    let minutes = Math.floor(value);
    let seconds = 60*(value - minutes);

    return [sign, degrees, minutes, seconds]
}

/** Parse a sexagesimal string of the form "-DD:MM:SS.s"
 *  For example, "10:30:00" is converted to "10.5"
 *  Fields may be separated by space, ":", or "_"
 *  Valid formats also include "DD.ddd" and "DD:MM.mmm"
 *
 *  @param str The string to parse
 *  @return The floating point value of the sexagesimal string
 */
export function parseDms(str)
{
    let fields = str.split(/[ :_]/);
    let sign = 1;
    let result = 0;

    if (parseFloat(fields[0]) < 0) {
        sign = -1;
        fields[0] = -parseFloat(fields[0]);
    }

    let denom = 1.0;

    for (let i in fields) {
        let field = parseFloat(fields[i]);
        result += field/denom;
        denom *= 60;
    }

    return sign*result;
}

export function formatDms(value, digits, decimals, sep1, sep2, sep3, showplus) {
    /*
    Format a decimal value as a sexagesimal string.

    @param digits: number of sexagesimal units to use - either 2 or 3
                   (2 = DD:MM, 3 = DD:MM:SS)
    @param decimals: number of places after the decimal point to display on
                     the last digit (0 = DD:MM:SS, 2 = DD:MM:SS.ss, etc.
    @param sep1: string to follow the first sexagesimal unit
    @param sep2: string to follow the second sexagesimal unit
    @param sep3: string to follow the third sexagesimal unit
                 (ignored if digits == 2)
    @param showplus: if True, explicitly show the "+" sign when positive

    Examples:
    >>> formatDms(-0.99999999)
    '-00:59:59.9'
    >>> formatDms(0.99999999)
    '00:59:59.9'
    >>> formatDms(0.99999999, showplus=True)
    '+00:59:59.9'
    >>> formatDms(0.99999999, digits=2)
    '00:59.9'
    >>> formatDms(10.5125, digits=2, sep1="d ", sep2="m ")
    '10d 30.7m '
    >>> formatDms(10.5125, digits=2, decimals=3, sep1="d ", sep2="m")
    '10d 30.749m'
    >>> formatDms(10.5125, digits=3, decimals=3, sep1="d ", sep2="m ", sep3="s")
    '10d 30m 44.999s'
    >>> formatDms(-10.5125, digits=3, decimals=3, sep1="d ", sep2="m ", sep3="s")
    '-10d 30m 44.999s'
    */

   /* assert digits in (2, 3), "digits arg must be 2 or 3"
    assert decimals >= 0, "decimals arg must be >= 0"
    assert type(value) in (int, float, long), "value arg must be numeric"
    assert type(digits) == int, "digits arg must be int"
    assert type(decimals) == int, "decimals arg must be int"
    assert type(sep1) == str, "sep1 must be a string"
    assert type(sep2) == str, "sep2 must be a string"
    assert type(sep3) == str, "sep3 must be a string"
    assert type(showplus) == bool, "showplus must be a boolean"*/

    if(digits == null) digits = 3;
    if(decimals == null) decimals = 1;
    if(sep1 == null) sep1 = ":";
    if(sep2 == null) sep2 = ":";
    if(sep3 == null) sep3 = "";
    if(showplus == null) showplus = false;
    
    
    
    if(digits == 2 && sep2 == ":") {
        // Probably don't want a trailing colon...
        sep2 = "";
    }

    let result = degToDms(value);
    let signVal = result[0];
    let sign = "";
    let d = result[1];
    let m = result[2];
    let s = result[3];


    if(signVal < 0) {
        sign = "-";
    }
    else if(showplus) {
        sign = "+";
    }
    else {
        sign = "";
    }

    let lastFormat = "%02d";
    if(decimals != 0) {
        lastFormat = sprintf("%%0%d.%df", decimals+3, decimals);
    }
    
    let r;
    if(digits == 2) {
        // Truncate before formatting to avoid, e.g., .999999 -> 00:60.0
        let lastDigit = truncFloat(m + s/60.0, decimals);

        let lastDigitStr = sprintf(lastFormat, lastDigit);
        r = sprintf("%s%02d%s%s%s", sign, d, sep1, lastDigitStr, sep2);
    }
    else {
        let lastDigit = sprintf(lastFormat, truncFloat(s, decimals));
        r = sprintf("%s%02d%s%02d%s%s%s", sign, d, sep1, m, sep2, lastDigit, sep3);
    }
    
    return r;
   
}

/** Convert from equatorial to horizon coordinates
 * 
 * @param {Number} ha   The hour angle, in hours, in the current epoch
 * @param {Number} dec  The decliation, in degrees, in the current epoch
 * @param {Number} lat  The latitude, in degrees
 * @return An array [az, el] in degrees. Azimuth 0 is North, 90 is East
 */
export function haDecToAzEl(ha, dec, lat)
{
    ha = hrs2rad(ha);
    dec = deg2rad(dec);
    lat = deg2rad(lat);

    let el = rad2deg(Math.asin(Math.sin(lat)*Math.sin(dec) +
            Math.cos(lat)*Math.cos(dec)*Math.cos(ha)));

	let az = rad2deg(Math.atan2(Math.sin(ha), 
	           Math.cos(ha)*Math.sin(lat)-Math.tan(dec)*Math.cos(lat)));

	az = rerange(az+180, 0, 360);
	//alt = rerange(alt, -90, 90);
			   
	return [az, el];
}

/** Convert from horizon to equatorial coordinates
 * 
 * @param {Object} az   The azimuth in degrees; 0 is North, 90 is East
 * @param {Object} el  The elevation in the sky, in degrees
 * @param {Object} lat  The latitude, in degrees
 * @return  An array [ha, dec], ha in hours between 0 and 24, dec in degrees
 *          between -90 and 90. Coordinates are in the current epoch.
 */
export function azElToHADec(az, el, lat)
{
    az = rerange(az+180, 0, 360) // Meeus says az 0 = south, we say it is north

    az = deg2rad(az);
    el = deg2rad(el);
    lat = deg2rad(lat);

    let ha = degrees(Math.atan2( Math.sin(az), Math.cos(az)*Math.sin(lat) + Math.tan(el)*Math.cos(lat) ))
    let dec = degrees(Math.asin( Math.sin(lat)*Math.sin(el) - Math.cos(lat)*Math.cos(el)*Math.cos(az) ))
    
    return [ha/15.0, dec]
}

/** Convert RA/Dec to Az/El
 *  ra: Hours
 *  dec: Degrees
 *  lon: Degrees
 *  lat: Degrees
 *  jd: julian day, or null to use current time
 *
 *  Returns: az and el in degrees
 */
export function raDecToAzEl(ra, dec, lon, lat, jd)
{
    let lst = lmst(lon, jd);
    let ha = rerange(lst - ra, 0, 24);

    let azEl = haDecToAzEl(ha, dec, lat);
    let az = azEl[0];
    let el = azEl[1];


    return [az, el];
}

/** Convert Az/El to RA/Dec
 *  az: Degrees
 *  el: Degrees
 *  lon: Degrees
 *  lat: Degrees
 *  jd: julian day, or null to use current time
 *
 *  Returns: ra in hours and dec in degrees
 */
export function azElToRaDec(az, el, lon, lat, jd)
{
    let hadec = azElToHADec(az, el, lat);
    let ha = hadec[0];
    let dec = hadec[1];

    let lst = lmst(lon, jd);
    let ra = rerange(lst - ha, 0, 24);

    return [ra, dec];
}

/** Convert from equatorial coordinates to galactic coordinates
 * 
 * @param {Number} ra   Right ascension in hours, in B1950 epoch
 * @param {Number} dec  Declination in degrees, in B1950 epoch
 * @return An array [l,b] of galactic longitude and latitude in degrees
 */
export function raDecToGalactic(ra, dec)
{
    ra = deg2rad(ra*15.0);
    dec = deg2rad(dec);

    let pole_ra = deg2rad(192.25);
    let pole_dec = deg2rad(27.4);

    let x = Math.atan2(Math.sin(pole_ra - ra),
                       Math.cos(pole_ra - ra) * Math.sin(pole_dec) - 
                       Math.tan(dec) * Math.cos(pole_dec));

    let l = 303-rad2deg(x);
    let b = Math.asin(Math.sin(dec)*Math.sin(pole_dec) + 
            Math.cos(dec)*Math.cos(pole_dec)*Math.cos(pole_ra-ra));

    b = rad2deg(b);

    l = rerange(l, 0, 360);
    b = rerange(b, -90, 90);

    return [l, b];
}

/** Convert from galactic to equatorial coordinates
 * 
 * @param {Number} l  Galactic longitude, in degrees
 * @param {Number} b  Galactic latitude, in degrees
 * @return An object with members ra and dec. RA is in hours
 *         and Dec is in degrees. Both are in the B1950 epoch.
 */
export function galacticToRaDec(l, b)
{
    let pole_lon = deg2rad(123);
    let pole_lat = deg2rad(27.4);

    l = deg2rad(l);
    b = deg2rad(b);

    let y = Math.atan2(Math.sin(l-pole_lon),
              Math.cos(l-pole_lon)*Math.sin(pole_lat)-
              Math.tan(b)*Math.cos(pole_lat));
    let ra = (rad2deg(y)+12.25)/15.0;

    let dec = Math.asin(Math.sin(b)*Math.sin(pole_lat) +
                Math.cos(b)*Math.cos(pole_lat)*Math.cos(l-pole_lon));
    dec = rad2deg(dec);

    ra = rerange(ra, 0, 24);
    dec = rerange(dec, -90, 90);

    return [ra, dec];
}

export function altDecToHa(alt, dec, lat) {
    /*
    Find the positive (westward) hour angle for a line of
    declination at a given altitude and site latitude.
    This can be useful in determining how long an object
    will be visible above a given altitude, or for drawing
    lines of declination above the horizon in a graphical
    view of the sky.

    All input parameters are in degrees.

    Derived by taking the equation to transform ha,dec,lat to
    alt (Meeus 2ed, eqn 13.6) and solving for ha.

    Returns HA in hours, with a range of [0.0, 12.0].
    If the line of declination is circumpolar above the altitude limit,
    returns +12.0. If the line of declination is always below the
    altitude limit, returns 0.0.
    */
    
    alt = radians(alt);
    dec = radians(dec);
    lat = radians(lat);

    let cosHA = (Math.sin(alt) - Math.sin(lat)*Math.sin(dec)) / (Math.cos(lat)*Math.cos(dec));
    
    if(cosHA >= 1.0) {
        return 0.0;  // Declination is never visible
    }

    if(cosHA <= -1.0) {
        return 12.0; // Declination is circumpolar
    }

    return degrees(Math.acos(cosHA))/15.0;
}

export function altHaToDec(alt, ha, lat) {
    /*
    Calculate the declination for a point at a given altitude
    and HA for a site at some latitude. This can be useful when drawing
    HA grid lines for an alt-az view of the sky.

    alt and lat are in degrees
    ha is in hours (-12 to +12)

    Derived by taking the equation to transform ha,dec,lat to
    alt (Meeus 2ed, eqn 13.6) and solving for dec. This appears to
    be quite a non-trivial algebraic transformation, so I had to ask
    Wolfram Alpha for help.

    Returns Dec in degrees, with a range of [-90.0, 90.0]
    
    WARNING: This only works reliably for alt=0 at the moment
    */

    alt = radians(alt)
    ha = radians(ha*15)
    lat = radians(lat)

    let top = Math.sin(lat) - Math.sqrt(
            Math.cos(ha)*Math.cos(ha) * Math.cos(lat)*Math.cos(lat) -
            Math.sin(alt)*Math.sin(alt) + Math.sin(lat)*Math.sin(lat)
            );

    let bottom = Math.cos(ha)*Math.cos(lat) + Math.sin(alt);
    
    let dec = 2*Math.atan2(top, bottom);
    dec = degrees(dec) // This value could be between -360 and +360

    return rerange(dec, -90, 90)
}




/** Return an estimate of the magnitude of the 10th brightest
 *  star in a 10 arcminute square field at the given coordinates.
 *  This formula was determined empirically from looking at star
 *  densities in the GSC II catalog. This is described in detail
 *  in the "stardensity" folder of this program.
 *  
 * @param {Number} ra  The right ascension of your field, in hours
 * @param {Number} dec Decliation of your field, in degrees
 * @return A numeric magnitude
 */
export function estimateFieldMagnitude(ra, dec)
{
	// We should actually precess ra and dec to B1950 here, which is
	// what this export function wants
	let galactic = raDecToGalactic(ra, dec);
	let B = galactic[1];
	
	return 12.5 + 0.5*Math.sqrt(Math.abs(0.8*B));
}

/** Precess RA/Dec coordinates between two epochs.
 *
 * @param {Number} ra  The right ascension to precess, in hours
 * @param {Number} dec Declination to precess, in hours
 * @param {Number} from_jd The julian day to precess from, e.g. 2451545.0 for
                           gmas000.  If null, use the current epoch.
 * @param {Number} to_jd   The julian day to precess to. If null, use
 *                         the current epoch.
 * @return Precessed position, as an object with ra and dec members.
 *         ra is in hours, dec is in degrees.
 */

export function precess(ra, dec, from_jd, to_jd)
{
    

    if (from_jd == null) {
        from_jd = jdNow();
    }

    if (to_jd == null) {
        to_jd = jdNow();
    }
    
    ra = hrs2rad(ra);
    dec = deg2rad(dec);

    let T = (from_jd - gmas000) / 36525.0;
    let t = (to_jd - from_jd) / 36525.0;

    let T2 = T*T;
    let t2 = t*t;
    let t3 = t2*t;

    let zeta = (2306.2181 + 1.39656*T - 0.000139*T2) * t 
                  + (0.30188 - 0.000344*T) * t2 
                  + 0.017998 * t3;

    let eta = (2306.2181 + 1.39656*T - 0.000139*T2) * t 
                  + (1.09468 + 0.000066*T) * t2 
                  + 0.018203 * t3;

    let theta = (2004.3109 - 0.85330*T - 0.000217*T2) * t 
                  - (0.42665 + 0.000217*T) * t2 
                  - 0.041833 * t*t*t;

    zeta = deg2rad(zeta/3600.0);
    eta = deg2rad(eta/3600.0);
    theta = deg2rad(theta/3600.0);

    let A = Math.cos(dec) * Math.sin(ra + zeta);
    let B = Math.cos(theta) * Math.cos(dec) * Math.cos(ra + zeta) - Math.sin(theta) * Math.sin(dec);
    let C = Math.sin(theta) * Math.cos(dec) * Math.cos(ra + zeta) + Math.cos(theta) * Math.sin(dec);

    let prec_ra = Math.atan2(A, B) + eta;

    let prec_dec;
    /* Check for object near celestial pole */
    if (dec > (0.4 * Math.PI) || dec < (-0.4 * Math.PI)) {
        /* Close to pole */
        prec_dec = Math.acos( Math.sqrt( A*A + B*B) );
        if (dec < 0.0) {
            prec_dec = -prec_dec;
        }
    }
    else {
        /* Not close to pole */
        prec_dec = Math.asin(C);
    }

    prec_ra = rerange(rad2hrs(prec_ra), 0, 24);
    prec_dec = rerange(rad2deg(prec_dec), -90, 90);
    

    return [prec_ra, prec_dec];
}

export function datetimeToJd(year, month, day, hour, minute, second) {
    return jdNow(year, month, day, hour, minute, second);
}

/** Return the julian day for a given time. If no arguments are supplied,
 *  return the current JD.
 */

export function jdNow(year?: number, month?: number, day?: number, hour?: number, minute?: number, second?: number)
{
    if (year == undefined) {
        /* Probably no args; return current JD */
        let now = new Date();
        year = now.getUTCFullYear();
        month = now.getUTCMonth() + 1;
        day = now.getUTCDate();
        hour = now.getUTCHours();
        minute = now.getUTCMinutes();
        second = now.getUTCSeconds() + now.getMilliseconds()/1000.0;
    }

    if (hour != undefined && minute != undefined && second != undefined) {
        /* Convert hours/minutes/seconds into fractional days */
        let fracday = hour/24.0 + minute/24.0/60.0 + second/86400.0;
        day += fracday;
    }

    if (month == 1 || month == 2) {
        year = year-1;
        month = month+12;
    }

    let A = Math.floor(year / 100);
    let B = 2 - A + Math.floor(A/4);

    let jd = Math.floor(365.25*(year + 4716)) + Math.floor(30.6001*(month+1))
                + day + B - 1524.5;

    return jd;
}

export function jdToDatetime(jd) {
    jd += 0.5;
    let Z = Math.floor(jd);
    let F = jd - Z;

    let A;

    if(Z < 2299161) {
        A = Math.floor(Z);
    }
    else {
        let a = Math.floor((Z - 1867216.25) / 36524.25);
        A = Math.floor(Z + 1 + a - Math.floor(a/4));
    }

    let B = A + 1524;
    let C = Math.floor((B - 122.1) / 365.25);
    let D = Math.floor(365.25*C);
    let E = Math.floor((B-D)/30.6001);

    let hours = Math.floor(F*24);
    F -= hours/24.0;
    let minutes = Math.floor(F*1440);
    F -= minutes/1440.0
    let seconds = F*86400;

    let days = B - D - Math.floor(30.6001*E);

    let months, years;
    if(E < 14) {
        months = E - 1;
    }
    else {
        months = E - 13;
    }
    
    if(months > 2) {
        years = C - 4716;
    }
    else {
        years = C - 4715;
    }

    let result = new Date()
    result.setUTCFullYear(years);
    result.setUTCMonth(months);
    result.setUTCDate(days);
    result.setUTCHours(hours);
    result.setUTCMinutes(minutes);
    result.setUTCSeconds(seconds);
    
    return result;
}

export function mjdNow()
{
    return jdNow() - 2400000.5;
}

export function mjdToJd(mjd) {
    return mjd + 2400000.5;
}

export function jdToMjd(jd) {
    return jd - 2400000.5;
}

/**
 *  Returns Greenwich Mean Sidereal Time in hours
 *  jd: julian day; if null, use current time
 */
export function gmst(targetJD)
{

    if (targetJD == null) {
        targetJD = jdNow();
    }

    // Meeus 2ed, eq 12.1
    let T = (targetJD - 2451545.0) / 36525.0;
    let T2 = T * T;
    let T3 = T2 * T;

    // Meeus 2ed, eq 12.4
    let st = (280.46061837 + 360.98564736629*(targetJD - 2451545.0) 
         + 0.000387933 * T2 
         - T3 / 38710000.0)

    return st/15.0;
}

/**
 *  Returns local mean sidereal time in hours
 *  lon: longitude in degrees. Negative = west of greenwich
 *  jd: julian day; if null, use current time
 */
export function lmst(lon, jd)
{
    return rerange(gmst(jd) + lon/15.0, 0, 24);
}

/**
 * Return a tuple (ra, dec) for the position of the sun
 * at the given julian day
 * 
 * ra: in hours
 * dec: in degrees
 */
export function solarRaDec(jd)
{
    // Meeus 2ed eqs 25.1 - 25.7
    let T = (jd - 2451545.0) / 36525;
    let T2 = T*T;

    let L0 = 280.46646 + 36000.76983*T + 0.0003032*T2;            
    let M = 357.52911 + 35999.05029*T - 0.0001537*T2;
    // let e = 0.016708634 - 0.000042037*T - 0.0000001267*T2;

    let Mrad = deg2rad(M)

    let C = (1.914602 - 0.004817*T - 0.000014*T2) * Math.sin(Mrad) 
        + (0.019993 - 0.000101*T) * Math.sin(2*Mrad)           
        + 0.000289 * Math.sin(3*Mrad);

    let lon = deg2rad(L0 + C)

    // TODO - we should really be passing in JDE, not JD
    let epsilon = deg2rad(meanObliquity(jd));

    let ra = Math.atan2(
            Math.cos(epsilon) * Math.sin(lon),
            Math.cos(lon)
        );

    let dec = Math.asin(Math.sin(epsilon) * Math.sin(lon));

    ra = rad2deg(ra)
    dec = rad2deg(dec)

    ra = rerange(ra, 0, 360)/15.0

    return [ra, dec];
}

/**
 * lat: Site latitude, in degrees
 * lon: Site longitude, in degrees
 * jd:  Julian Day at which to calculate position
 * Returns an object with the following members:
 *   alt: Altitude, in degrees
 *   az: Azimuth, in degrees
 */
export function solarAzEl(lat, lon, jd)
{
    let sun = solarRaDec(jd);
    return raDecToAzEl(sun[0], sun[1], lon, lat, jd);
}


export function datetimeFromHours(year, month, day, hours) {
    let result = new Date()
    result.setUTCFullYear(year);
    result.setUTCMonth(month);
    result.setUTCDate(day);
    let h = hours;
    let m = (h-Math.floor(h))*60.0;
    let s = (m-Math.floor(m))*60.0;
    result.setUTCHours(Math.floor(h));
    result.setUTCMinutes(Math.floor(m));
    result.setUTCSeconds(Math.floor(s));
    return result;
}

/*

*/
export function solarTime(lat, lon, jd, type) {
    let t = jdToDatetime(jd);
    for(let i=0; i<2; i++) {
        let hours = _calculateSolarTimes(lat, lon, jd)[type];
        let tnew = datetimeFromHours(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate(), hours);
        jd = jdNow(tnew.getUTCFullYear(), tnew.getUTCMonth(), tnew.getUTCDate(), tnew.getUTCHours(), tnew.getUTCMinutes(), tnew.getUTCSeconds());
    }
    return jd;
}


export function _calculateSolarTimes(lat, lon, startTimeJd) {
    let jd = startTimeJd;
    
    let jc = (jd-2451545.0)/36525.0;
    let gmls = (280.46646+jc*(36000.76983 + jc*0.0003032)) % 360;
    let gmas = 357.52911+jc*(35999.05029 - 0.0001537*jc);
    let eeo = 0.016708634-jc*(0.000042037+0.0000001267*jc);
    let seqc = Math.sin(deg2rad(gmas))*(1.914602-jc*(0.004817+0.000014*jc))+Math.sin(deg2rad(2*gmas))*(0.019993-0.000101*jc)+Math.sin(deg2rad(3*gmas))*0.000289;
    let stl = gmls + seqc;
    // let sta = gmas + seqc;
    let sal = stl-0.00569-0.00478*Math.sin(deg2rad(125.04-1934.136*jc));
    let moe =23+(26+((21.448-jc*(46.815+jc*(0.00059-jc*0.001813))))/60)/60;
    let oc = moe+0.00256*Math.cos(deg2rad(125.04-1934.136*jc));
    // let sunRa = rad2deg(Math.atan2(Math.cos(deg2rad(oc))*Math.sin(deg2rad(sal)),Math.cos(deg2rad(sal))));
    let sunDec = rad2deg(Math.asin(Math.sin(deg2rad(oc))* Math.sin(deg2rad(sal))))
    let vary = Math.tan(deg2rad(oc/2))*Math.tan(deg2rad(oc/2));
    let eot = 4*rad2deg(vary*Math.sin(2*deg2rad(gmls))-2*eeo*Math.sin(deg2rad(gmas))+4*eeo*vary*Math.sin(deg2rad(gmas))*Math.cos(2*deg2rad(gmls))-0.5*vary*vary*Math.sin(4*deg2rad(gmls))-1.25*eeo*eeo*Math.sin(2*deg2rad(gmas)));
    
    let sunriseHa = rad2deg(Math.acos(Math.cos(deg2rad(90.833))/(Math.cos(deg2rad(lat))*Math.cos(deg2rad(sunDec)))-Math.tan(deg2rad(lat))*Math.tan(deg2rad(sunDec))));
    let solarNoon = (720-4*lon-eot)/60.0;
    let sunrise = solarNoon-sunriseHa/15.0;
    let sunset = solarNoon+sunriseHa/15.0;
    
    let result = {'sunrise':sunrise, 'noon':solarNoon, 'sunset':sunset, 'midnight':rerange(solarNoon+12.0, 0, 24)};
    return result;
}


/**
 * Return mean obliquity in degrees at the given JDE
 */
export function meanObliquity(jde)
{
    let T = (jde - 2451545.0) / 36535.0;
    let T2 = T*T;
    let T3 = T2*T;

    let e0 = (23 + 26/60.0 + 31.448/3600.0) 
          - (46.8150/3600.0) * T        
          - (0.00059/3600.0) * T2       
          + (0.001813/3600.0) * T3;

    return e0;
}



/** Put a value into the range [low,high] using clock arithmetic
 * 
 * @param {Number} val  The value to put into a given range
 * @param {Number} min  The low end of the range; included in the range
 * @param {Number} max  The high end of the range; not included in the range
 *
 * Example: rerange(361, -180, 180) returns -179
 */
export function rerange(val, min, max)
{
	let range = max-min;
    return (range+(val-min)%range)%range + min;
}

/**** Conversions between hours, degrees, and radians ****/

export function rad2deg(rad)
{
    return rad*180/Math.PI;
}

export function deg2rad(deg)
{
    return deg*Math.PI/180;
}

export function hrs2deg(hrs)
{
	return hrs*15.0;
}

export function deg2hrs(deg)
{
	return deg/15.0;
}

export function rad2hrs(rad)
{
	return rad*12/Math.PI;
}

export function hrs2rad(hrs)
{
	return hrs*Math.PI/12;
}


 //L2   L3   L4  L5  L6  L7  L8  Ldash D   Mdash F   xsin      xsint xcos    xcost ysin   ysint ycos     ycost zsin   zsint zcos    zcost
let aberrationCoefficients = [
  [  0,  1,   0,  0,  0,  0,  0,  0,    0,  0,    0,  -1719914, -2,   -25,    0,    25,    -13,  1578089, 156,  10,    32,   684185, -358 ],
  [  0,  2,   0,  0,  0,  0,  0,  0,    0,  0,    0,  6434,     141,  28007,  -107, 25697, -95,  -5904,   -130, 11141, -48,  -2559,  -55  ],
  [  0,  0,   0,  1,  0,  0,  0,  0,    0,  0,    0,  715,      0,    0,      0,    6,     0,    -657,    0,    -15,   0,    -282,   0    ],
  [  0,  0,   0,  0,  0,  0,  0,  1,    0,  0,    0,  715,      0,    0,      0,    0,     0,    -656,    0,    0,     0,    -285,   0    ],
  [  0,  3,   0,  0,  0,  0,  0,  0,    0,  0,    0,  486,      -5,   -236,   -4,   -216,  -4,   -446,    5,    -94,   0,    -193,   0    ],
  [  0,  0,   0,  0,  1,  0,  0,  0,    0,  0,    0,  159,      0,    0,      0,    2,     0,    -147,    0,    -6,    0,    -61,    0    ],
  [  0,  0,   0,  0,  0,  0,  0,  0,    0,  0,    1,  0,        0,    0,      0,    0,     0,    26,      0,    0,     0,    -59,    0    ],
  [  0,  0,   0,  0,  0,  0,  0,  1,    0,  1,    0,  39,       0,    0,      0,    0,     0,    -36,     0,    0,     0,    -16,    0    ],
  [  0,  0,   0,  2,  0,  0,  0,  0,    0,  0,    0,  33,       0,    -10,    0,    -9,    0,    -30,     0,    -5,    0,    -13,    0    ],
  [  0,  2,   0,  -1, 0,  0,  0,  0,    0,  0,    0,  31,       0,    1,      0,    1,     0,    -28,     0,    0,     0,    -12,    0    ],
  [  0,  3,   -8, 3,  0,  0,  0,  0,    0,  0,    0,  8,        0,    -28,    0,    25,    0,    8,       0,    11,    0,    3,      0    ],
  [  0,  5,   -8, 3,  0,  0,  0,  0,    0,  0,    0,  8,        0,    -28,    0,    -25,   0,    -8,      0,    -11,   0,    -3,     0    ],
  [  2,  -1,  0,  0,  0,  0,  0,  0,    0,  0,    0,  21,       0,    0,      0,    0,     0,    -19,     0,    0,     0,    -8,     0    ],
  [  1,  0,   0,  0,  0,  0,  0,  0,    0,  0,    0,  -19,      0,    0,      0,    0,     0,    17,      0,    0,     0,    8,      0    ],
  [  0,  0,   0,  0,  0,  1,  0,  0,    0,  0,    0,  17,       0,    0,      0,    0,     0,    -16,     0,    0,     0,    -7,     0    ],
  [  0,  1,   0,  -2, 0,  0,  0,  0,    0,  0,    0,  16,       0,    0,      0,    0,     0,    15,      0,    1,     0,    7,      0    ],
  [  0,  0,   0,  0,  0,  0,  1,  0,    0,  0,    0,  16,       0,    0,      0,    1,     0,    -15,     0,    -3,    0,    -6,     0    ],
  [  0,  1,   0,  1,  0,  0,  0,  0,    0,  0,    0,  11,       0,    -1,     0,    -1,    0,    -10,     0,    -1,    0,    -5,     0    ],
  [  2,  -2,  0,  0,  0,  0,  0,  0,    0,  0,    0,  0,        0,    -11,    0,    -10,   0,    0,       0,    -4,    0,    0,      0    ],
  [  0,  1,   0,  -1, 0,  0,  0,  0,    0,  0,    0,  -11,      0,    -2,     0,    -2,    0,    9,       0,    -1,    0,    4,      0    ],
  [  0,  4,   0,  0,  0,  0,  0,  0,    0,  0,    0,  -7,       0,    -8,     0,    -8,    0,    6,       0,    -3,    0,    3,      0    ],
  [  0,  3,   0,  -2, 0,  0,  0,  0,    0,  0,    0,  -10,      0,    0,      0,    0,     0,    9,       0,    0,     0,    4,      0    ],
  [  1,  -2,  0,  0,  0,  0,  0,  0,    0,  0,    0,  -9,       0,    0,      0,    0,     0,    -9,      0,    0,     0,    -4,     0    ],
  [  2,  -3,  0,  0,  0,  0,  0,  0,    0,  0,    0,  -9,       0,    0,      0,    0,     0,    -8,      0,    0,     0,    -4,     0    ],
  [  0,  0,   0,  0,  2,  0,  0,  0,    0,  0,    0,  0,        0,    -9,     0,    -8,    0,    0,       0,    -3,    0,    0,      0    ],
  [  2,  -4,  0,  0,  0,  0,  0,  0,    0,  0,    0,  0,        0,    -9,     0,    8,     0,    0,       0,    3,     0,    0,      0    ],
  [  0,  3,   -2, 0,  0,  0,  0,  0,    0,  0,    0,  8,        0,    0,      0,    0,     0,    -8,      0,    0,     0,    -3,     0    ],
  [  0,  0,   0,  0,  0,  0,  0,  1,    2,  -1,   0,  8,        0,    0,      0,    0,     0,    -7,      0,    0,     0,    -3,     0    ],
  [  8,  -12, 0,  0,  0,  0,  0,  0,    0,  0,    0,  -4,       0,    -7,     0,    -6,    0,    4,       0,    -3,    0,    2,      0    ],
  [  8,  -14, 0,  0,  0,  0,  0,  0,    0,  0,    0,  -4,       0,    -7,     0,    6,     0,    -4,      0,    3,     0,    -2,     0    ],
  [  0,  0,   2,  0,  0,  0,  0,  0,    0,  0,    0,  -6,       0,    -5,     0,    -4,    0,    5,       0,    -2,    0,    2,      0    ],
  [  3,  -4,  0,  0,  0,  0,  0,  0,    0,  0,    0,  -1,       0,    -1,     0,    -2,    0,    -7,      0,    1,     0,    -4,     0    ],
  [  0,  2,   0,  -2, 0,  0,  0,  0,    0,  0,    0,  4,        0,    -6,     0,    -5,    0,    -4,      0,    -2,    0,    -2,     0    ],
  [  3,  -3,  0,  0,  0,  0,  0,  0,    0,  0,    0,  0,        0,    -7,     0,    -6,    0,    0,       0,    -3,    0,    0,      0    ],
  [  0,  2,   -2, 0,  0,  0,  0,  0,    0,  0,    0,  5,        0,    -5,     0,    -4,    0,    -5,      0,    -2,    0,    -2,     0    ],
  [  0,  0,   0,  0,  0,  0,  0,  1,    -2, 0,    0,  5,        0,    0,      0,    0,     0,    -5,      0,    0,     0,    -2,     0    ]]


export function earthVelocity(jd) {
    let T = (jd - 2451545) / 36525.0;
    let L20 = 3.1761467 + 1021.3285546 * T;
    let L30 = 1.7534703 + 628.3075849 * T;
    let L40 = 6.2034809 + 334.0612431 * T;
    let L50 = 0.5995465 + 52.9690965 * T;
    let L60 = 0.8740168 + 21.3299095 * T;
    let L70 = 5.4812939 + 7.4781599 * T;
    let L80 = 5.3118863 + 3.8133036 * T;
    let Ldash0 = 3.8103444 + 8399.6847337 * T;
    let D0 = 5.1984667 + 7771.3771486 * T;
    let Mdash0 = 2.3555559 + 8328.6914289 * T;
    let F0 = 1.6279052 + 8433.4661601 * T;

    let velZ = 0.0;
    let velY = 0.0;
    let velX = 0.0;
    
    for(let i=0; i < aberrationCoefficients.length; i++) {
        let coeffs = aberrationCoefficients[i];
        let L2 = coeffs[0];
        let L3 = coeffs[1];
        let L4 = coeffs[2];
        let L5 = coeffs[3];
        let L6 = coeffs[4];
        let L7 = coeffs[5];
        let L8 = coeffs[6];
        let Ldash = coeffs[7];
        let D = coeffs[8];
        let Mdash = coeffs[9];
        let F = coeffs[10];
        let xsin = coeffs[11];
        let xsint = coeffs[12];
        let xcos = coeffs[13];
        let xcost = coeffs[14];
        let ysin  = coeffs[15];
        let ysint = coeffs[16];
        let ycos  = coeffs[17];
        let ycost = coeffs[18];
        let zsin  = coeffs[19];
        let zsint = coeffs[20];
        let zcos  = coeffs[21];
        let zcost = coeffs[22];
        
        let arg = L2*L20 + L3*L30 + L4*L40 + L5*L50 + L6*L60 + L7*L70 + L8*L80 + Ldash*Ldash0 + D*D0 + Mdash*Mdash0 + F*F0;
        
        velX = velX + (xsin + xsint * T) * Math.sin(arg);
        velX = velX + (xcos + xcost * T) * Math.cos(arg);

        velY = velY + (ysin + ysint * T) * Math.sin(arg);
        velY = velY + (ycos + ycost * T) * Math.cos(arg);

        velZ = velZ + (zsin + zsint * T) * Math.sin(arg);
        velZ = velZ + (zcos + zcost * T) * Math.cos(arg);
    }
        
    return [velX, velY, velZ];
    
}
    
export function equatorialAberration(ra, dec, jd) {
    //Convert to radians
    let Alpha = deg2rad(ra*15.0);
    let Delta = deg2rad(dec);

    let cosAlpha = Math.cos(Alpha);
    let sinAlpha = Math.sin(Alpha);
    let cosDelta = Math.cos(Delta);
    let sinDelta = Math.sin(Delta);

    let vel = earthVelocity(jd);
    let velX = vel[0];
    let velY = vel[1];
    let velZ = vel[2];

    let raAb = rad2deg((velY * cosAlpha - velX * sinAlpha) / ( 17314463350.0 * cosDelta))/15.0;
    let decAb = rad2deg(- (((velX * cosAlpha + velY * sinAlpha) * sinDelta - velZ * cosDelta) / 17314463350.0));

    return [raAb, decAb];
}



// String.prototype.format = String.prototype.f = export function() {
//     let s = this,
//         i = arguments.length;

//     while (i--) {
//         s = s.replace(new RegExp('\\{' + i + '\\}', 'gm'), arguments[i]);
//     }
//     return s;
// };

// Array.range= export function(a, b, step){
//     let A= [];
//     if(typeof a== 'number'){
//         A[0]= a;
//         step= step || 1;
//         while(a+step<= b){
//             A[A.length]= a+= step;
//         }
//     }
//     else{
//         let s= 'abcdefghijklmnopqrstuvwxyz';
//         if(a=== a.toUpperCase()){
//             b=b.toUpperCase();
//             s= s.toUpperCase();
//         }
//         s= s.substring(s.indexOf(a), s.indexOf(b)+ 1);
//         A= s.split('');        
//     }
//     return A;
// }

export function radians(x) {
    return x * (Math.PI/180.0);
}

export function degrees(x) {
    return x * (180.0/Math.PI);
}

export function cosd(x) {
    return Math.cos( x * (Math.PI/180.0) );
}

export function sind(x) {
    return Math.sin( x * (Math.PI/180.0) );
}

export function sep(h1, v1, h2, v2) {
   /*
    Determine the angle in degrees between the two points on a sphere (h1, v1) and (h2, v2)
    
    h1: horizontal-like spherical coordinate of first point in degrees (ra, longitude, azimuth)
    v1: vertical-like spherical coordinate of first point in degrees (dec, latitude, elevation)
    h2: horizontal-like spherical coordinate of second point in degrees (ra, longitude, azimuth)
    v2: vertical-like spherical coordinate of second point in degrees (dec, latitude, elevation)
    */
    h1 = radians(h1);
    v1 = radians(v1);
    h2 = radians(h2);
    v2 = radians(v2);
    
    let deltaH = h2 - h1;
    
    let numerator = Math.sqrt(Math.pow(Math.cos(v2)*Math.sin(deltaH),2.0) + Math.pow(Math.cos(v1)*Math.sin(v2)-Math.sin(v1)*Math.cos(v2)*Math.cos(deltaH), 2.0));
    let denominator = Math.sin(v1)*Math.sin(v2) + Math.cos(v1)*Math.cos(v2)*Math.cos(deltaH);
    
    return degrees(Math.atan2(numerator, denominator));
    
}
    
    
export function sepRaDec(ra1, dec1, ra2, dec2) {
    /*
    Determine the angle in degrees between the two points in equatorial coordinate.
    Shorthand for sep(ra1*15.0, dec1, ra2*15.0, dec2)
    
    ra1: RA of first coordinate
    dec1: Dec of first coordinate
    ra2: RA of second coordinate
    dec2: Dec of second coordinate
    */
    
    return sep(ra1*15.0, dec1, ra2*15.0, dec2);
}



/* SkySlalib */



export function gast(jdUtc) {
    /*
    jd: UTC julian day; if None, use current time
    Returns Greenwich Apparent Sidereal Time in hours
    */
    
    if(jdUtc == null) {
        jdUtc = jdNow();
    }
        
    let mjdTT = utcToDynamical(jdUtc) - 2400000.5   //this should be TDB, but difference is so small, ignore for now
    
    return gmst(jdUtc) + degrees(sla_eqeqx(mjdTT))/15.0;
}   
    
export function last(lng, jdUtc) {
    /*
    lng: Longitude of observer in degrees
    jd: UTC julian day; if None, use current time
    Returns Local Apparent Sidereal Time in hours
    */
    
    return rerange(gast(jdUtc) + lng/15.0, 0, 24);
    
}

export function utcToDynamical(jdUtc) {
    var mjd = jdUtc - 2400000.5;
    return mjd + sla_dtt(mjd)/86400.0 + 2400000.5;
    
}

export function planetApparentRaDecSize(id, lng, lat, jdUtc) {
    if(id <0 || id > 9) {
        id = 0;
    }
    
    if(jdUtc == null) {
        jdUtc = jdNow();
    }
    
    if(lng == null || lat == null) {
        lng = 0.0;
        lat = 0.0;
    }
        
    var jdDynam = utcToDynamical(jdUtc);
    var mjdDynam = jdDynam - 2400000.5;
    var result = sla_rdplan(mjdDynam, id, radians(lng), radians(lat));
    var ra = result[0];
    var dec = result[1];
    var diam = result[2];
    
    return [degrees(ra)/15.0, degrees(dec), degrees(diam)];
    
}

export function moonPhase(sunRaHours, sunDecDegs, moonRaHours, moonDecDegs) {
    /*Determines the phase of the moon expressed as a percentage of
     illumination. */
     
    var sepRads = sla_dsep(radians(sunRaHours*15.0), radians(sunDecDegs), radians(moonRaHours*15.0), radians(moonDecDegs)); 
    /* Convert angular separation into percentage illumination */
    var phase = ( 1.0 - Math.cos(sepRads) ) / 2.0;
    var phaseAngle = degrees(sepRads);
    
    
    //calculate the position angle of the midpoint of the illuminate limb of the Moon 
    //see Astronomical Algorithms pg 346
    var a0 = radians(sunRaHours*15.0);
    var d0 = radians(sunDecDegs);
    var a = radians(moonRaHours*15.0);
    var d = radians(moonDecDegs);
    var num = Math.cos(d0)*Math.sin(a0-a);
    var denom = Math.sin(d0)*Math.cos(d) - Math.cos(d0)*Math.sin(d)*Math.cos(a0-a);
    var x = Math.atan2(num, denom);
    
    
    return [phase, phaseAngle, degrees(x)];
}

export function parallacticAngle(raHours, decDegs, lngDegs, latDegs) {
    var jd = jdNow();
    var lst = last(lngDegs, jd);
    var haRads = radians((lst - raHours)*15.0);
    var decRads = radians(decDegs);
    var latRads = radians(latDegs);

    var pa = sla_pa(haRads, decRads, latRads);
    return degrees(pa);
    
    // num = Math.sin(haRads);
    // denom = Math.tan(latRads)*Math.cos(decRads)-Math.sin(decRads)*Math.cos(haRads)
    // if(num == 0 && denom == 0) num = 1.0;
    // return degrees(Math.atan2(num, denom));
    
    
    
    
}

export function range(a, b, step){
    let A: Array<number>= [];
    A[0]= a;
    step= step || 1;
    while(a+step<= b){
        A[A.length]= a+= step;
    }
    return A;
}