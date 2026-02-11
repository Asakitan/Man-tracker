"""
Humanized aim curve engine.

Provides smooth, natural-looking mouse movement using:
  - Quadratic Bezier interpolation between waypoints
  - Missile (proportional-navigation) pursuit curve
  - Velocity-based acceleration / deceleration
  - Random micro-jitter for human imperfection
  - EMA (Exponential Moving Average) target smoothing
"""

import math
import time
import random
from dataclasses import dataclass, field
from typing import Tuple, Optional


@dataclass
class AimCurveConfig:
    """Configuration for humanized aim curves."""

    # ── Curve mode ──
    # "bezier"  — quadratic bezier with adaptive control point
    # "missile" — proportional-navigation pursuit (like a homing missile)
    # "hybrid"  — missile for large offsets, bezier for fine aim
    curve_mode: str = "hybrid"

    # ── Bezier settings ──
    bezier_aggression: float = 0.6      # 0.0-1.0, how aggressively the curve bows
    bezier_steps: int = 5               # Sub-steps per frame (smoothness of curve)

    # ── Missile / PN settings ──
    missile_gain: float = 3.0           # Navigation constant N (2-5 typical)
    missile_max_turn: float = 60.0      # Max turn per frame (pixels)

    # ── Velocity envelope ──
    accel_factor: float = 0.55          # Acceleration ramp-up (0-1), higher = faster response
    decel_distance: float = 50.0        # Distance (px) to start decelerating
    max_velocity: float = 120.0         # Hard cap on pixels per frame
    min_velocity: float = 0.5           # Below this → stop

    # ── Human imperfections ──
    jitter_amount: float = 0.8          # Random micro-jitter in px
    overshoot_chance: float = 0.05      # Probability of slight overshoot per frame
    overshoot_scale: float = 1.15       # How much to overshoot (multiplier)

    # ── EMA target smoothing ──
    target_ema_alpha: float = 0.65      # 0=ignore new, 1=instant update (higher = more responsive)

    # ── Hybrid threshold ──
    hybrid_switch_dist: float = 80.0    # Switch from missile to bezier below this

    # ── Interpolation settings ──
    interpolation_enabled: bool = True  # Enable smooth interpolation between frames
    interpolation_steps: int = 3        # Number of micro-steps per frame
    interpolation_interval: float = 0.002  # Delay between micro-steps (seconds)


