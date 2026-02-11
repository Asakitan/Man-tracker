"""
Configuration module
"""
import json
from dataclasses import dataclass, field, asdict
from typing import Tuple, Optional, Dict
from enum import Enum
from pathlib import Path


class SkeletonPoint(Enum):
    """Skeleton point definitions (COCO format)"""
    NOSE = 0
    LEFT_EYE = 1
    RIGHT_EYE = 2
    LEFT_EAR = 3
    RIGHT_EAR = 4
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_HIP = 11
    RIGHT_HIP = 12
    LEFT_KNEE = 13
    RIGHT_KNEE = 14
    LEFT_ANKLE = 15
    RIGHT_ANKLE = 16


def _build_point_names() -> Dict:
    """Build skeleton point display names from encoded data"""
    from utils.obfuscation import _s
    _keys = [
        "nose", "leye", "reye", "lear", "rear",
        "lshoulder", "rshoulder", "lelbow", "relbow",
        "lwrist", "rwrist", "lhip", "rhip",
        "lknee", "rknee", "lankle", "rankle",
    ]
    return {SkeletonPoint(i): _s(k) for i, k in enumerate(_keys)}


# Lazy-loaded skeleton point names
_SKELETON_POINT_CN_CACHE = None

def _get_skeleton_point_cn() -> Dict:
    global _SKELETON_POINT_CN_CACHE
    if _SKELETON_POINT_CN_CACHE is None:
        _SKELETON_POINT_CN_CACHE = _build_point_names()
    return _SKELETON_POINT_CN_CACHE


class _SkeletonPointCNProxy:
    """Proxy that lazily loads the skeleton point CN map"""
    def get(self, key, default=''):
        return _get_skeleton_point_cn().get(key, default)
    def __getitem__(self, key):
        return _get_skeleton_point_cn()[key]
    def __contains__(self, key):
        return key in _get_skeleton_point_cn()
    def items(self):
        return _get_skeleton_point_cn().items()
    def keys(self):
        return _get_skeleton_point_cn().keys()
    def values(self):
        return _get_skeleton_point_cn().values()


SKELETON_POINT_CN = _SkeletonPointCNProxy()


@dataclass
class DetectorConfig:
    model_path: str = "model-pose.pt"
    conf_threshold: float = 0.5
    iou_threshold: float = 0.45
    device: str = "cuda"
    imgsz: int = 320
    half_precision: bool = True
    detect_interval: int = 2            # Run detection every N frames (higher = less GPU)
    red_edge_filter: bool = False
    max_det: int = 10                   # Max detections per frame
    debug_red_edge: bool = False        # Show red edge detection debug overlay


@dataclass
class TrackerConfig:
    track_thresh: float = 0.5
    track_buffer: int = 30
    match_thresh: float = 0.8
    min_box_area: int = 10
    frame_rate: int = 30


@dataclass
class MouseConfig:
    target_skeleton_point: SkeletonPoint = SkeletonPoint.NOSE
    target_track_id: Optional[int] = None
    smoothing_factor: float = 2.0
    enable_mouse_control: bool = True
    screen_margin: int = 10
    coordinate_mapping: str = "relative"
    mouse_speed: float = 1.0
    mouse_backend: str = "kmbox"
    auto_click_enabled: bool = False
    arrival_threshold: float = 5.0
    auto_click_interval: float = 0.1    # Base interval between clicks (seconds)
    auto_click_jitter: float = 0.02     # Random jitter ± (seconds)


@dataclass
class KmboxConfig:
    enabled: bool = False
    ip: str = "192.168.2.188"
    port: int = 8312
    mac: str = "12345678"
    timeout: float = 0.5


@dataclass
class AimCurveConfig:
    """Humanized aim curve settings."""
    curve_mode: str = "hybrid"              # bezier / missile / hybrid
    bezier_aggression: float = 0.6          # 0.0-1.0
    missile_gain: float = 3.0               # PN navigation constant
    accel_factor: float = 0.55              # velocity ramp-up (higher = faster response)
    decel_distance: float = 50.0            # px to start braking
    max_velocity: float = 120.0             # hard cap px/frame
    jitter_amount: float = 0.8              # random micro-jitter px
    overshoot_chance: float = 0.05          # probability 0-1
    target_ema_alpha: float = 0.65          # target smoothing (higher = more responsive)
    hybrid_switch_dist: float = 80.0        # missile→bezier threshold
    interpolation_enabled: bool = True      # smooth interpolation between frames
    interpolation_steps: int = 3            # micro-steps per frame
    interpolation_interval: float = 0.002   # delay between micro-steps (seconds)


@dataclass
class VideoConfig:
    source: str = ""
    output_path: Optional[str] = None
    show_preview: bool = True
    save_video: bool = False
    fps: int = 30
    process_scale: float = 0.5
    # source memory
    source_type: str = "file"
    screen_region: Optional[Tuple[int, int, int, int]] = None
    screen_fps: int = 30
    window_title: str = ""
    window_fps: int = 30


@dataclass
class VisualizationConfig:
    draw_skeleton: bool = True
    draw_bbox: bool = True
    draw_track_id: bool = True
    draw_target_point: bool = True
    draw_red_edge_debug: bool = False   # Show red edge detection mask overlay
    skeleton_color: Tuple[int, int, int] = (0, 255, 0)
    bbox_color: Tuple[int, int, int] = (255, 0, 0)
    target_color: Tuple[int, int, int] = (0, 0, 255)
    text_color: Tuple[int, int, int] = (255, 255, 255)
    line_thickness: int = 2


