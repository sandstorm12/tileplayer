import gi
import sys
import math
import yaml
import argparse

gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst, GLib


def _get_arguments():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-c', '--config',
        help=(
            'A yaml config file containing stream or file URIs'
            ' and playback information'
        ),
        type=str,
        default=None
    )
    group.add_argument(
        '-i', '--inputs',
        type=str,
        nargs='+',
        help='List of input stream or file URIs',
        default=None
    )
    parser.add_argument(
        '-f', '--fps',
        help='Playback fps',
        type=int,
        default=25
    )
    parser.add_argument(
        '-p', '--protocol',
        help=(
            'Protocol for camera connection if inputs'
            ' are streams. Cound be "auto", "tcp", or'
            ' "udp". Default is "tcp"'
        ),
        type=str,
        default="tcp"
    )
    parser.add_argument(
        '-w', '--width',
        help=(
            'Tile width. Default: 640'
        ),
        type=int,
        default=640
    )
    parser.add_argument(
        '-a', '--height',
        help=(
            'Tile height. Default: 360'
        ),
        type=int,
        default=360
    )
    parser.add_argument(
        '-t', '--text_size',
        help=(
            'Overlay text size. Default: 30'
        ),
        type=int,
        default=30
    )
    parser.add_argument(
        '-l', '--low_latency',
        help=(
            'Apply latency limit on decoder. Default: False'
        ),
        type=bool,
        default=False
    )

    args = parser.parse_args()

    return args


def _get_input_uris(args):
    uris = None
    if uris is None and args.config is not None:
        uris = _load_uris_from_config(args.config)

    if uris is None and args.inputs is not None:
        uris = []
        for uri in args.inputs:
            uris.append({"uri": uri})

    return uris


def _load_uris_from_config(config_path):
    with open(config_path, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)

    if not config.__contains__("streams"):
        raise Exception("Key \"streams\" not found in config file")

    return config["streams"]


def __decodebin_child_added(child_proxy, Object, name, inputs):
    if (name.find("decodebin") != -1):
        Object.connect(
            "child-added", __decodebin_child_added,
            inputs
        )
    elif name.find("source") != -1:
        if args.low_latency:
            Object.set_property(
                "drop-on-latency",
                1
            )
            Object.set_property(
                "latency",
                1000
            )
        if args.protocol != "auto":
            Object.set_property(
                "protocols",
                args.protocol
            )


def _fix_callbacks(pipeline, inputs):
    for i, source in enumerate(inputs):
        source_name = 'source_bin_{:02d}'.format(i)
        uridecodebin_element = pipeline.get_child_by_name(source_name)
        uridecodebin_element.connect('child-added', __decodebin_child_added, args)


def _generate_pipeline(inputs, args):
    grid = math.ceil(math.sqrt(len(inputs)))

    pipeline = (
        'compositor name=mix' +
        ' ! videoconvert' +
        ' ! autovideosink sync=1'
    )

    for i, source in enumerate(inputs):
        x = i % grid
        y = i // grid

        width = inputs[i].get("width", args.width)
        height = inputs[i].get("height", args.height)

        pipeline += (
            ' uridecodebin name=source_bin_{:02d} uri="{}"'.format(
                i, inputs[i]["uri"]
            ) +
            ' ! videoscale add-borders=0 ! videoconvert ! videorate' +
            ' ! capsfilter' +
            ' caps="video/x-raw, width={},'.format(
                width   
            ) +
            ' height={}, framerate={}/1"'.format(
                height,
                inputs[i].get("fps", args.fps)
            ) +
            ' ! textoverlay text="{}" font-desc="Ubuntu, {}"'.format(
                inputs[i].get("text", ""),
                inputs[i].get("text_size", args.text_size)
            ) +
            ' ! alpha alpha=1' +
            ' ! videobox border-alpha=0 top={} left={}'.format(
                y * -1 * height, x * -1 * width
            ) +
            ' ! mix.'
        )

    return pipeline


def _run_pipeline(pipeline_string, inputs):
    Gst.init(None)
    mainloop = GLib.MainLoop()
    pipeline = Gst.parse_launch(pipeline_string)
    _fix_callbacks(pipeline, inputs)
    pipeline.set_state(Gst.State.NULL)
    pipeline.set_state(Gst.State.PLAYING)
    mainloop.run()


if __name__ == "__main__":
    args = _get_arguments()

    uris = _get_input_uris(args)
    if uris is None:
        raise Exception('Unable to obtain input list.')
    else:
        for uri in uris:
            print("Playing: {}".format(uri))

    pipeline_string = _generate_pipeline(
        uris, args
    )

    print(pipeline_string)

    _run_pipeline(pipeline_string, uris)
