# -*- coding: utf-8 -*-
import threading
from functools import partial
from time import sleep, strftime, gmtime
from bokeh.io import curdoc
from bokeh.layouts import row, column
from bokeh.models import (Button, TextInput, ColumnDataSource, PanTool, HoverTool, PreText, WheelZoomTool)
from bokeh.palettes import plasma, small_palettes
from bokeh.plotting import figure
from twisted.internet import threads, reactor
from tornado import gen
from bptc.data.event import Fame
from bptc.protocols.pull_protocol import PullClientFactory

R_COLORS = small_palettes['Set2'][8]

doc = curdoc()


def round_color(r):
    return R_COLORS[r % 8]

I_COLORS = plasma(256)

lock = threading.Lock()


class App:

    def __init__(self):
        self.pull_thread = None
        self.pulling = False
        if not reactor.running:
            self.start_reactor_thread()

        self.text = PreText(text='Reload the page to clear all events,\n'
                                 'especially when changing the member to\n'
                                 'pull from.',
                            width=500, height=100)
        self.ip_text_input = TextInput(value='localhost')
        self.port_text_input = TextInput(value='8001')
        self.pulling_button = Button(label="start/stop pulling", width=150)
        self.pulling_button.on_click(partial(self.toggle_pulling, self.ip_text_input, self.port_text_input))

        self.all_events = {}
        self.member_id_to_x = {}
        self.n_nodes = 10

        plot = figure(
                plot_height=800, plot_width=1800, y_range=(0, 30), x_range=(0, self.n_nodes - 1),
                tools=[PanTool(),  # dimensions=[Dimensions.height, Dimensions.width]
                       HoverTool(tooltips=[
                           ('id', '@id'), ('from', '@from'), ('height', '@height'), ('witness', '@witness'),
                           ('round', '@round'), ('data', '@data'), ('famous', '@famous'),
                           ('round_received', '@round_received'), ('consensus_timestamp', '@consensus_timestamp')])])
        plot.add_tools(WheelZoomTool())

        plot.xgrid.grid_line_color = None
        plot.xaxis.minor_tick_line_color = None
        plot.ygrid.grid_line_color = None
        plot.yaxis.minor_tick_line_color = None

        self.index_counter = 0
        self.links_src = ColumnDataSource(data={'x0': [], 'y0': [], 'x1': [],
                                                'y1': [], 'width': []})

        self.links_rend = plot.segment(color='#777777',
                x0='x0', y0='y0', x1='x1',
                y1='y1', source=self.links_src, line_width='width')

        self.events_src = ColumnDataSource(
                data={'x': [], 'y': [], 'round_color': [], 'line_alpha': [],
                      'round': [], 'id': [], 'payload': [], 'time': [], 'from': [], 'height': [], 'data': [],
                      'witness': [], 'famous': [], 'round_received': [], 'consensus_timestamp': []})

        self.events_rend = plot.circle(x='x', y='y', size=20, color='round_color',
                                       line_alpha='line_alpha', source=self.events_src, line_width=5)

        control_row = row(self.text, self.ip_text_input, self.port_text_input, self.pulling_button)
        main_row = column([control_row, plot])
        doc.add_root(main_row)

    @gen.coroutine
    def received_data_callback(self, from_member, events):
        print('received_data_callback()')
        new_events = []
        for event in events:
            if event.id in self.all_events:
                if event.consensus_time is not None:
                    self.update_event(event)
            else:
                # don't know event
                if event.verify_key not in self.member_id_to_x.keys():
                    # don't know member
                    self.member_id_to_x[event.verify_key] = len(self.member_id_to_x)
                event.index = len(self.all_events)
                self.all_events[event.id] = event
                new_events.append(event)
        self.draw(from_member, new_events)

    @gen.coroutine
    def draw(self, from_member, new_events):
        events, links = self.extract_data(new_events)
        self.links_src.stream(links)
        self.events_src.stream(events)
        print("Updated member {} at {}...\n".format(from_member[:6], strftime("%H:%M:%S", gmtime())))
        lock.release()

    def update_event(self, event):
        index = self.all_events[event.id].index
        patches = {
            'round_color': [(index, self.color_of(event))],
            'famous': [(index, self.fame_to_string(event.is_famous))],
            'round_received': [(index, event.round_received)],
            'consensus_timestamp': [(index, event.consensus_time)]
        }
        self.events_src.patch(patches)

    def toggle_pulling(self, ip_text_input, port_text_input):
        if self.pulling:
            self.pull_thread.stop()
            self.pulling = False
        else:
            ip = ip_text_input.value
            port = int(port_text_input.value)
            factory = PullClientFactory(self, doc, lock)

            self.pull_thread = PullingThread(ip, port, factory)
            self.pull_thread.daemon = True
            self.pull_thread.start()
            self.pulling = True

    def extract_data(self, events):
        events_data = {'x': [], 'y': [], 'round_color': [], 'line_alpha': [], 'round': [], 'id': [], 'payload': [],
                       'time': [], 'from': [], 'height': [], 'data': [], 'witness': [], 'famous': [],
                       'round_received': [], 'consensus_timestamp': []}
        links_data = {'x0': [], 'y0': [], 'x1': [], 'y1': [], 'width': []}

        for event in events:
            x = self.member_id_to_x[event.verify_key]
            y = event.height
            events_data['x'].append(x)
            events_data['y'].append(y)
            events_data['round_color'].append(self.color_of(event))
            events_data['round'].append(event.round)
            events_data['id'].append(event.id[:6] + "...")
            events_data['payload'].append("".format(event.data))
            events_data['time'].append(event.time)
            events_data['line_alpha'].append(1)
            events_data['from'].append(event.verify_key[:6] + '...')
            events_data['height'].append(event.height)
            events_data['data'].append('None' if event.data is None else str(event.data))
            events_data['witness'].append('Yes' if event.is_witness else 'No')
            events_data['famous'].append(self.fame_to_string(event.is_famous))
            events_data['round_received'].append(event.round_received)
            events_data['consensus_timestamp'].append(event.consensus_time)

            self_parent_id = event.parents.self_parent
            if self_parent_id is not None and self_parent_id in self.all_events:
                self_parent = self.all_events[self_parent_id]
                links_data['x0'].append(x)
                links_data['y0'].append(y)
                links_data['x1'].append(str(self.member_id_to_x[self_parent.verify_key]))
                links_data['y1'].append(self_parent.height)
                links_data['width'].append(3)

            other_parent_id = event.parents.other_parent
            if other_parent_id is not None and other_parent_id in self.all_events:
                other_parent = self.all_events[other_parent_id]
                links_data['x0'].append(x)
                links_data['y0'].append(y)
                links_data['x1'].append(str(self.member_id_to_x[other_parent.verify_key]))
                links_data['y1'].append(other_parent.height)
                links_data['width'].append(1)

        return events_data, links_data

    @staticmethod
    def color_of(event):
        if event.round_received is not None:
            color = '#000000'
        elif event.is_famous == Fame.TRUE:
            color = '#FF0000'
        else:
            color = round_color(event.round)
        return color

    @staticmethod
    def fame_to_string(fame):
        if fame is -1:
            return 'UNDECIDED'
        elif fame is 0:
            return 'NO'
        elif fame is 1:
            return 'YES'

    @staticmethod
    def start_reactor_thread():
        def start_reactor():
            reactor.run(installSignalHandlers=0)

        thread = threading.Thread(target=start_reactor)
        thread.daemon = True
        thread.start()
        print('Started reactor')

    @staticmethod
    def start_reactor_thread():
        def start_reactor():
            reactor.run(installSignalHandlers=0)

        thread = threading.Thread(target=start_reactor)
        thread.daemon = True
        thread.start()
        print('Started reactor')

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
            lock.acquire()
            print('Try to connect...')
            threads.blockingCallFromThread(reactor, partial(reactor.connectTCP, self.ip, self.port, self.factory))
            sleep(1)

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
