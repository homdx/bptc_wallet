# coding=utf-8
# -*- coding: utf-8 -*-
import threading
from functools import partial
import sys
from bokeh.io import curdoc
from bokeh.layouts import row, column
from bokeh.plotting import figure
from bokeh.palettes import plasma, small_palettes
from bokeh.models import (Button, ColumnDataSource, PanTool, HoverTool, Dimensions, PreText)
from networking.pull_protocol import PullClientFactory
from twisted.internet import threads, reactor

R_COLORS = small_palettes['Set2'][8]


# shuffle(R_COLORS)
def round_color(r):
    return R_COLORS[r % 8]

I_COLORS = plasma(256)


class App:

    @staticmethod
    def start_reactor_thread():
        def start_reactor():
            reactor.run(installSignalHandlers=0)

        threading.Thread(target=start_reactor).start()
        print('Started reactor')

    def __init__(self, ip, port):
        if not reactor.running:
            self.start_reactor_thread()

        self.update_button = Button(label="Update", width=60)
        self.update_button.on_click(partial(self.pull_from, ip, port))

        self.draw_button = Button(label='Draw', width=60)
        self.draw_button.on_click(self.draw)

        self.all_events = {}
        self.new_events = {}
        self.verify_key_to_x = {}
        self.n_nodes = 4
        self.counter = 0

        plot = figure(
                plot_height=1000, plot_width=900, y_range=(0, 30), x_range=(0, self.n_nodes - 1),
                tools=[PanTool(dimensions=Dimensions.height),
                       HoverTool(tooltips=[
                           ('round', '@round'), ('hash', '@hash'),
                           ('timestamp', '@time'), ('payload', '@payload')])])

        plot.xgrid.grid_line_color = None
        plot.xaxis.minor_tick_line_color = None
        plot.ygrid.grid_line_color = None
        plot.yaxis.minor_tick_line_color = None

        self.links_src = ColumnDataSource(data={'x0': [], 'y0': [], 'x1': [],
                                                'y1': [], 'width': []})

        self.links_rend = plot.segment(color='#777777',
                x0='x0', y0='y0', x1='x1',
                y1='y1', source=self.links_src, line_width='width')

        self.tr_src = ColumnDataSource(
                data={'x': [], 'y': [], 'round_color': [], 'line_alpha': [],
                      'round': [], 'hash': [], 'payload': [], 'time': []})

        self.tr_rend = plot.circle(x='x', y='y', size=20, color='round_color',
                                   line_alpha='line_alpha', source=self.tr_src, line_width=5)

        self.log = PreText(text='')

        control_column = column(self.update_button, self.draw_button, self.log)
        main_row = row([control_column, plot], sizing_mode='fixed')
        curdoc().add_root(main_row)

    @staticmethod
    def received_data_callback(self, events):
        for event_id, event in events.items():
            if event_id not in self.all_events:
                if event.verify_key not in self.verify_key_to_x.keys():
                    self.verify_key_to_x[str(event.verify_key)] = self.counter
                    self.counter = self.counter + 1
                self.all_events[event_id] = event
                self.new_events[event_id] = event
        self.n_nodes = len(self.verify_key_to_x)

    def pull_from(self, ip, port):
        factory = PullClientFactory(self, self.received_data_callback)

        def sync_with_member():
            reactor.connectTCP(ip, port, factory)
        threads.blockingCallFromThread(reactor, sync_with_member)

    def draw(self):
        tr, links = self.extract_data(self.new_events)
        self.new_events = {}
        self.links_src.stream(links)
        self.tr_src.stream(tr)

    def extract_data(self, events):
        tr_data = {'x': [], 'y': [], 'round_color': [],
                   'line_alpha': [], 'round': [], 'hash': [], 'payload': [], 'time': []}
        links_data = {'x0': [], 'y0': [], 'x1': [], 'y1': [], 'width': []}

        for event_id, event in events.items():
            x = self.verify_key_to_x[event.verify_key]
            y = event.height
            tr_data['x'].append(x)
            tr_data['y'].append(y)
            event.round = 0  # TODO: fix
            tr_data['round_color'].append(round_color(event.round))
            tr_data['round'].append(event.round)
            tr_data['hash'].append(event.id[:8] + "...")
            tr_data['payload'].append("".format(event.data))
            tr_data['time'].append(event.time)
            tr_data['line_alpha'].append(1)

            if event.parents.self_parent is not None:
                links_data['x0'].append(x)
                links_data['y0'].append(y)
                links_data['x1'].append(self.verify_key_to_x[self.all_events[event.parents.self_parent].verify_key])
                links_data['y1'].append(self.all_events[event.parents.self_parent].height)
                links_data['width'].append(3)

            if event.parents.other_parent is not None:
                links_data['x0'].append(x)
                links_data['y0'].append(y)
                links_data['x1'].append(self.verify_key_to_x[self.all_events[event.parents.other_parent].verify_key])
                links_data['y1'].append(self.all_events[event.parents.other_parent].height)
                links_data['width'].append(1)

        return tr_data, links_data

App(sys.argv[1], int(sys.argv[2]))