class AimCurveEngine:
    """
    Stateful engine that converts raw (target_screen_x, target_screen_y) into
    smooth, human-like per-frame (dx, dy) deltas.

    Call `update(target_x, target_y)` each frame.
    It returns the (dx, dy) integer offsets to send to the KMBOX device.
    
    Supports interpolation: instead of one big move per frame, it can return
    multiple smaller moves for smoother motion.
    """

    def __init__(self, screen_center: Tuple[float, float],
                 config: Optional[AimCurveConfig] = None):
        self.cfg = config or AimCurveConfig()
        self.cx, self.cy = screen_center

        # ── State ──
        self._ema_tx: float = self.cx      # Smoothed target X
        self._ema_ty: float = self.cy      # Smoothed target Y
        self._vel_x: float = 0.0           # Current velocity X
        self._vel_y: float = 0.0           # Current velocity Y
        self._last_time: float = 0.0
        self._accumulated_dx: float = 0.0  # Sub-pixel accumulator
        self._accumulated_dy: float = 0.0
        self._prev_los_angle: float = 0.0  # For missile PN
        
        # ── Interpolation state ──
        self._pending_moves: list = []     # Queue of (dx, dy) micro-moves
        self._last_raw_dx: float = 0.0     # Last computed raw delta
        self._last_raw_dy: float = 0.0

    def reset(self):
        """Reset state (e.g., when switching targets)."""
        self._ema_tx = self.cx
        self._ema_ty = self.cy
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._accumulated_dx = 0.0
        self._accumulated_dy = 0.0
        self._prev_los_angle = 0.0
        self._last_time = 0.0
        self._pending_moves = []
        self._last_raw_dx = 0.0
        self._last_raw_dy = 0.0

    def get_interpolated_moves(self, total_dx: int, total_dy: int) -> list:
        """
        Split a single (dx, dy) into multiple smaller moves for smooth interpolation.
        
        Returns a list of (dx, dy, delay) tuples where delay is the time to wait
        before sending the next move.
        """
        if not self.cfg.interpolation_enabled:
            return [(total_dx, total_dy, 0.0)]
        
        steps = max(1, self.cfg.interpolation_steps)
        
        # Skip interpolation for very small moves
        if abs(total_dx) <= 2 and abs(total_dy) <= 2:
            return [(total_dx, total_dy, 0.0)]
        
        moves = []
        remaining_dx = float(total_dx)
        remaining_dy = float(total_dy)
        
        for i in range(steps):
            # Distribute movement with slight easing (more movement in middle)
            if steps > 1:
                # Use sine easing for smoother distribution
                t = (i + 1) / steps
                ease = math.sin(t * math.pi / 2)  # Ease out
                progress = ease
                prev_progress = math.sin(i / steps * math.pi / 2) if i > 0 else 0.0
                step_ratio = progress - prev_progress
            else:
                step_ratio = 1.0
            
            step_dx = int(round(total_dx * step_ratio))
            step_dy = int(round(total_dy * step_ratio))
            
            # Ensure we don't exceed total
            if i == steps - 1:
                step_dx = int(remaining_dx)
                step_dy = int(remaining_dy)
            else:
                remaining_dx -= step_dx
                remaining_dy -= step_dy
            
            if step_dx != 0 or step_dy != 0:
                delay = self.cfg.interpolation_interval if i < steps - 1 else 0.0
                moves.append((step_dx, step_dy, delay))
        
        return moves if moves else [(0, 0, 0.0)]

    def update(self, target_x: float, target_y: float,
               speed: float = 1.0, smooth: float = 1.0) -> Tuple[int, int]:
        """
        Compute one frame of humanized mouse movement.

        Parameters
        ----------
        target_x, target_y : screen coordinates of the aim target
        speed : user speed multiplier
        smooth : user smoothing factor (higher = slower)

        Returns
        -------
        (dx, dy) : integer pixel offsets to send to device
        """
        now = time.perf_counter()
        dt = now - self._last_time if self._last_time > 0 else 1 / 60
        dt = min(dt, 0.1)  # Cap at 100ms to avoid jumps after stalls
        self._last_time = now

        # ── 1. EMA smooth the target position ──
        # Ensure minimum alpha for responsiveness (prevent too-slow tracking)
        alpha = max(self.cfg.target_ema_alpha, 0.3)  # At least 30% update per frame
        self._ema_tx = self._ema_tx + alpha * (target_x - self._ema_tx)
        self._ema_ty = self._ema_ty + alpha * (target_y - self._ema_ty)

        tx = self._ema_tx
        ty = self._ema_ty

        # ── 2. Error vector (screen center → target) ──
        err_x = tx - self.cx
        err_y = ty - self.cy
        dist = math.hypot(err_x, err_y)

        if dist < self.cfg.min_velocity:
            self._vel_x *= 0.5
            self._vel_y *= 0.5
            return (0, 0)

        # ── 3. Choose curve mode ──
        mode = self.cfg.curve_mode
        if mode == "hybrid":
            mode = "missile" if dist > self.cfg.hybrid_switch_dist else "bezier"

        # ── 4. Compute desired displacement ──
        if mode == "bezier":
            dx, dy = self._bezier_step(err_x, err_y, dist, speed, smooth, dt)
        else:
            dx, dy = self._missile_step(err_x, err_y, dist, speed, smooth, dt)

        # ── 5. Velocity envelope (acceleration / deceleration) ──
        dx, dy = self._apply_velocity_envelope(dx, dy, dist, speed, smooth)

        # ── 6. Human jitter ──
        dx, dy = self._apply_jitter(dx, dy, dist)

        # ── 7. Overshoot chance ──
        if random.random() < self.cfg.overshoot_chance:
            dx *= self.cfg.overshoot_scale
            dy *= self.cfg.overshoot_scale

        # ── 8. Sub-pixel accumulation → integer output ──
        self._accumulated_dx += dx
        self._accumulated_dy += dy

        out_dx = int(self._accumulated_dx)
        out_dy = int(self._accumulated_dy)

        self._accumulated_dx -= out_dx
        self._accumulated_dy -= out_dy

        return (out_dx, out_dy)

    # ─────────────────────────────────────────────
    # Curve implementations
    # ─────────────────────────────────────────────

    def _bezier_step(self, err_x: float, err_y: float, dist: float,
                     speed: float, smooth: float, dt: float) -> Tuple[float, float]:
        """
        Quadratic Bezier: P0 = (0,0), P1 = control point, P2 = (err_x, err_y).
        We only move a fraction `t_step` along the curve per frame.
        """
        smooth_eff = max(smooth, 0.01)

        # How far along the curve to step this frame
        # Ensure minimum step size for responsiveness
        base_step = max(0.15, (speed / smooth_eff) * 0.25)  # At least 15% per frame
        t_step = min(1.0, base_step * (60 * dt))

        # Control point: perpendicular offset for curve shape
        aggr = max(self.cfg.bezier_aggression, 0.1)  # Minimum aggression
        # Perpendicular direction
        perp_x = -err_y / max(dist, 1)
        perp_y = err_x / max(dist, 1)

        # Randomize control point side slightly (but keep consistent per engagement)
        side = 1.0 if (int(self._ema_tx * 7) % 2 == 0) else -1.0
        ctrl_x = err_x * 0.5 + perp_x * dist * aggr * 0.3 * side
        ctrl_y = err_y * 0.5 + perp_y * dist * aggr * 0.3 * side

        # Evaluate quadratic bezier at t_step
        # B(t) = (1-t)² P0 + 2(1-t)t P1 + t² P2
        t = t_step
        bx = 2 * (1 - t) * t * ctrl_x + t * t * err_x
        by = 2 * (1 - t) * t * ctrl_y + t * t * err_y

        return (bx, by)

    def _missile_step(self, err_x: float, err_y: float, dist: float,
                      speed: float, smooth: float, dt: float) -> Tuple[float, float]:
        """
        Proportional Navigation (PN) — like a homing missile.
        Steers proportionally to the rate of change of the line-of-sight angle.
        """
        smooth_eff = max(smooth, 0.01)

        # Current line-of-sight angle
        los_angle = math.atan2(err_y, err_x)

        # LOS rate (angular velocity)
        los_rate = los_angle - self._prev_los_angle
        # Normalize to [-pi, pi]
        while los_rate > math.pi:
            los_rate -= 2 * math.pi
        while los_rate < -math.pi:
            los_rate += 2 * math.pi
        self._prev_los_angle = los_angle

        # PN guidance: acceleration = N * closing_speed * LOS_rate
        # closing_speed approximated by desired speed
        closing_speed = min(dist * 0.3 * speed / smooth_eff, self.cfg.max_velocity)

        # PN lateral acceleration
        N = self.cfg.missile_gain
        accel_lateral = N * closing_speed * los_rate

        # Cap lateral acceleration
        max_turn = self.cfg.missile_max_turn * (60 * dt)
        accel_lateral = max(-max_turn, min(max_turn, accel_lateral))

        # Decompose: move along LOS + lateral correction
        cos_los = math.cos(los_angle)
        sin_los = math.sin(los_angle)

        # Forward component (along line of sight)
        fwd = closing_speed * (60 * dt) * 0.2
        fwd = min(fwd, dist * 0.5)  # Don't overshoot

        # Lateral component (perpendicular correction)
        lat = accel_lateral

        dx = fwd * cos_los - lat * sin_los
        dy = fwd * sin_los + lat * cos_los

        return (dx, dy)

    # ─────────────────────────────────────────────
    # Post-processing
    # ─────────────────────────────────────────────

    def _apply_velocity_envelope(self, dx: float, dy: float,
                                 dist: float, speed: float,
                                 smooth: float) -> Tuple[float, float]:
        """Apply acceleration ramp-up and deceleration near target."""
        mag = math.hypot(dx, dy)
        if mag < 0.001:
            return (dx, dy)

        # Deceleration: ease off as we approach target
        decel_dist = max(self.cfg.decel_distance, 1)
        if dist < decel_dist:
            # Smooth decel: cubic ease-out
            t = dist / decel_dist
            decel_mult = t * t * (3 - 2 * t)  # smoothstep
            dx *= decel_mult
            dy *= decel_mult

        # Acceleration: blend current with previous velocity
        # Ensure minimum acceleration factor for responsiveness
        accel = max(self.cfg.accel_factor, 0.4)  # At least 40% blend per frame
        target_vx = dx
        target_vy = dy
        self._vel_x = self._vel_x * (1 - accel) + target_vx * accel
        self._vel_y = self._vel_y * (1 - accel) + target_vy * accel

        # Hard velocity cap
        v = math.hypot(self._vel_x, self._vel_y)
        max_v = self.cfg.max_velocity * speed / max(smooth, 0.01) * 0.5
        max_v = max(max_v, 1.0)
        if v > max_v:
            scale = max_v / v
            self._vel_x *= scale
            self._vel_y *= scale

        return (self._vel_x, self._vel_y)

    def _apply_jitter(self, dx: float, dy: float,
                      dist: float) -> Tuple[float, float]:
        """Add subtle random jitter that scales down near the target."""
        j = self.cfg.jitter_amount
        if j <= 0:
            return (dx, dy)

        # Jitter reduces as we get closer (more precise near target)
        dist_scale = min(dist / 100.0, 1.0)
        jx = random.gauss(0, j * dist_scale)
        jy = random.gauss(0, j * dist_scale)

        return (dx + jx, dy + jy)
