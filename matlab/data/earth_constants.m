function constants = earth_constants()
%EARTH_CONSTANTS  Physical constants for mission analysis.

constants.mu_km3_s2 = 398600.4418;   % Earth's gravitational parameter [km^3/s^2]
constants.re_km = 6378.137;          % Equatorial radius [km]
constants.j2 = 1.08263e-3;           % J2 coefficient [-]
constants.omega_earth = 7.2921159e-5; % Earth rotation rate [rad/s]

constants.au_km = 149597870.7;       % Astronomical unit [km]
constants.solar_pressure = 4.56e-6;  % Solar radiation pressure at 1 AU [N/m^2]
constants.solar_flux = 1361.0;       % Solar flux [W/m^2]
end