@dataclass
class HotkeyBinding:
    key: str = ""
    secondary_key: str = ""
    mode: str = "toggle"


@dataclass
class HotkeyConfig:
    toggle_tracking: HotkeyBinding = field(default_factory=lambda: HotkeyBinding("F5", "", "hold"))
    quit: HotkeyBinding = field(default_factory=lambda: HotkeyBinding("esc", "", "toggle"))
    toggle_auto_click: HotkeyBinding = field(default_factory=lambda: HotkeyBinding("F7", "", "toggle"))
    toggle_visibility: HotkeyBinding = field(default_factory=lambda: HotkeyBinding("F8", "", "toggle"))
    increase_smoothing: HotkeyBinding = field(default_factory=lambda: HotkeyBinding("up", "", "hold"))
    decrease_smoothing: HotkeyBinding = field(default_factory=lambda: HotkeyBinding("down", "", "hold"))
    increase_speed: HotkeyBinding = field(default_factory=lambda: HotkeyBinding("right", "", "hold"))
    decrease_speed: HotkeyBinding = field(default_factory=lambda: HotkeyBinding("left", "", "hold"))


@dataclass
class AppConfig:
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    mouse: MouseConfig = field(default_factory=MouseConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    kmbox: KmboxConfig = field(default_factory=KmboxConfig)
    aim_curve: AimCurveConfig = field(default_factory=AimCurveConfig)

    def to_dict(self) -> Dict:
        d = {}
        for section_name in ("detector", "tracker", "mouse", "video", "visualization", "hotkeys", "kmbox", "aim_curve"):
            section = asdict(getattr(self, section_name))
            # handle SkeletonPoint enum
            for k, v in section.items():
                if isinstance(v, SkeletonPoint):
                    section[k] = v.name
            d[section_name] = section
        # asdict converts SkeletonPoint to its value int, fix it
        if "target_skeleton_point" in d.get("mouse", {}):
            sp = self.mouse.target_skeleton_point
            d["mouse"]["target_skeleton_point"] = sp.name
        return d

    def save(self, path: str):
        data = self.to_dict()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "AppConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, config_dict: Dict) -> "AppConfig":
        # handle mouse SkeletonPoint
        mouse_dict = dict(config_dict.get("mouse", {}))
        if "target_skeleton_point" in mouse_dict:
            val = mouse_dict["target_skeleton_point"]
            if isinstance(val, str):
                mouse_dict["target_skeleton_point"] = SkeletonPoint[val]
            elif isinstance(val, int):
                mouse_dict["target_skeleton_point"] = SkeletonPoint(val)
        # handle visualization tuples
        vis_dict = dict(config_dict.get("visualization", {}))
        for key in ("skeleton_color", "bbox_color", "target_color", "text_color"):
            if key in vis_dict and isinstance(vis_dict[key], list):
                vis_dict[key] = tuple(vis_dict[key])

        # handle hotkeys (legacy str or new dict format)
        hotkeys_dict = dict(config_dict.get("hotkeys", {}))
        hotkey_kwargs = {}
        # Only load fields that exist in current HotkeyConfig
        _valid_hotkey_fields = {f.name for f in HotkeyConfig.__dataclass_fields__.values()}
        for k, v in hotkeys_dict.items():
            if k not in _valid_hotkey_fields:
                continue  # skip removed hotkey fields from old configs
            if isinstance(v, str):
                hotkey_kwargs[k] = HotkeyBinding(key=v, mode="toggle")
            elif isinstance(v, dict):
                # Filter dict to only valid HotkeyBinding fields
                valid_binding_keys = {'key', 'secondary_key', 'mode'}
                filtered = {bk: bv for bk, bv in v.items() if bk in valid_binding_keys}
                hotkey_kwargs[k] = HotkeyBinding(**filtered)
            elif isinstance(v, HotkeyBinding):
                hotkey_kwargs[k] = v

        # handle kmbox config
        kmbox_dict = dict(config_dict.get("kmbox", {}))

        # handle aim_curve config — filter unknown fields
        aim_curve_dict = dict(config_dict.get("aim_curve", {}))
        _valid_ac_fields = {f.name for f in AimCurveConfig.__dataclass_fields__.values()}
        aim_curve_dict = {k: v for k, v in aim_curve_dict.items() if k in _valid_ac_fields}

        # handle video config — filter unknown fields & convert screen_region
        video_dict = dict(config_dict.get("video", {}))
        _valid_video_fields = {f.name for f in VideoConfig.__dataclass_fields__.values()}
        video_dict = {k: v for k, v in video_dict.items() if k in _valid_video_fields}
        if "screen_region" in video_dict and isinstance(video_dict["screen_region"], list):
            video_dict["screen_region"] = tuple(video_dict["screen_region"])

        # handle detector config — filter unknown fields
        det_dict = dict(config_dict.get("detector", {}))
        _valid_det_fields = {f.name for f in DetectorConfig.__dataclass_fields__.values()}
        det_dict = {k: v for k, v in det_dict.items() if k in _valid_det_fields}

        return cls(
            detector=DetectorConfig(**det_dict),
            tracker=TrackerConfig(**config_dict.get("tracker", {})),
            mouse=MouseConfig(**mouse_dict),
            video=VideoConfig(**video_dict),
            visualization=VisualizationConfig(**vis_dict),
            hotkeys=HotkeyConfig(**hotkey_kwargs),
            kmbox=KmboxConfig(**kmbox_dict),
            aim_curve=AimCurveConfig(**aim_curve_dict),
        )

    @classmethod
    def from_dict(cls, config_dict: Dict) -> "AppConfig":
        return cls._from_dict(config_dict)
