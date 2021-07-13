import gi
import sys
import math

gi.require_version('Gst', '1.0')

from load_from_api import get_camera_uri
from gi.repository import GObject, Gst, GLib


def _get_stream_urls(argv):
    return get_camera_uri(argv[1])


def __decodebin_child_added(child_proxy, Object, name, userdata):
    if (name.find("decodebin") != -1):
        Object.connect(
            "child-added", __decodebin_child_added,
            userdata
        )
    elif name.find("source") != -1:
        Object.set_property(
            "drop-on-latency",
            1
        )
        Object.set_property(
            "latency",
            1000
        )
        # Object.set_property(
        #     "protocols",
        #     "tcp"
        # )


def _fix_callbacks(pipeline, sources):
    for i, source in enumerate(sources):
        source_name = 'source_bin_{:02d}'.format(i)
        uridecodebin_element = pipeline.get_child_by_name(source_name)
        uridecodebin_element.connect('child-added', __decodebin_child_added, sources)


def _generate_pipeline(stream_urls, width, height, framerate, font):
    grid = math.ceil(math.sqrt(len(stream_urls)))

    pipeline = (
        'videomixer name=mix' +
        ' ! queue ! videoconvert' +
        ' ! xvimagesink sync=0'
    )

    for i, source in enumerate(stream_urls):
        x = i % grid
        y = i // grid

        pipeline += (
            ' uridecodebin name=source_bin_{:02d} uri="{}" ! queue'.format(
                i, source[1]
            ) +
            ' ! videoscale add-borders=0 ! videoconvert ! videorate' +
            ' ! textoverlay text="{}" font-desc="Ubuntu, {}"'.format(
                source[0], font
            ) +
            ' ! capsfilter' +
            ' caps="video/x-raw, width={},'.format(
                width
            ) +
            ' height={}, framerate={}/1"'.format(
                height, framerate
            ) +
            ' ! alpha alpha=1' +
            ' ! videobox border-alpha=0 top={} left={}'.format(
                y * -1 * height, x * -1 * width
            ) +
            ' ! queue ! mix.'
        )

    return pipeline


def _run_pipeline(pipeline_string, stream_urls):
    Gst.init(None)
    mainloop = GLib.MainLoop()
    pipeline = Gst.parse_launch(pipeline_string)
    _fix_callbacks(pipeline, stream_urls)
    pipeline.set_state(Gst.State.PLAYING)
    mainloop.run()


if __name__ == "__main__":
    width = 640
    height = 360
    framerate = 25
    font = 20

    stream_urls = _get_stream_urls(sys.argv)

    pipeline_string = _generate_pipeline(
        stream_urls, width, height, framerate, font
    )

    print(pipeline_string)

    _run_pipeline(pipeline_string, stream_urls)
