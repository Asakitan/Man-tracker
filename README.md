# Man-tracker

A real-time human detection and tracking system powered by YOLOv8 and ByteTrack, featuring advanced pose estimation and tracking capabilities.

## Features

- Real-time human detection using YOLOv8
- Multi-object tracking with ByteTrack algorithm
- Pose estimation with 17 keypoint detection (COCO format)
- Kalman filter-based motion prediction
- Interactive GUI built with PyQt6
- Video source support (camera, video files, screen capture)
- Enemy detection through red edge recognition
- Customizable aim curve and mouse control
- FPS counter and performance monitoring
- Model obfuscation support

## Architecture

```
Man-tracker/
├── app/                    # Application layer
│   └── video_processor.py  # Video processing pipeline
├── config/                 # Configuration management
│   └── settings.py         # Global settings and parameters
├── core/                   # Core functionality
│   ├── detector.py         # YOLOv8 detection engine
│   ├── tracker.py          # ByteTrack tracking algorithm
│   ├── aim_curve.py        # Aim smoothing curves
│   ├── mouse_controller.py # Mouse input control
│   └── kmbox_net.py        # KMBox network interface
├── gui/                    # GUI components
│   ├── main_window.py      # Main application window
│   ├── settings_panel.py   # Settings control panel
│   ├── video_widget.py     # Video display widget
│   ├── skeleton_widget.py  # Skeleton visualization
│   └── hotkey_listener.py  # Hotkey management
├── utils/                  # Utility modules
│   ├── model_manager.py    # Model loading and management
│   ├── screen_capture.py   # Screen capture utilities
│   ├── video_source.py     # Video input abstraction
│   └── visualizer.py       # Detection visualization
└── main.py                 # Application entry point
```

## Requirements

- Python 3.8+
- CUDA-capable GPU (recommended for real-time performance)
- Windows/Linux/macOS

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Asakitan/Man-tracker.git
cd Man-tracker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Place your YOLOv8 pose model file (e.g., `v13341.pt`) in the project root directory.

## Usage

Run the application:
```bash
python main.py
```

### Configuration

Settings are stored in `config_user.json` and can be modified through the GUI or manually:

- Detection confidence threshold
- Tracking parameters (IOU threshold, hit/miss counts)
- Target skeleton point selection
- Aim curve parameters
- Hotkey bindings
- Video source selection

## Key Components

### Detection
The detector module uses YOLOv8-pose for simultaneous human detection and pose estimation, providing:
- Bounding box coordinates
- Confidence scores
- 17 keypoints per person (COCO format)
- Red edge detection for enemy identification

### Tracking
ByteTrack algorithm provides robust multi-object tracking:
- Kalman filter for motion prediction
- ID assignment and management
- Track lifecycle handling
- Lost track recovery

### Pose Estimation
17 keypoint COCO format skeleton:
- Nose, eyes, ears
- Shoulders, elbows, wrists
- Hips, knees, ankles

Each keypoint includes (x, y, confidence) coordinates.

## Development

### Model Training
Train your own YOLOv8 pose model using the Ultralytics framework and place it in the project root.

### Obfuscation
Use `obfuscate_model.py` to protect your trained models:
```bash
python obfuscate_model.py
```

### Debug Mode
Enable debug visualization with `debug_torch.py` to verify model loading and inference.

## Dependencies

Core libraries:
- ultralytics >= 8.0.0 (YOLOv8)
- torch >= 2.0.0
- torchvision >= 0.15.0
- opencv-python >= 4.8.0
- PyQt6 >= 6.5.0
- filterpy >= 1.4.5 (Kalman filter)
- scipy >= 1.10.0
- numpy >= 1.24.0

## License

This project is provided as-is for educational and research purposes.

## Credits

Built with:
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)
- [ByteTrack](https://github.com/ifzhang/ByteTrack)
- PyQt6 for the GUI framework

## Disclaimer

This tool is intended for educational and research purposes only. Users are responsible for ensuring their use complies with applicable laws and terms of service.
