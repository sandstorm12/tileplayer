# tileplayer
A simpler multi-video file and stream player based on GStreamer

![](images/sample_image.png)


## Notice
This is a personal project under development. Bug reports and feature requests are appriciated.

## Installation

### Prerequisites
1. GStreamer 1.x
2. Python 3.x

```bash
python3 -m pip install git+https://github.com/sandstorm12/tileplayer
```

## Usage

Using config file
```bash
# Generate sample config file
tileplayer -g config.yaml
# Run tileplayer using the sample configs
tileplayer -c config.yaml
```

Directly passing streams:
```bash
tileplayer -i [file or stream uri ...]
tileplayer -i file:///path/to/video/file file:///path/to/video/file ...
tileplayer -i rtsp://stream_address rtsp://stream_address ...
```

Refer to sample config file or help to check available options:
```bash
tileplayer -g /tmp/config.yaml | less
tileplayer -h
```


## Sample config
```yaml
streams:
  -
    # Optional
    text: "FPS=5"
    # Mandatory
    uri: "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov"
    # Optional
    fps: 5
    # Optional
    text_size: 30
  -
    text: "FPS=10"
    uri: "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov"
    fps: 10
    text_size: 30
```

## Run using docker image (tested on ubuntu)

Build the docker image
```bash
docker build -f dockerfile_x86 -t tileplayer .
```

Give desktop environment access for docker to connect
```bash
xhost +
```

Run docker container
```bash
docker run -it --rm --env="DISPLAY" -v /tmp/.X11-unix:/tmp/.X11-unix tileplayer bash
```

Run tileplayer sample
```bash
# Generate sample config file
tileplayer -g config.yaml
# Run tileplayer using the sample configs
tileplayer -c config.yaml
```

## Urgent issues and future work
1. Fully separate core api from UI script

## Issues and future work
1. Add the protocol, latency, and drop-on-latency config per stream
2. FIX: GStreamer critical error. Pipeline is not in NULL state.
3. Add more interesting grid placement.
4. FIX: Warning: .gobject/gsignal.c:2736: instance A has no handler with id B
5. Add output stream feature
6. Add a waiting image instead of the grid background
7. Add pause functionality
8. Caps changin method is not efficient
9. Use logger
10. Add fps change on input selection
11. Add library documentation
12. Add window size change functionality
13. Add gif instead of current image
14. More sample config to resourcs folder
