# coding=utf-8
# -*- coding: utf-8 -*-
import threading
import os
from functools import partial
from time import sleep
from bokeh.io import curdoc
from bokeh.layouts import row, column
from bokeh.models import (Button, TextInput, ColumnDataSource, PanTool, HoverTool, Dimensions, PreText)
from bokeh.palettes import plasma, small_palettes
from bokeh.plotting import figure
from twisted.internet import threads, reactor
from tornado import gen
from bptc.networking.pull_protocol import PullClientFactory
from bptc.utils import init_logger

R_COLORS = small_palettes['Set2'][8]

doc = curdoc()

# shuffle(R_COLORS)
def round_color(r):
    return R_COLORS[r % 8]

I_COLORS = plasma(256)


class App:

    @staticmethod
    def start_reactor_thread():
        def start_reactor():
            reactor.run(installSignalHandlers=0)

        thread = threading.Thread(target=start_reactor)
        thread.daemon = True
        thread.start()
        print('Started reactor')

    def __init__(self):
        self.pull_thread = None
        log_directory = 'data/viz'
        os.makedirs(log_directory, exist_ok=True)
        init_logger(log_directory)

        if not reactor.running:
            self.start_reactor_thread()

        self.text = PreText(text='Reload the page to clear all events,\n'
                                 'especially when changing the member to\n'
                                 'pull from.',
                            width=500, height=100)
        self.ip_text_input = TextInput(value='localhost')
        self.port_text_input = TextInput(value='8001')
        self.start_pulling_button = Button(label="Start pulling...", width=60)
        self.start_pulling_button.on_click(partial(self.start_pulling, self.ip_text_input, self.port_text_input))
        self.stop_pulling_button = Button(label="Stop pulling...", width=60)
        self.stop_pulling_button.on_click(self.stop_pulling)

        self.all_events = {}
        self.new_events = {}
        self.verify_key_to_x = {}
        self.n_nodes = 4
        self.counter = 0

        plot = figure(
                plot_height=1000, plot_width=900, y_range=(0, 30), x_range=(0, self.n_nodes - 1),
                tools=[PanTool(dimensions=Dimensions.height),
                       HoverTool(tooltips=[
                           ('hash', '@hash'), ('member', '@member_id'), ('height', '@height'), ('round', '@round'), ('data', '@data')])])

        plot.xgrid.grid_line_color = None
        plot.xaxis.minor_tick_line_color = None
        plot.ygrid.grid_line_color = None
        plot.yaxis.minor_tick_line_color = None

        self.links_src = ColumnDataSource(data={'x0': [], 'y0': [], 'x1': [],
                                                'y1': [], 'width': []})

        self.links_rend = plot.segment(color='#777777',
                x0='x0', y0='y0', x1='x1',
                y1='y1', source=self.links_src, line_width='width')

        self.events_src = ColumnDataSource(
                data={'x': [], 'y': [], 'round_color': [], 'line_alpha': [],
                      'round': [], 'hash': [], 'payload': [], 'time': [], 'member_id': [], 'height': [], 'data': []})

        self.events_rend = plot.circle(x='x', y='y', size=20, color='round_color',
                                       line_alpha='line_alpha', source=self.events_src, line_width=5)

        self.log = PreText(text='')

        control_column = column(self.text, self.ip_text_input,
                                self.port_text_input, self.start_pulling_button, self.stop_pulling_button, self.log)
        main_row = row([control_column, plot], sizing_mode='fixed')
        doc.add_root(main_row)

    @gen.coroutine
    def received_data_callback(self, from_member, events):
        for event_id, event in events.items():
            if event_id not in self.all_events:
                if event.verify_key not in self.verify_key_to_x.keys():
                    self.verify_key_to_x[event.verify_key] = self.counter
                    self.counter = self.counter + 1
                self.all_events[event_id] = event
                self.new_events[event_id] = event
        self.n_nodes = len(self.verify_key_to_x)
        self.log.text += "Updated member {}...\n".format(from_member[:6])

    def start_pulling(self, ip_text_input, port_text_input):
        ip = ip_text_input.value
        port = int(port_text_input.value)
        factory = PullClientFactory(self, doc)

        self.pull_thread = PullingThread(ip, port, factory)
        self.pull_thread.daemon = True
        self.pull_thread.start()

    def stop_pulling(self):
        self.pull_thread.stop()

    @gen.coroutine
    def draw(self):
        events, links = self.extract_data(self.new_events)
        self.new_events = {}
        self.links_src.stream(links)
        self.events_src.stream(events)

    def extract_data(self, events):
        events_data = {'x': [], 'y': [], 'round_color': [],
                   'line_alpha': [], 'round': [], 'hash': [], 'payload': [], 'time': [], 'member_id': [], 'height': [], 'data': []}
        links_data = {'x0': [], 'y0': [], 'x1': [], 'y1': [], 'width': []}

        for event_id, event in events.items():
            x = self.verify_key_to_x[event.verify_key]
            y = event.height
            events_data['x'].append(x)
            events_data['y'].append(y)
            events_data['round_color'].append(round_color(event.round))
            events_data['round'].append(event.round)
            events_data['hash'].append(event.id[:6] + "...")
            events_data['payload'].append("".format(event.data))
            events_data['time'].append(event.time)
            events_data['line_alpha'].append(1)
            events_data['member_id'].append(event.verify_key[:6] + '...')
            events_data['height'].append(event.height)
            events_data['data'].append('None' if event.data is None else str(event.data))

            if event.parents.self_parent is not None:
                links_data['x0'].append(x)
                links_data['y0'].append(y)
                links_data['x1'].append(str(self.verify_key_to_x[self.all_events[event.parents.self_parent].verify_key]))
                links_data['y1'].append(self.all_events[event.parents.self_parent].height)
                links_data['width'].append(3)

            if event.parents.other_parent is not None:
                links_data['x0'].append(x)
                links_data['y0'].append(y)
                links_data['x1'].append(str(self.verify_key_to_x[self.all_events[event.parents.other_parent].verify_key]))
                links_data['y1'].append(self.all_events[event.parents.other_parent].height)
                links_data['width'].append(1)

        return events_data, links_data

App()


class PullingThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, ip, port, factory):
        super(PullingThread, self).__init__()
        self.ip = ip
        self.port = port
        self.factory = factory
        self._stop_event = threading.Event()

    def run(self):
        while not self.stopped():
                    threads.blockingCallFromThread(reactor, partial(reactor.connectTCP, self.ip, self.port, self.factory))
                    sleep(1)

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
