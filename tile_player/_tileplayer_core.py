import gi
import os
import sys
import time
import math
import yaml
import argparse

gi.require_version('Gst', '1.0')

from threading import Thread
from gi.repository import GObject, Gst, GLib
from ._config_helper import copy_sample_config


class TilePlayer(object):
    _NAME_SELECTOR = "is"

    def __init__(self):
        self.pipeline = None
        self.inputs = None
        self.args = None

    def _add_mandatory_arguments(self, parser):
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
        group.add_argument(
            '-g', '--generate',
            help=(
                'Generate sample config file on the provided path.'
            ),
            type=str,
            default=None
        )

    def _add_format_arguments(self, parser):
        parser.add_argument(
            '-f', '--fps',
            help='Playback fps',
            type=int,
            default=25
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

    def _add_stream_arguments(self, parser):
        parser.add_argument(
            '-p', '--protocol',
            help=(
                'Protocol for camera connection if inputs'
                ' are streams. Cound be "auto", "tcp", or'
                ' "udp". Default is "auto"'
            ),
            type=str,
            default="auto"
        )
        parser.add_argument(
            '-l', '--low_latency',
            help=(
                'Apply latency limit on decoder. Default: False'
            ),
            type=bool,
            default=False
        )

    def _add_overlay_arguments(self, parser):
        parser.add_argument(
            '-t', '--text_size',
            help=(
                'Overlay text size. Default: 30'
            ),
            type=int,
            default=30
        )

    def _add_debug_arguments(self, parser):
        parser.add_argument(
            '-v', '--verbose',
            help=(
                'Print some useful information.'
            ),
            action='store_true'
        )

    def _add_optional_arguments(self, parser):
        self._add_format_arguments(parser)
        self._add_stream_arguments(parser)
        self._add_overlay_arguments(parser)
        self._add_debug_arguments(parser)

    def _get_arguments(self):
        parser = argparse.ArgumentParser()
        
        self._add_mandatory_arguments(parser)
        self._add_optional_arguments(parser)

        args = parser.parse_args()

        return args

    def _get_input_uris(self):
        uris = None
        if uris is None and self.args.config is not None:
            uris = self._load_uris_from_config(self.args.config)

        if uris is None and self.args.inputs is not None:
            uris = []
            for uri in self.args.inputs:
                uris.append({"uri": uri})

        return uris

    def _load_uris_from_config(self, config_path):
        with open(config_path, 'r') as yaml_file:
            config = yaml.safe_load(yaml_file)

        if not config.__contains__("streams"):
            raise Exception("Key \"streams\" not found in config file")

        return config["streams"]

    def __decodebin_child_added(self, child_proxy, Object, name, args):
        if (name.find("decodebin") != -1):
            Object.connect(
                "child-added", self.__decodebin_child_added,
                args
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

    def _fix_callbacks(self):
        for i, source in enumerate(self.inputs):
            source_name = 'source_bin_{:02d}'.format(i)
            uridecodebin_element = self.pipeline.get_child_by_name(
                source_name
            )
            uridecodebin_element.connect(
                'child-added', self.__decodebin_child_added, self.args
            )

    """0: tilePlayer, other integers: other streams"""
    def select_output(self, stream,
            height=None, width=None):
        if self.pipeline is not None:
            selector = self.pipeline.get_by_name(self._NAME_SELECTOR)
            new_pad = selector.get_static_pad(
                "sink_{}".format(stream)
            )
            selector.set_property("active-pad", new_pad)

            self._update_caps(stream, height, width)
        else:
            print("WARNING: pipeline is not generated yet")

    def _update_stream_caps(self, stream, height, width):
        stream_caps = self.pipeline.get_by_name(
            "caps_{:02d}".format(stream)
        )
        
        if stream_caps is not None:
            if height is not None or width is not None:
                caps_old = stream_caps.get_property("caps")
                caps_new = Gst.caps_from_string(str(caps_old))
                
                if width is not None:
                    caps_new.set_value("width", width)
                if height is not None:
                    caps_new.set_value("height", height)
                
                stream_caps.set_property(
                    "caps",
                    caps_new
                )
        else:
            print(f"WARNING: stream {stream} does not exist.")

    def _update_compositor_caps(self, stream, height, width):
        compositor_caps = self.pipeline.get_by_name(
            "caps_00"
        )

        if compositor_caps is not None:
            if height is not None or width is not None:
                caps_old = compositor_caps.get_property("caps")
                caps_new = Gst.caps_from_string(str(caps_old))
                
                if width is not None:
                    caps_new.set_value("width", width)
                if height is not None:
                    caps_new.set_value("height", height)
                
                compositor_caps.set_property(
                    "caps",
                    caps_new
                )
        else:
            print(f"WARNING: compositor does not exist.")

    def _update_caps(self, stream, height, width):
        self._update_stream_caps(stream, height, width)
        self._update_compositor_caps(stream, height, width)

    def _generate_mixer_branch(self):
        mixer_branch = (
            ' input-selector name=is sync-streams=0' +
            ' ! queue ! videoconvert ! videoscale ! videorate ! capsfilter name=caps_00' +
            ' ! xvimagesink name=display sync=1'
            ' compositor name=mix ! is.'
        )

        return mixer_branch

    def _generate_stream_branch(self, index, source, grid):
        x = index % grid
        y = index // grid

        width = self.inputs[index].get("width", self.args.width)
        height = self.inputs[index].get("height", self.args.height)

        stream_branch = (
            ' uridecodebin name=source_bin_{:02d} uri="{}"'.format(
                index, self.inputs[index]["uri"]
            ) +
            ' ! videoscale add-borders=0 ! videoconvert ! videorate' +
            ' ! capsfilter name=caps_{:02d}'.format(
                index + 1
            ) +
            ' caps="video/x-raw, width={},'.format(
                width   
            ) +
            ' height={}, framerate={}/1"'.format(
                height,
                self.inputs[index].get("fps", self.args.fps)
            ) +
            ' ! textoverlay text="{}" font-desc="Ubuntu, {}"'.format(
                self.inputs[index].get("text", ""),
                self.inputs[index].get("text_size", self.args.text_size)
            ) +
            ' ! tee name=tea_{:02d} ! queue ! alpha_{:02d}.'.format(
                index, index
            ) +
            ' tea_{:02d}. ! queue ! is.'.format(
                index
            ) +
            ' alpha alpha=1 name=alpha_{:02d}'.format(
                index
            ) +
            ' ! videobox border-alpha=0 top={} left={}'.format(
                y * -1 * height, x * -1 * width
            ) +
            ' ! mix.'
        )

        return stream_branch

    def _generate_pipeline(self):
        grid = math.ceil(math.sqrt(len(self.inputs)))

        pipeline = self._generate_mixer_branch()

        for i, source in enumerate(self.inputs):
            pipeline += self._generate_stream_branch(
                i, source, grid
            )

        return pipeline

    def _run_pipeline(self, pipeline_string):
        Gst.init(None)
        mainloop = GLib.MainLoop.new(None, False)
        
        self.pipeline = Gst.parse_launch(pipeline_string)
        self._fix_callbacks()
        
        self.pipeline.set_state(Gst.State.PLAYING)

        bus = self.pipeline.get_bus()
        bus.timed_pop_filtered(
            Gst.CLOCK_TIME_NONE,
            Gst.MessageType.ERROR | Gst.MessageType.EOS
        )

        self.pipeline.set_state(Gst.State.NULL);

    def _parse_run_pipeline(self):
        self.inputs = self._get_input_uris()
        if self.inputs is None:
            raise Exception('Unable to obtain input list.')
        else:
            if self.args.verbose:
                for uri in self.inputs:
                    print("Playing: {}".format(uri))

        pipeline_string = self._generate_pipeline()

        if self.args.verbose:
            print("Pipeline: {}".format(pipeline_string))

        self._run_pipeline(pipeline_string)

    def _parse_run_pipeline_thread(self):
        thread = Thread(
            target=self._parse_run_pipeline
        )
        thread.daemon = True
        thread.start()

        return thread

    def start(self, run_in_thread=False):
        self.args = self._get_arguments()

        if self.args.generate is not None:
            copy_sample_config(self.args.generate)
        elif run_in_thread:
            thread = self._parse_run_pipeline_thread()
            return thread
        else:
            self._parse_run_pipeline(self.args)