"""
Test script to verify boresight discontinuity fix.
Run this from the AntennaPatternViewer directory.
"""
import numpy as np
from swe.core import SphericalWaveExpansion, compute_pole_limits

print("=" * 60)
print("Testing Boresight Discontinuity Fix")
print("=" * 60)

# Verify the fix is present
print("\n1. Checking if code changes are active...")
import inspect
source = inspect.getsource(compute_pole_limits)
if 'mP_sign' in source and 'dP_sign' in source:
    print("   [OK] Updated compute_pole_limits() is active")
else:
    print("   [ERROR] Code changes not detected! Old version may be cached.")
    print("   Try deleting __pycache__ folders and restarting Python.")

# Test pole limits
print("\n2. Testing pole limit calculations...")
for pole in ['north', 'south']:
    for n, m in [(1, 1), (2, 1), (3, 1)]:
        mP_lim, dP_lim = compute_pole_limits(n, m, pole)
        print(f"   n={n}, m={m}, {pole}: mP={mP_lim:+.4f}, dP={dP_lim:+.4f}")

# Test far-field pattern
print("\n3. Testing far-field pattern continuity...")
freq = 9.8e9
Q1_coeffs = {}
Q2_coeffs = {}

# Create realistic mode distribution
for n in range(1, 21):
    for m in range(-min(n, 5), min(n, 5) + 1):
        mag = np.exp(-0.1 * n) * np.exp(-0.2 * abs(m))
        Q1_coeffs[(n, m)] = mag
        Q2_coeffs[(n, m)] = 0.5 * mag

swe = SphericalWaveExpansion(Q1_coeffs, Q2_coeffs, frequency=freq)

theta_rad = np.radians(np.linspace(0, 180, 181))
phi_rad = np.zeros_like(theta_rad)
E_theta, E_phi = swe.far_field(theta_rad, phi_rad)
power = np.abs(E_theta)**2 + np.abs(E_phi)**2
gain_db = 10 * np.log10(power + 1e-30)

# Check discontinuities
diff_0_1 = abs(gain_db[0] - gain_db[1])
diff_1_2 = abs(gain_db[1] - gain_db[2])
diff_end = abs(gain_db[-1] - gain_db[-2])
diff_end2 = abs(gain_db[-2] - gain_db[-3])

print(f"\n   Gain at theta=0:   {gain_db[0]:.2f} dB")
print(f"   Gain at theta=1:   {gain_db[1]:.2f} dB")
print(f"   Gain at theta=179: {gain_db[-2]:.2f} dB")
print(f"   Gain at theta=180: {gain_db[-1]:.2f} dB")

print(f"\n   Delta (0 to 1 deg):   {diff_0_1:.4f} dB")
print(f"   Delta (1 to 2 deg):   {diff_1_2:.4f} dB")
print(f"   Delta (178 to 179):   {diff_end2:.4f} dB")
print(f"   Delta (179 to 180):   {diff_end:.4f} dB")

# Verdict
print("\n4. Verdict:")
boresight_ok = diff_0_1 < 2 * diff_1_2 + 0.1  # Allow some tolerance
backlobe_ok = diff_end < 2 * diff_end2 + 0.5  # Back lobe has more variation

if boresight_ok and backlobe_ok:
    print("   [PASS] No discontinuities detected - fix is working!")
else:
    if not boresight_ok:
        print(f"   [FAIL] Boresight discontinuity: {diff_0_1:.2f} dB jump at theta=0")
    if not backlobe_ok:
        print(f"   [FAIL] Back lobe discontinuity: {diff_end:.2f} dB jump at theta=180")

print("\n" + "=" * 60)
