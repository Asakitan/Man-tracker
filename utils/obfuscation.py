"""
Data transformation utilities
"""
import base64 as _b64

# Entropy seed for data transformation
_K = b'\x5a\x3c\x7f\x1d\xa2\xe8\x4b\x91\xd3\x6e\xb5\x08\xf7\x44\x2a\xc9'

# Encoded data table
_T = {
    "nose": "s4DE+A94",
    "leye": "v4vZ+j5U",
    "reye": "v7PM+j5U",
    "lear": "v4vZ9SJb",
    "rear": "v7PM9SJb",
    "lshoulder": "v4vZ9SBB",
    "rshoulder": "v7PM9SBB",
    "lelbow": "v4vZ9SBw",
    "relbow": "v7PM9SBw",
    "lwrist": "v4vZ+ytjoxRG",
    "rwrist": "v7PM+ytjoxRG",
    "lhip": "v4vZ9Alj",
    "rhip": "v7PM9Alj",
    "lknee": "v4vZ9SR1",
    "rknee": "v7PM9SR1",
    "lankle": "v4vZ9SZyoylO",
    "rankle": "v7PM9SZyoylO",
    "start": "uKrJPYIN9xE2yT7gSPnCcfA=",
    "stop": "uKrfPYINyg01wxc=",
    "pause": "uLPHPYIO0RM27yk=",
    "resume": "uKrJPYIP8DY01Rg=",
    "tab_settings": "uKbmPYIA5S800xs=",
    "tab_skeleton": "qqPZqYLIojt7hx+0",
    "tab_hotkey": "uLDXPYIN9Do14wLhY+o=",
    "skel_tip": "vb7G+CVTrhRghj+KHsSjL9GVl6IfAPM7OsQd4V34zUvj",
    "menu_file": "vKr4+RleY7eVRw==",
    "menu_save": "voPi+A9wohReiQim",
    "menu_load": "v7bf9R9VohReiQimFcSM",
    "menu_exit": "s7z/+CVSY7eLRw==",
    "menu_help": "v4TR+ChBY7ebRw==",
    "menu_about": "v7nM+Rhm",
    "fps_default": "HGwsJ4IKywU=",
    "track_zero": "soPC9RpCcbHj",
    "skelpt": "s5bX9AhUrBNqVJU=",
    "mouse_on": "s4Df+wJvcbE2/hrvY+w=",
    "mouse_off": "s4Df+wJvcbE0yDTvY+w=",
    "state_ready": "uKvwPUdY+nZoxA==",
    "warn_source": "spPI+Cdgoz9tiQimH+OsIPitmacyC8sT",
    "warn_window": "spPI+CdgohFaiD6hEN+EL/q7mLc1DcQyMO43",
    "hint": "vLPv+gZS",
    "state_loading": "uKvwPUdi63lu01OgVqG0Qri82Q==",
    "state_running": "uKvwPUpX23ly4lGwWg==",
    "state_paused": "uKvwPUdf+XdJ7FCJaw==",
    "state_done": "uKvwPUdf+XR94lOAZw==",
    "state_hold": "uKvwPUdY+nZoxFq0f6KmQL6B8PgdQ60cZIchphH7qi/uh5ChKw==",
    "cfg_saved": "s7ny+h9GriZhigqVEumy",
    "save_fail": "voPi+A9wrjVihgGt",
    "load_fail": "v7bf9R9VrjVihgGt",
    "loaded": "v4vN+ChIoyxuVJU=",
    "about_title": "v7nM+Rhm",
    "err_title": "v5j7+jJuogVKhhqn",
    "json_filter": "EG8wU4LAYb+5Hdpm3n8RL9O8mYErDt0WN9UDKN9uAw==",
    "load_cfg": "v7bf9R9VohReiQim",
    "cur_sel": "v4Hs+CtlohFaiD6hzWQ=",
    "src_group": "spv59AB5rStD",
    "src_type": "vIbv+hNTrg9YVA==",
    "src_file": "spv59AB5rQdUig6+2KK7Tb+/8PgGXA==",
    "src_screen": "v43w+Bt9rh1piyqX",
    "src_window": "vZbo+C1LrRxGhju/",
    "browse": "vInw9QVgqRF1",
    "fullscreen": "v7nX+BNnpC1big2zEdyULv6GmoQKB/cY",
    "cap_fps": "vLHq9Sxfril0iTuPzQ==",
    "sel_region": "s7z2+ylBrh1piyqXFcSM",
    "fullscr_btn": "v7nX+BNn",
    "refresh": "v7TI+zRY",
    "save_output": "voPi+A9woy9AizKyH+OsIPit",
    "output_path": "soLs+CVSoyZ8iwuM12zPRvXV/5SL",
    "model_group": "vJTe+Dxjryldhhu2EuCt",
    "model_label": "vJTe+DxjcQ==",
    "device_label": "spLB+AZvcQ==",
    "imgsz_label": "vLLX+jJuriFpixqwzQ==",
    "fp16": "HGxOK4INxhs03AvtTeLFddJ7L0hHYut4U/FatH4=",
    "det_interval": "vJ//+xdjogZnhy+c36GSbnMG",
    "det_group": "vJ//+xdjrh5RiCC4",
    "conf_label": "vYHR+R1Jrit1hy2AEsSW8w==",
    "scale_label": "v5j7+jJurC16iCG2zQ==",
    "mouse_group": "s4Df+wJvrR90iz2+",
    "mouse_enable": "v6zQ+jZAoi1ziBWPEcqNLNKK",
    "smooth_label": "v4XM+xl5rit1VA==",
    "speed_label": "s7zg+BhOrhFeiTuPzQ==",
    "map_label": "v6Hv+wJvrQlziwWMzQ==",
    "tid_label": "soPC9RpCrAp9iBWP1w1u8w==",
    "auto": "srvV+ChA",
    "kmbox_group": "EXE9UvrFBdSHTl2mSaGOTg==",
    "backend_label": "s4Df+wJvrgFdiR6nzQ==",
    "ip_label": "E2xf+D5YrgxTVA==",
    "port_label": "vZfQ+C1LcQ==",
    "mac_label": "F308Jw==",
    "connect": "soPh+yxN",
    "disconnect": "vKrS+B5o",
    "connected": "v4vN9R12rR92TleUZA==",
    "disconnected": "vKDV9R12rR92",
    "vis_group": "v7PQ9QVurh1F",
    "show_skel": "vKTB+gZSojt7hx+0",
    "show_bbox": "vKTB+gZSoy9qiSCEEeWs",
    "show_tid": "vKTB+gZSoy5uhg2i1w1u",
    "show_target": "vKTB+gZSrAp9iBWPEMaTLN26mqIh",
    "sel_video": "s7z2+ylBozZVhxeZEdKtLeGK",
    "save_video_dlg": "voPi+A9woy9AizKyH+OsIPit",
    "region_dlg": "vJ359CJhriBciwydEsiQLMWj",
    "vid_filter": "spv59AB5rQdUig6+12wA5zdMSz2Ixirnuk6fJpovXOlwEhJy1Mhhv7UCwyjdal2kLBVEJkRhy3dP51OecKCRf3oUVTQ=",
    "mp4_filter": "F2xLPYrCZfyjWpwzzAV8gHoUVTPDniK46FVTgXeitkC8qvj5GV5ruflH",
    "src_placeholder": "spv59AB5rQdUig6+H/OFLOS4X/sqfmt3QupQi3ihjn29iN34Hn1rueNClTnbZMhJ/BU=",
    "no_pywin32": "tYD39D5orj9ahhaN1zRTvjNSTC9NVMI=",
    "no_window": "tYD3+z5CrRhtiz24EO69LNWfkKEr",
    "ip_ph": "spLB+AZva9iDTp1EtAAKL8KCmLkYwQ==",
    "mac_ph": "YtjCkEdlynRWw123bKGif3oUM17myK0JbYkRst4=",
    "send_input": "CVkReeuGO+SnTp1fnioZ+3M=",
    "det_tip": "vJPwU0dQ7Hls/l2pe6CSSbyQ3vsBaK0kWIEJhBP8hyDNiJqlBQ3vHDT6HexPzsxl+9vEjkR213JT7F2+faGObh1sKvgvSKwFe4YDghP5pA==",
    "hk_tracking": "v4D/+AVjZHRS8lOlVayVdLKE1Q==",
    "hk_pause": "vKb9+CN0ZHZoyVKzWg==",
    "hk_mouse": "v7T4+y9Koi1ziBWPEcqNLNKK",
    "hk_skeleton": "v7T4+y9Kojt7hx+0EMaT",
    "hk_quit": "s7z/+CVS",
    "hk_inc_smooth": "v57h+AZPrihgiA6Z",
    "hk_dec_smooth": "v7vw+BJnrihgiA6Z",
    "hk_inc_speed": "v57h+AZPohFMiw+u",
    "hk_dec_speed": "v7vw+BJnohFMiw+u",
    "mode_always": "v4TH+B5o",
    "mode_hold": "vLD2+R9nrAVMiCCA",
    "mode_toggle": "v4D/+Cdb",
    "hk_reset": "vL3d+AZloipLhhus",
    "hk_func": "v7bg9SFV",
    "hk_key": "vLD29DZG",
    "hk_mode": "vJTe+B5n",
    "ml": "s4Df+wJvriZ1hyGm",
    "mr": "s4Df+wJvrh5ghyGm",
    "mm": "s4Df+wJvryl+hyGm",
    "mx1": "s4Df+wJvry90hyGmxmzPWdTV/52L",
    "mx2": "s4Df+wJvry90hyGmxWzPQNfUwIaL",
    "vid_preview": "qqPspILIozZVhxeZHuauIf20mpEYDdQO",
    "vid_hint": "s7z2+ylBozZVhxeZEf66LOOKmJ8bDcwqMO457UvEz27R1MCgSlDhclPj",
    "hide_show": "s6bv9TVnZHdL0FKsTaOAXr+z3A==",
    "kmbox_ok": "EXE9UvrFBdSHTl23aaKkbLyJ9PUNfa0ZQ4s/lw==",
    "kmbox_fail": "EXE9UvrFBdSHTl23aaKkbL+YzvUWTQ==",
    "kmbox_err": "EXE9UvrFBdSHTlycbqyFZmAc",
    "kmbox_disc": "EXE9UvrFBdSHTlC/RaK8ZL+A/w==",
    "region_fmt": "v7DF+D13cbH7Fcgk1z9X4HpHAt41kzY=",
    "red_filter": "vYbd9Staoy9qiQmQEsGjLvenlp0r",
    "red_filter_tip": "vof69R1Voyl5iw2uEdijLuCel5QQAPUoNNIt7XLNzVPe2MWnRWHifm/iXbdwopFtvKvf+hhKrhRaiS6mEeSt",
}

# Decoded cache
_C = {}


def _d(encoded: str) -> str:
    """Transform encoded data back to original form"""
    x = _b64.b64decode(encoded)
    return bytes([x[i] ^ _K[i % len(_K)] for i in range(len(x))]).decode('utf-8')


def _e(plain: str) -> str:
    """Transform plaintext to encoded form (dev utility)"""
    b = plain.encode('utf-8')
    x = bytes([b[i] ^ _K[i % len(_K)] for i in range(len(b))])
    return _b64.b64encode(x).decode('ascii')


def _s(key: str) -> str:
    """Retrieve decoded string by key"""
    if key not in _C:
        _C[key] = _d(_T[key])
    return _C[key]
