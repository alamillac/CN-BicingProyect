#!/usr/bin/env python

import networkx as nx
import logging
import json
from datetime import datetime
from os.path import join
from WalkingTimes import WalkingTimes

# draw graphs without X11 in linux
import matplotlib
matplotlib.use('Agg')  # Must be before importing matplotlib.pyplot or pylab!
import matplotlib.pyplot as plt

# set up logging to file
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
                    # datefmt='%m-%d %H:%M',
                    filename='./network.log',
                    filemode='w')
# define a Handler which writes DEBUG messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)


class StationsNetworks(object):
    def __init__(self):
        self.data_file = 'data.json'
        self.G = nx.Graph()
        self.wtime = WalkingTimes()

        logging.info("Reading data")
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            logging.info("Data was read")
        except IOError:
            logging.error("The file %s don't exist" % self.data_file)

        # start the process of drawing the timeseries in png files
        self._draw_timeseries(data)

    def _draw_timeseries(self, data):
        i = 0
        for timestamp in self._build_from_data(data):
            # we get all the properties from the graph
            nodes_sizes = self._get_node_sizes()
            nodes_colors = self._get_node_colors()
            nodes_pos = self._get_positions()

            # we set the title of the graph
            datatime = datetime.fromtimestamp(timestamp)
            title = datatime.strftime('%d-%m-%y %H:%M:%S')

            for weight_key in ['weight_1', 'weight_5', 'weight_15']:
                # We set the default settings of the graph
                plt.axis((41.35, 41.46, -2.23, -2.10))
                plt.axis('off')
                plt.title(title)

                edges_sizes = self._get_edge_sizes(weight_key)
                filename_map = join("public", "images", weight_key, "map_bicing_%04d.png" % i)
                logging.info("Drawing file %s" % filename_map)

                # we draw the graph in a file
                nx.draw_networkx_nodes(self.G, nodes_pos, node_size=nodes_sizes, node_color=nodes_colors, with_labels=False)
                nx.draw_networkx_edges(self.G, nodes_pos, width=edges_sizes, edge_color='g')
                plt.savefig(filename_map)
                plt.close()

            i += 1

    def _get_edge_sizes(self, weight_key):
        edges = []
        edges_not_std = [sum(edge[2][weight_key]) for edge in self.G.edges(data=True)]
        if edges_not_std:
            max_edge_value = max(edges_not_std)
            if max_edge_value:
                constant = float(1) / max_edge_value
            else:
                constant = 0
            edges = [edge * constant for edge in edges_not_std]
        return edges

    def _get_node_property(self, prop):
        return [self.G.node[node_id][prop] for node_id in self.G.nodes()]

    def _get_node_colors(self):
        return self._get_node_property('color')

    def _get_node_sizes(self):
        return self._get_node_property('size')

    def _get_positions(self):
        return {node_id: self.G.node[node_id]['pos'] for node_id in self.G.nodes()}

    def _get_bike_durations(self, origin_position):
        """
        Get the duration of node_id against all the nodes present in self.G.nodes()
        using WalkingTimes.calculate_bike. This get the approximate time spent to
        go from one station to another in a bike
        """

        bike_durations = {}
        for destination_node_id, destination_node_data in self.G.nodes(data=True):
            bike_duration = self.wtime.calculate_bike(origin_position, destination_node_data)
            if bike_duration:
                bike_durations[destination_node_id] = bike_duration['duration']

        return bike_durations

    def _find_posible_origins(self, station_destination_id, station_less_bikes, timestamp):
        posible_origins = []
        for timestamp_origin, posible_origin_station_id in station_less_bikes:
            if station_destination_id != posible_origin_station_id:
                posible_duration = timestamp - timestamp_origin
                try:
                    max_duration = self.G.node[station_destination_id]['bike_durations'][posible_origin_station_id]['max']
                    min_duration = self.G.node[station_destination_id]['bike_durations'][posible_origin_station_id]['min']
                    if max_duration >= posible_duration and min_duration <= posible_duration:
                        posible_origins.append(posible_origin_station_id)
                except KeyError:
                    logging.error("Key error in nodes (%d, %d)" % (station_destination_id, posible_origin_station_id))

        return posible_origins

    def _build_from_data(self, data):
        # data is a timeseries list of the form:
        # [(time1, object), (time2, object), ...]
        # and object is a list of all stations and has the form:
        # [station1, station2, ...]
        # station is an object with the following properties:
        # { status: -> station working or not (OPN)
        #   bikes: -> number of bikes in the station
        #   slots: -> The number of slots available to put a bike
        #   lat: -> latitude coordinate of the station
        #   long: -> longitude coordinate of the station
        #   height: ->
        #   street: -> the name of the street of the station
        #   nearbyStationList: -> A list with the id of the nearest stations
        #   streetNumber: -> The number of the street
        #   type: -> The type of the stations
        #   id: -> The id of the station }

        max_cut_time = 35 * 60  # (35 mins) time in seconds

        logging.info("Sorting data")
        # the data should be sorted by time
        data = sorted(data, key=lambda timeserie: timeserie[0])
        logging.info("Data sorted")

        logging.info("Processing data")
        station_less_bikes = []
        for timestamp, stations in data:
            station_more_bikes = []

            for station in stations:
                node_id = station['id']
                bikes = station['bikes']
                slots = station['slots']
                status = station['status']

                # if node don't exist create it
                if node_id not in self.G.node:
                    logging.debug("New node found: %d" % node_id)

                    # The position of the node in the graph is proportional
                    # to the coordinates of the station in a map
                    lat = station['lat']
                    lon = station['long']
                    pos_x = lat
                    pos_y = -lon
                    node_pos = [pos_x, pos_y]

                    # We add the number of bikes in the station. We use this
                    # to know if the number of bikes change in the next timestamp
                    properties = {
                        'pos': node_pos,
                        'bikes': bikes,
                        'lat': lat,
                        'lon': lon
                        }

                    # We found the bike durations from the current node to all the
                    # nodes
                    bike_durations = self._get_bike_durations(properties)
                    properties['bike_durations'] = bike_durations

                    # We have to update the bike durations in all the nodes
                    for remote_node_id in bike_durations:
                        bike_duration_to_remote = bike_durations[remote_node_id]
                        self.G.node[remote_node_id]['bike_durations'][node_id] = bike_duration_to_remote

                    # We add the new node to the graph with the position and bikes property
                    self.G.add_node(node_id, properties)

                # find color for node
                # green = all ok, there are available bikes in the station
                # yellow = station not operational
                # blue = station not operational or with error (bikes = slots = 0)
                # red = empty station. Station with 0 bikes
                if status == "OPN":
                    node_color = "g"
                else:
                    node_color = "y"

                # node size start in 10 until 50
                # if the station is not working the default size is 25
                try:
                    node_size = (float(bikes)/(bikes+slots)) * 40 + 10
                    if not bikes and slots:
                        node_color = "r"
                except ZeroDivisionError:
                    # this usually happen when status is CLS
                    node_size = 25
                    node_color = "b"

                # We try to know if the station change from the previous status
                # this mean if the number of bikes changes
                previous_bikes = self.G.node[node_id]['bikes']
                self.G.node[node_id]['bikes'] = bikes

                # if the number of bikes is lower than before at least one bike is
                # on road so we add this node to find the destination later (new edge).
                # if the number of bikes is greater than before at least one bike
                # arrive to the station. We can set the edge with the origin node.
                if bikes < previous_bikes:
                    logging.debug("%d bikes part from station %d" % (previous_bikes - bikes, node_id))
                    station_less_bikes.append((timestamp, node_id))
                    node_color = "m"
                elif bikes > previous_bikes:
                    logging.debug("%d bikes arrived to station %d" % (bikes - previous_bikes, node_id))
                    station_more_bikes.append(node_id)
                    node_color = "c"

                # We add the color and size properties to the node
                self.G.node[node_id]['color'] = node_color
                self.G.node[node_id]['size'] = node_size

            # Remove bikes with more than 35 mins. According with wikipedia
            # More than 95% of rides in the system are shorter than 30 minutes.
            # https://en.wikipedia.org/wiki/Bicing
            # We improve the accuracy and reduce times doing this.
            break_i = 0
            for processed_timestamp, processed_node_id in station_less_bikes:
                deltatime = timestamp - processed_timestamp
                if deltatime < max_cut_time:
                    break
                break_i += 1

            station_less_bikes = station_less_bikes[break_i:]

            # Find all the edges
            found_edges = set()
            for station_destination_id in station_more_bikes:
                stations_origin_id = self._find_posible_origins(station_destination_id, station_less_bikes, timestamp)
                logging.info("%d new edges to node %d" % (len(stations_origin_id), station_destination_id))
                for station_origin_id in stations_origin_id:
                    found_edges.add((station_origin_id, station_destination_id))

            # Update edges
            for edge in self.G.edges():
                weight_1 = self.G[edge[0]][edge[1]]['weight_1']
                weight_5 = self.G[edge[0]][edge[1]]['weight_5']
                weight_15 = self.G[edge[0]][edge[1]]['weight_15']

                was_removed = False
                if edge in found_edges:
                    # remove edge from set
                    found_edges.remove(edge)

                    # increment the weight of the edge
                    weight_1.append(1)
                    weight_5.append(1)
                    weight_15.append(1)
                else:
                    if sum(weight_15) == 0:
                        # remove edge
                        self.G.remove_edge(edge[0], edge[1])
                        was_removed = True
                    else:
                        weight_1.append(0)
                        weight_5.append(0)
                        weight_15.append(0)

                # update weights from edge
                if not was_removed:
                    self.G[edge[0]][edge[1]]['weight_1'] = weight_1[-1:]
                    self.G[edge[0]][edge[1]]['weight_5'] = weight_5[-5:]
                    self.G[edge[0]][edge[1]]['weight_15'] = weight_15[-15:]

            # Create the other edges
            for edge in found_edges:
                weights = {
                    "weight_1": [1],
                    "weight_5": [1],
                    "weight_15": [1]
                }
                self.G.add_edge(edge[0], edge[1], weights)

            # when we process all the stations in the timestamp we return
            # the timestamp
            yield timestamp


if __name__ == "__main__":
    net = StationsNetworks()
