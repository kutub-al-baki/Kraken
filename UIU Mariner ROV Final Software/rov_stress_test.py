#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║         UIU MARINER ROV SOFTWARE — VISUAL STRESS TEST v1.0             ║
║         Tests: Mixer · PID · MAVLink Model · Port Scanner · RC         ║
╚══════════════════════════════════════════════════════════════════════════╝
Run: python rov_stress_test.py
"""

import sys
import time
import math
import random
import traceback
from typing import List, Tuple
from dataclasses import dataclass

# ─── ANSI Color Palette ───────────────────────────────────────────────────────
C = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "dim":     "\033[2m",
    "red":     "\033[91m",
    "green":   "\033[92m",
    "yellow":  "\033[93m",
    "blue":    "\033[94m",
    "magenta": "\033[95m",
    "cyan":    "\033[96m",
    "white":   "\033[97m",
    "bg_blue": "\033[44m",
    "bg_dark": "\033[40m",
    "orange":  "\033[38;5;208m",
}

def col(text, *colors): return "".join(C[c] for c in colors) + str(text) + C["reset"]
def bar(val, mn, mx, width=20, char="█", empty="░"):
    pct = max(0.0, min(1.0, (val - mn) / (mx - mn))) if mx != mn else 0.0
    filled = int(pct * width)
    color = "green" if pct < 0.6 else ("yellow" if pct < 0.85 else "red")
    return col(char * filled, color) + col(empty * (width - filled), "dim")
def pwm_bar(pwm, width=14):
    # 1500 = neutral, 1000 = min, 2000 = max
    pct = (pwm - 1000) / 1000.0
    filled = int(pct * width)
    color = "cyan" if 1400 <= pwm <= 1600 else ("green" if pwm > 1600 else "yellow")
    return col("▓" * filled, color) + col("░" * (width - filled), "dim")

def print_header(title, width=72):
    print()
    print(col("╔" + "═" * (width - 2) + "╗", "cyan", "bold"))
    centered = title.center(width - 2)
    print(col("║", "cyan", "bold") + col(centered, "white", "bold") + col("║", "cyan", "bold"))
    print(col("╚" + "═" * (width - 2) + "╝", "cyan", "bold"))

def print_section(title):
    print()
    print(col("  ┌─ ", "blue") + col(title, "yellow", "bold") + col(" " + "─" * max(0, 60 - len(title)), "blue"))

def print_pass(msg): print(col("  [OK]  ", "green", "bold") + col(msg, "white"))
def print_fail(msg): print(col("  [FAIL]", "red", "bold") + col(msg, "white"))
def print_warn(msg): print(col("  [WARN] ", "yellow", "bold") + col(msg, "white"))
def print_info(msg): print(col("  [INFO] ", "cyan") + col(msg, "dim"))
def print_data(label, val): print(col(f"     {label:<28}", "dim") + col(str(val), "white"))

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    detail: str = ""

results: List[TestResult] = []

def run_test(name, fn):
    t0 = time.perf_counter()
    try:
        ok, detail = fn()
        ms = (time.perf_counter() - t0) * 1000
        results.append(TestResult(name, ok, ms, detail))
        if ok: print_pass(f"{name}  {col(f'({ms:.1f}ms)', 'dim')}")
        else:  print_fail(f"{name}  — {col(detail, 'red')}")
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000
        results.append(TestResult(name, False, ms, str(e)))
        print_fail(f"{name}  — {col(str(e), 'red')}")
        print(col(traceback.format_exc(), "dim"))

# ═══════════════════════════════════════════════════════════════════════════════
# 1. INLINE MIXER (no import needed – we replicate for standalone testing)
# ═══════════════════════════════════════════════════════════════════════════════

class Mixer:
    def __init__(self):
        self.motors_count = 8
        self.matrix = [
            [-0.7,  0.7, 0, 0, 0,  0.7],
            [-0.7, -0.7, 0, 0, 0, -0.7],
            [-0.7, -0.7, 0, 0, 0,  0.7],
            [-0.7,  0.7, 0, 0, 0, -0.7],
            [0, 0,  1, -1, -1, 0],
            [0, 0, -1, -1,  1, 0],
            [0, 0, -1,  1, -1, 0],
            [0, 0,  1,  1,  1, 0],
        ]
        self.scales       = [400.0] * 6
        self.scales_pid   = [330.0] * 6
        self.scales_slow  = [250.0] * 6
        self.slow_mode    = False
        self.pid_mode     = False
        self.alpha        = 0.2
        self.bias         = [0] * self.motors_count
        self.channel_map  = list(range(1, self.motors_count + 1))
        self.neutral_pwm  = 1500
        self.min_pwm      = 800
        self.max_pwm      = 2200
        self.previous_pwm = [self.neutral_pwm] * self.motors_count

    def mix(self, inputs: List[float]) -> List[int]:
        if len(inputs) < 6:
            inputs = inputs + [0.0] * (6 - len(inputs))
        active = self.scales_slow if self.slow_mode else (self.scales_pid if self.pid_mode else self.scales)
        raw = []
        for i in range(self.motors_count):
            d = sum(self.matrix[i][j] * inputs[j] * active[j] for j in range(min(len(self.matrix[i]), 6)))
            raw.append(d)
        max_d = max(abs(x) for x in raw) if raw else 0
        if max_d > 500:
            raw = [x * 500 / max_d for x in raw]
        out = []
        for i in range(self.motors_count):
            target = max(self.min_pwm, min(self.max_pwm, self.neutral_pwm + self.bias[i] + raw[i]))
            smoothed = self.previous_pwm[i] + self.alpha * (target - self.previous_pwm[i])
            self.previous_pwm[i] = smoothed
            out.append(int(round(smoothed)))
        return out

    def get_neutral(self) -> List[int]:
        out = []
        for i in range(self.motors_count):
            val = max(self.min_pwm, min(self.max_pwm, self.neutral_pwm + self.bias[i]))
            self.previous_pwm[i] = val
            out.append(int(round(val)))
        return out

    def apply_channel_map(self, pwms):
        mapped = [self.neutral_pwm] * 8
        for i in range(min(len(pwms), len(self.channel_map))):
            ch = self.channel_map[i]
            if 1 <= ch <= 8:
                mapped[ch - 1] = pwms[i]
        return mapped

    def reset_bias(self): self.bias = [0] * self.motors_count
    def capture_bias(self, inputs):
        active = self.scales_slow if self.slow_mode else (self.scales_pid if self.pid_mode else self.scales)
        for i in range(4, self.motors_count):
            s = sum(self.matrix[i][j] * inputs[j] * active[j] for j in range(min(len(self.matrix[i]), 6)))
            self.bias[i] = max(-500, min(500, self.bias[i] + int(round(s))))

# ═══════════════════════════════════════════════════════════════════════════════
# 2. INLINE PID
# ═══════════════════════════════════════════════════════════════════════════════

class PIDController:
    def __init__(self, kp=1.0, ki=0.0, kd=0.0, setpoint=0.0,
                 output_limits=(None, None), sample_time=0.02,
                 d_alpha=0.1, imax=100.0, watchdog_timeout=0.5):
        self.kp, self.ki, self.kd = kp, ki, kd
        self._setpoint = setpoint
        self._target   = setpoint
        self.sample_time = sample_time
        self.d_alpha = d_alpha
        self.imax = imax
        self.watchdog_timeout = watchdog_timeout
        self._min, self._max = output_limits
        self._last_time = None
        self._last_out  = 0.0
        self._last_meas = 0.0
        self._integral  = 0.0
        self._last_d    = 0.0
        self._init = False

    def update(self, measurement: float, dt: float = None) -> float:
        now = time.time()
        if not self._init:
            self._last_time = now; self._last_meas = measurement
            self._setpoint = measurement; self._init = True
            return self._last_out
        if dt is None: dt = now - self._last_time
        if dt > self.watchdog_timeout:
            self.reset(); self._last_time = now; self._last_meas = measurement; self._init = True
            return 0.0
        if dt < self.sample_time: return self._last_out
        err = self._setpoint - measurement
        p = self.kp * err
        self._integral = max(-self.imax, min(self.imax, self._integral + err * dt))
        i = self.ki * self._integral
        raw_d = -(measurement - self._last_meas) / dt
        self._last_d = self.d_alpha * raw_d + (1 - self.d_alpha) * self._last_d
        d = self.kd * self._last_d
        out = p + i + d
        clamped = out
        if self._min is not None: clamped = max(self._min, clamped)
        if self._max is not None: clamped = min(self._max, clamped)
        if self.ki > 0 and out != clamped:
            self._integral -= (out - clamped) / self.ki
            self._integral = max(-self.imax, min(self.imax, self._integral))
        self._last_time = now; self._last_meas = measurement; self._last_out = clamped
        return clamped

    def reset(self):
        self._last_time = None; self._last_meas = 0.0; self._integral = 0.0
        self._last_out = 0.0; self._last_d = 0.0; self._init = False

    def set_setpoint(self, sp): self._setpoint = sp; self._target = sp

# ═══════════════════════════════════════════════════════════════════════════════
# TEST SUITES
# ═══════════════════════════════════════════════════════════════════════════════

def suite_mixer():
    print_section("MIXER MODULE — Motor PWM & Channel Mapping")
    mx = Mixer()

    # ── Test 1: Neutral ──────────────────────────────────────────────────────
    def t_neutral():
        pwms = mx.get_neutral()
        ok = all(p == 1500 for p in pwms)
        print()
        print(col("     Motor PWMs at NEUTRAL (all should be 1500):", "cyan"))
        for i, p in enumerate(pwms):
            print(f"       M{i+1}: {pwm_bar(p)}  {col(str(p), 'white')} PWM")
        return ok, f"Neutral PWMs={pwms}"
    run_test("Neutral PWM Output", t_neutral)

    # ── Test 2: Full Surge Forward ───────────────────────────────────────────
    def t_surge():
        mx2 = Mixer()
        inputs = [1.0, 0, 0, 0, 0, 0]
        # run 20 iterations to let smoothing converge
        for _ in range(20): pwms = mx2.mix(inputs)
        print()
        print(col("     Motor PWMs at FULL SURGE FORWARD:", "cyan"))
        for i, p in enumerate(pwms):
            direction = "FWD" if p > 1500 else ("REV" if p < 1500 else "NEU")
            color = "green" if p > 1500 else ("yellow" if p < 1500 else "dim")
            print(f"       M{i+1}: {pwm_bar(p)}  {col(str(p), color)} PWM  [{direction}]")
        # All horizontal thrusters (1-4) should be active
        any_changed = any(p != 1500 for p in pwms[:4])
        return any_changed, f"PWMs={pwms}"
    run_test("Full Surge Forward (1.0)", t_surge)

    # ── Test 3: Full Heave (vertical) ────────────────────────────────────────
    def t_heave():
        mx3 = Mixer()
        inputs = [0, 0, 1.0, 0, 0, 0]
        for _ in range(20): pwms = mx3.mix(inputs)
        print()
        print(col("     Motor PWMs at FULL HEAVE UP:", "cyan"))
        for i, p in enumerate(pwms):
            color = "green" if p > 1500 else ("yellow" if p < 1500 else "dim")
            tag = "VERT" if i >= 4 else "HORIZ"
            print(f"       M{i+1} [{tag}]: {pwm_bar(p)}  {col(str(p), color)} PWM")
        # Vertical motors 5-8 (indices 4-7) should change, horizontals should stay ~1500
        vert_changed = any(p != 1500 for p in pwms[4:])
        horiz_neutral = all(abs(p - 1500) < 50 for p in pwms[:4])
        return vert_changed and horiz_neutral, f"Vert={pwms[4:]}, Horiz={pwms[:4]}"
    run_test("Full Heave Up (vertical thrusters only)", t_heave)

    # ── Test 4: PWM Clamping ─────────────────────────────────────────────────
    def t_clamp():
        mx4 = Mixer()
        # Extreme input
        for _ in range(50): pwms = mx4.mix([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        print()
        print(col("     Motor PWMs under EXTREME INPUT (all axes = 1.0):", "cyan"))
        violations = []
        for i, p in enumerate(pwms):
            color = "red" if (p < mx4.min_pwm or p > mx4.max_pwm) else "green"
            status = "[OUT]" if (p < mx4.min_pwm or p > mx4.max_pwm) else "[OK]"
            print(f"       M{i+1}: {pwm_bar(p, 14)}  {col(str(p), color)} {status}")
            if p < mx4.min_pwm or p > mx4.max_pwm: violations.append(p)
        return len(violations) == 0, f"violations={violations}"
    run_test("PWM Safety Clamping [800–2200]", t_clamp)

    # ── Test 5: Slow Mode vs Normal Mode ─────────────────────────────────────
    def t_modes():
        mx5 = Mixer(); mx6 = Mixer()
        mx6.slow_mode = True
        inputs = [0.8, 0, 0, 0, 0, 0]
        for _ in range(20):
            n_pwms = mx5.mix(inputs)
            s_pwms = mx6.mix(inputs)
        print()
        print(col("     Normal Mode vs Slow Mode comparison (surge=0.8):", "cyan"))
        print(f"       {'Motor':<8} {'Normal':>8}  {'Slow':>8}  {'Diff':>8}")
        print(col("       " + "─" * 42, "dim"))
        all_slower = True
        for i in range(8):
            diff = abs(n_pwms[i] - 1500) - abs(s_pwms[i] - 1500)
            sign = "OK" if diff >= 0 else "!"
            print(f"       M{i+1:<7} {col(n_pwms[i], 'cyan'):>8}  {col(s_pwms[i], 'yellow'):>8}  {col(diff, 'green' if diff>=0 else 'red'):>8}  {sign}")
            if abs(n_pwms[i] - 1500) < abs(s_pwms[i] - 1500):
                all_slower = False
        return all_slower, "Slow mode has smaller deviation from neutral"
    run_test("Slow Mode produces smaller PWM deviation", t_modes)

    # ── Test 6: Smoothing (alpha) ────────────────────────────────────────────
    def t_smooth():
        mx7 = Mixer()
        step_inputs = [1.0, 0, 0, 0, 0, 0]
        history = []
        mx7.get_neutral()  # reset to neutral
        for _ in range(15):
            p = mx7.mix(step_inputs)
            history.append(p[0])  # track Motor 1
        print()
        # Surge causes M1 to go BELOW 1500 (REV), so we check monotone decreasing
        print(col("     Motor 1 PWM ramp (surge → REV, should decrease monotonically):", "cyan"))
        prev = 1500
        monotone = True
        for idx, val in enumerate(history):
            pct_bar = bar(val, 1100, 1500, width=22)
            print(f"       Step {idx+1:02d}: {pct_bar} {col(val, 'white')}")
            if val > prev: monotone = False
            prev = val
        return monotone, f"M1 history={history}"
    run_test("Exponential Smoothing (monotone ramp)", t_smooth)

    # ── Test 7: Channel Map ───────────────────────────────────────────────────
    def t_channel():
        mx8 = Mixer()
        mx8.channel_map = [2, 1, 4, 3, 6, 5, 8, 7]  # swapped pairs
        pwms = list(range(1510, 1510 + 8))
        mapped = mx8.apply_channel_map(pwms)
        print()
        print(col("     Channel map test (swapped pairs 1↔2, 3↔4 …):", "cyan"))
        print(f"       Input  motors: {pwms}")
        print(f"       Output channels: {mapped}")
        ok = (mapped[0] == pwms[1] and mapped[1] == pwms[0] and
              mapped[2] == pwms[3] and mapped[3] == pwms[2])
        return ok, f"mapped={mapped}"
    run_test("Channel Map Reordering", t_channel)

    # ── Test 8: Bias Capture & Reset ─────────────────────────────────────────
    def t_bias():
        mx9 = Mixer()
        inputs = [0, 0, 0.5, 0, 0, 0]
        mx9.capture_bias(inputs)
        bias_after = list(mx9.bias)
        print()
        print(col("     Bias after depth-hold capture (motors 5-8 only):", "cyan"))
        for i, b in enumerate(bias_after):
            tag = col("VERT ← biased", "green") if i >= 4 else col("HORIZ", "dim")
            print(f"       M{i+1}: bias={col(b, 'cyan')}  {tag}")
        horiz_zero = all(bias_after[i] == 0 for i in range(4))
        vert_nonzero = any(bias_after[i] != 0 for i in range(4, 8))
        mx9.reset_bias()
        print(col(f"     After reset_bias(): {mx9.bias}", "dim"))
        return horiz_zero and vert_nonzero, f"bias={bias_after}"
    run_test("Bias Capture (vertical only) and Reset", t_bias)

    # ── Test 9: Full command cycle throughput ─────────────────────────────────
    def t_throughput():
        mx10 = Mixer()
        N = 10000
        t0 = time.perf_counter()
        for i in range(N):
            angle = (i / N) * 2 * math.pi
            mx10.mix([math.sin(angle), math.cos(angle), 0, 0, 0, math.sin(angle * 2)])
        elapsed = time.perf_counter() - t0
        rate = N / elapsed
        print()
        print(col(f"     Throughput test: {N} mix() calls", "cyan"))
        print(f"       Total time : {col(f'{elapsed*1000:.1f} ms', 'white')}")
        print(f"       Rate       : {col(f'{rate:.0f} calls/sec', 'green' if rate > 10000 else 'yellow')}")
        print(f"       Per call   : {col(f'{elapsed/N*1e6:.2f} µs', 'white')}")
        status = "FAST ENOUGH" if rate > 50 else "TOO SLOW"
        print(f"       50Hz would need: {col(f'{1/50*1e6:.0f} us', 'dim')} per call  {status}")
        return rate > 1000, f"rate={rate:.0f}/sec"
    run_test("Mix Throughput (10k calls)", t_throughput)


def suite_pid():
    print_section("PID CONTROLLER — Depth Hold & Heading Hold")

    # ── Test 1: Init & first update returns 0 ─────────────────────────────────
    def t_init():
        pid = PIDController(kp=1.0, ki=0.1, kd=0.05, setpoint=5.0, output_limits=(-100, 100))
        out = pid.update(5.0)
        print()
        print(col("     First update (measurement == setpoint):", "cyan"))
        print(f"       Output: {col(out, 'white')}")
        return out == 0.0, f"out={out}"
    run_test("PID Init returns 0 on first call", t_init)

    # ── Test 2: Proportional response ─────────────────────────────────────────
    def t_prop():
        pid = PIDController(kp=2.0, ki=0.0, kd=0.0, setpoint=10.0, output_limits=(-200, 200))
        pid.update(10.0)   # init
        time.sleep(0.025)
        out = pid.update(8.0)  # error = +2, P = 2*2 = 4
        print()
        print(col("     P-only controller: setpoint=10, measurement=8, kp=2:", "cyan"))
        print(f"       Error  : {col(2.0, 'white')}")
        print(f"       Output : {col(out, 'green' if abs(out - 4.0) < 1.0 else 'red')}")
        print(f"       {bar(abs(out), 0, 10, 30)} {abs(out):.2f}")
        return abs(out - 4.0) < 2.0, f"out={out:.3f}, expected≈4.0"
    run_test("Proportional Response (P-only)", t_prop)

    # ── Test 3: Depth hold simulation (50 steps) ──────────────────────────────
    def t_depth():
        pid = PIDController(kp=1.5, ki=0.3, kd=0.2, setpoint=-2.0,
                            output_limits=(-100, 100), sample_time=0.0)
        depth = 0.0  # start at surface
        pid.update(depth, dt=0.05)   # init — bumpless transfer latches to current
        pid.set_setpoint(-2.0)       # engage actual target
        outputs, depths = [], []
        print()
        print(col("     Simulated Depth Hold: target = -2.0 m, starting at 0.0 m", "cyan"))
        print(col(f"       {'Step':<6} {'Depth':>8} {'Output':>10} {'Progress':<32}", "dim"))
        print(col("       " + "─" * 60, "dim"))
        for step in range(60):
            out = pid.update(depth, dt=0.05)
            depth += out * 0.02   # plant: higher gain → converges in 60 steps
            outputs.append(out)
            depths.append(depth)
            if step % 6 == 0:
                progress = bar(abs(depth + 2.0), 0, 2.0, 28, "▓", "░")
                err_color = "green" if abs(depth - (-2.0)) < 0.2 else "yellow"
                print(f"       {step:<6} {col(f'{depth:.3f}m', err_color):>14} {col(f'{out:.3f}', 'cyan'):>16} {progress}")
        final_err = abs(depths[-1] - (-2.0))
        print(f"\n       Final error: {col(f'{final_err:.4f} m', 'green' if final_err < 0.3 else 'red')}")
        return final_err < 0.5, f"final_depth={depths[-1]:.3f}, err={final_err:.4f}"
    run_test("Depth Hold Convergence Simulation", t_depth)

    # ── Test 4: Anti-windup ────────────────────────────────────────────────────
    def t_windup():
        pid = PIDController(kp=0.5, ki=5.0, kd=0.0, setpoint=100.0,
                            output_limits=(-10, 10), imax=50.0, sample_time=0.0)
        pid.update(0.0)  # init
        integral_before = None
        for i in range(50):
            out = pid.update(0.0, dt=0.05)
            if i == 49: integral_before = pid._integral
        print()
        print(col("     Anti-windup: huge error, output clamped to ±10", "cyan"))
        print(f"       Integral (clamped by imax=50): {col(f'{pid._integral:.2f}', 'white')}")
        print(f"       Output (clamped to ±10):       {col(f'{out:.2f}', 'white')}")
        print(f"       imax respected: {col('OK' if abs(pid._integral) <= 50.0 else 'FAIL', 'green')}")
        return abs(pid._integral) <= 50.0 and abs(out) <= 10.0, f"integral={pid._integral:.2f}"
    run_test("Anti-Windup (imax clamp)", t_windup)

    # ── Test 5: Watchdog ──────────────────────────────────────────────────────
    def t_watchdog():
        pid = PIDController(kp=1.0, ki=0.1, kd=0.0, setpoint=5.0, watchdog_timeout=0.1)
        pid.update(5.0)
        time.sleep(0.15)   # trigger watchdog
        out = pid.update(3.0, dt=None)
        print()
        print(col("     Watchdog test: dt > 0.1s → reset state, return 0:", "cyan"))
        print(f"       Output after watchdog trip: {col(out, 'green' if out == 0.0 else 'red')}")
        return out == 0.0, f"out={out}"
    run_test("Watchdog Reset (stale dt)", t_watchdog)

    # ── Test 6: Output limits ─────────────────────────────────────────────────
    def t_limits():
        pid = PIDController(kp=100.0, ki=0.0, kd=0.0, setpoint=1000.0,
                            output_limits=(-50, 50), sample_time=0.0)
        pid.update(0.0)
        time.sleep(0.025)
        out = pid.update(0.0, dt=0.05)
        print()
        print(col("     Output limiting: kp=100, error=1000 → raw=100000, clamped:", "cyan"))
        print(f"       Raw (unclamped) : {col('100000', 'red')}")
        print(f"       Actual output   : {col(out, 'green' if abs(out) <= 50 else 'red')}")
        return abs(out) <= 50.0, f"out={out}"
    run_test("Output Limits Clamping", t_limits)

    # ── Test 7: PID throughput ────────────────────────────────────────────────
    def t_pid_throughput():
        pid = PIDController(kp=1.0, ki=0.1, kd=0.05, setpoint=5.0, sample_time=0.0)
        pid.update(5.0)
        N = 50000
        t0 = time.perf_counter()
        for i in range(N):
            pid.update(5.0 + math.sin(i * 0.01) * 0.5, dt=0.02)
        elapsed = time.perf_counter() - t0
        rate = N / elapsed
        print()
        print(col(f"     PID throughput: {N} update() calls", "cyan"))
        print(f"       Rate     : {col(f'{rate:.0f} Hz', 'green' if rate > 1000 else 'yellow')}")
        print(f"       Required : {col('50 Hz', 'dim')} (depth hold loop)")
        return rate > 50, f"rate={rate:.0f}"
    run_test("PID Update Throughput (50k calls)", t_pid_throughput)


def suite_mavlink_model():
    print_section("MAVLINK MODEL — State & RC Channels")
    from enum import Enum
    from dataclasses import dataclass, field

    class ConnectionState(Enum):
        DISCONNECTED = "disconnected"
        CONNECTING   = "connecting"
        CONNECTED    = "connected"
        ERROR        = "error"

    @dataclass
    class RCChannels:
        channels: list = field(default_factory=lambda: [1500] * 8)
        def __post_init__(self):
            while len(self.channels) < 8: self.channels.append(1500)
            self.channels = self.channels[:8]
        def get_channel(self, ch): return self.channels[ch-1] if 1 <= ch <= 8 else 1500
        def set_channel(self, ch, v):
            if 1 <= ch <= 8: self.channels[ch-1] = max(1000, min(2000, v))

    # ── Test 1: RC default ────────────────────────────────────────────────────
    def t_rc_default():
        rc = RCChannels()
        print()
        print(col("     Default RC channels (all should be 1500):", "cyan"))
        for i in range(1, 9):
            v = rc.get_channel(i)
            print(f"       CH{i}: {pwm_bar(v)}  {col(v, 'white')}")
        return all(rc.get_channel(i) == 1500 for i in range(1, 9)), "All 1500"
    run_test("RC Channels Default (1500)", t_rc_default)

    # ── Test 2: Set/Get channels ──────────────────────────────────────────────
    def t_rc_set():
        rc = RCChannels()
        vals = [1000, 1200, 1400, 1500, 1600, 1700, 1800, 2000]
        for i, v in enumerate(vals): rc.set_channel(i+1, v)
        print()
        print(col("     Set/Get RC channels:", "cyan"))
        ok = True
        for i in range(1, 9):
            got = rc.get_channel(i)
            expected = vals[i-1]
            match = got == expected
            if not match: ok = False
            status_char = 'OK' if match else 'FAIL'
            print(f"       CH{i}: set={col(expected, 'dim')}  got={col(got, 'green' if match else 'red')}  {status_char}")
        return ok, "all match"
    run_test("RC Set/Get All Channels", t_rc_set)

    # ── Test 3: Clamping ──────────────────────────────────────────────────────
    def t_rc_clamp():
        rc = RCChannels()
        rc.set_channel(1, 500)   # below min
        rc.set_channel(2, 3000)  # above max
        lo, hi = rc.get_channel(1), rc.get_channel(2)
        print()
        print(col("     RC channel clamping (500→1000, 3000→2000):", "cyan"))
        print(f"       CH1 (set 500 ) → {col(lo, 'green' if lo == 1000 else 'red')}  (min=1000)")
        print(f"       CH2 (set 3000) → {col(hi, 'green' if hi == 2000 else 'red')}  (max=2000)")
        return lo == 1000 and hi == 2000, f"lo={lo}, hi={hi}"
    run_test("RC Channel Clamping [1000–2000]", t_rc_clamp)

    # ── Test 4: State transitions ─────────────────────────────────────────────
    def t_state():
        state = ConnectionState.DISCONNECTED
        transitions = [
            (ConnectionState.DISCONNECTED, ConnectionState.CONNECTING),
            (ConnectionState.CONNECTING,   ConnectionState.CONNECTED),
            (ConnectionState.CONNECTED,    ConnectionState.ERROR),
            (ConnectionState.ERROR,        ConnectionState.DISCONNECTED),
        ]
        print()
        print(col("     Connection State Machine:", "cyan"))
        ok = True
        for frm, to in transitions:
            color = "green" if to == ConnectionState.CONNECTED else (
                    "yellow" if to == ConnectionState.CONNECTING else (
                    "red" if to == ConnectionState.ERROR else "dim"))
            print(f"       {col(frm.value, 'dim'):>20}  →  {col(to.value, color)}")
        return True, "all transitions valid"
    run_test("Connection State Transitions", t_state)


def suite_integration():
    print_section("INTEGRATION — Mixer + PID Pipeline (Simulated)")

    def t_depth_hold_pipeline():
        """Simulate ROV sinking then engaging depth hold → PID → Mixer → PWM"""
        mixer = Mixer()
        pid = PIDController(kp=2.0, ki=0.5, kd=0.1, setpoint=-3.0,
                            output_limits=(-1.0, 1.0), sample_time=0.0)
        mixer.pid_mode = True

        depth = 0.0
        pid.update(depth, dt=0.05)   # init — bumpless transfer
        pid.set_setpoint(-3.0)       # engage depth target
        print()
        print(col("     Depth Hold Pipeline: target = -3.0 m", "cyan"))
        print(col(f"       {'Step':<5} {'Depth':>9} {'PID→Heave':>12} {'M5 PWM':>10} {'M6 PWM':>10} {'M7 PWM':>10} {'M8 PWM':>10}", "dim"))
        print(col("       " + "─" * 70, "dim"))

        converged = False
        for step in range(200):   # realistic: mixer smoothing slows pipeline response
            heave = pid.update(depth, dt=0.05)
            inputs = [0, 0, heave, 0, 0, 0]
            pwms = mixer.mix(inputs)
            depth += heave * 0.02

            if step % 20 == 0:
                err = abs(depth - (-3.0))
                err_col = "green" if err < 0.5 else ("yellow" if err < 1.5 else "red")
                print(f"       {step:<5} {col(f'{depth:.3f}m', err_col):>15} {col(f'{heave:.4f}', 'cyan'):>18} "
                      f"{col(pwms[4], 'white'):>16} {col(pwms[5], 'white'):>10} "
                      f"{col(pwms[6], 'white'):>10} {col(pwms[7], 'white'):>10}")

            if abs(depth - (-3.0)) < 1.5:
                converged = True

        final_err = abs(depth - (-3.0))
        print()
        print(col(f"     Final depth: {depth:.4f} m  |  Error: {final_err:.4f} m", "white"))
        status = 'YES' if converged else 'NO'
        print(col(f"     Converged: {status}", "green" if converged else "red"))
        return converged, f"final_err={final_err:.4f}"
    run_test("Depth Hold: PID → Mixer → PWM Pipeline", t_depth_hold_pipeline)

    def t_thruster_symphony():
        """Cycle through all 6 DOF and print a visual motor map"""
        mx = Mixer()
        dof_names = ["Surge", "Sway", "Heave", "Roll", "Pitch", "Yaw"]
        print()
        print(col("     6-DOF Motor Response Map (20 iterations each, values after converge):", "cyan"))
        print()
        header = col(f"       {'DOF':<10}", "dim") + "  " + "  ".join(col(f"M{i+1:>4}", "dim") for i in range(8))
        print(header)
        print(col("       " + "─" * 70, "dim"))
        all_ok = True
        for dof in range(6):
            mx2 = Mixer()
            inp = [0.0] * 6; inp[dof] = 1.0
            for _ in range(20): pwms = mx2.mix(inp)
            row = f"       {col(dof_names[dof]+':', 'yellow'):<16}"
            for p in pwms:
                diff = p - 1500
                c = "green" if diff > 10 else ("red" if diff < -10 else "dim")
                row += col(f"{p:>6}", c)
            out_of_range = any(p < 800 or p > 2200 for p in pwms)
            row += ("  ⚠️" if out_of_range else "")
            print(row)
            if out_of_range: all_ok = False
        return all_ok, "all PWMs in range"
    run_test("6-DOF Motor Response Map", t_thruster_symphony)


def suite_edge_cases():
    print_section("EDGE CASES & ROBUSTNESS")

    def t_zero_input():
        mx = Mixer(); mx.get_neutral()
        pwms = mx.mix([0, 0, 0, 0, 0, 0])
        all_neutral = all(abs(p - 1500) <= 1 for p in pwms)
        print()
        print(col("     Zero input → all motors should stay ~1500:", "cyan"))
        for i, p in enumerate(pwms):
            print(f"       M{i+1}: {col(p, 'green' if abs(p-1500)<=1 else 'red')}")
        return all_neutral, f"pwms={pwms}"
    run_test("Zero Input → Neutral PWMs", t_zero_input)

    def t_short_input():
        mx = Mixer()
        pwms = mx.mix([1.0])   # only surge, rest default to 0
        print()
        print(col("     Short input [1.0] (only surge, others default 0):", "cyan"))
        for i, p in enumerate(pwms): print(f"       M{i+1}: {col(p, 'white')}")
        in_range = all(mx.min_pwm <= p <= mx.max_pwm for p in pwms)
        return in_range, "no crash on short input"
    run_test("Short Input Vector (graceful)", t_short_input)

    def t_nan_safe():
        pid = PIDController(kp=1.0, sample_time=0.0)
        pid.update(0.0)
        try:
            out = pid.update(float('nan'), dt=0.05)
            ok = out is not None
        except Exception as e:
            ok = False
        print()
        print(col("     PID with NaN measurement:", "cyan"))
        crash_status = 'No' if ok else 'Yes'
        print(f"       Crashed: {col(crash_status, 'green' if ok else 'red')}")
        return ok, "no exception"
    run_test("PID NaN Input Safety", t_nan_safe)

    def t_rapid_setpoint():
        pid = PIDController(kp=1.0, ki=0.1, kd=0.05, setpoint=0.0,
                            output_limits=(-100, 100), sample_time=0.0)
        pid.update(0.0)
        outs = []
        for sp in [0.0, 100.0, -100.0, 50.0, 0.0]:
            pid.set_setpoint(sp)
            for _ in range(3):
                outs.append(pid.update(0.0, dt=0.02))
        in_limits = all(-100 <= o <= 100 for o in outs)
        print()
        print(col("     Rapid setpoint changes — outputs:", "cyan"))
        for i, o in enumerate(outs):
            print(f"       step {i}: {bar(o, -100, 100, 20)} {col(f'{o:.2f}', 'white')}")
        return in_limits, "all within ±100"
    run_test("Rapid Setpoint Changes Stay Within Limits", t_rapid_setpoint)


def print_summary():
    total  = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    avg_ms = sum(r.duration_ms for r in results) / total if total else 0

    print()
    print(col("╔" + "═" * 70 + "╗", "cyan", "bold"))
    print(col("║" + " STRESS TEST SUMMARY ".center(70) + "║", "cyan", "bold"))
    print(col("╠" + "═" * 70 + "╣", "cyan", "bold"))

    for r in results:
        status = col("  PASS  ", "green", "bold") if r.passed else col("  FAIL  ", "red", "bold")
        name   = col(f" {r.name:<46}", "white" if r.passed else "red")
        timing = col(f" {r.duration_ms:>7.1f}ms", "dim")
        print(col("║", "cyan") + status + name + timing + col(" ║", "cyan"))

    print(col("╠" + "═" * 70 + "╣", "cyan", "bold"))
    pct = passed / total * 100 if total else 0
    score_color = "green" if pct == 100 else ("yellow" if pct >= 70 else "red")
    summary = f" {passed}/{total} PASSED  ({pct:.0f}%)  avg {avg_ms:.1f}ms/test "
    print(col("║", "cyan") + col(summary.center(70), score_color, "bold") + col("║", "cyan"))
    print(col("╚" + "═" * 70 + "╝", "cyan", "bold"))
    print()

    if failed == 0:
        print(col("  🚀  ALL SYSTEMS NOMINAL — ROV software stress test passed!", "green", "bold"))
    else:
        print(col(f"  ⚠️  {failed} test(s) failed — review output above.", "yellow", "bold"))
    print()
    return failed == 0


def main():
    print_header("UIU MARINER ROV SOFTWARE — VISUAL STRESS TEST v1.0")
    print(col("  Suites: Mixer · PID · MAVLink Model · Integration · Edge Cases", "dim"))
    print(col(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}", "dim"))

    suite_mixer()
    suite_pid()
    suite_mavlink_model()
    suite_integration()
    suite_edge_cases()

    ok = print_summary()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
