#!/usr/bin/env python

import xml.etree.ElementTree as ET


class Stations(object):
    def __init__(self, bicing_data_file):
        xml_tree = ET.parse(bicing_data_file)
        self.xml_root = xml_tree.getroot()

        # getting the updatetime
        self.time = int(self.xml_root.find('updatetime').text)

        self.stations = []

    def run(self):
        for xml_stations in self.xml_root.findall('station'):
            station = {}
            station['id'] = int(xml_stations.find('id').text)
            station['type'] = xml_stations.find('type').text
            station['lat'] = float(xml_stations.find('lat').text)
            station['long'] = float(xml_stations.find('long').text)
            station['street'] = xml_stations.find('street').text
            station['height'] = int(xml_stations.find('height').text)
            try:
                station['streetNumber'] = int(xml_stations.find('streetNumber').text)
            except:
                station['streetNumber'] = xml_stations.find('streetNumber').text
            station['nearbyStationList'] = self._parse_string_list(xml_stations.find('nearbyStationList').text)
            station['status'] = xml_stations.find('status').text
            station['slots'] = int(xml_stations.find('slots').text)
            station['bikes'] = int(xml_stations.find('bikes').text)
            self.stations.append(station)

    def _parse_string_list(self, string_list):
        num_list = [int(num_str) for num_str in string_list.split(',')]
        return num_list


if __name__ == "__main__":
    from os import listdir
    from os.path import isfile, join
    import json
    output_file_data = 'data.json'

    # this process build the data.json file only if don't exist
    if not isfile(output_file_data):
        data_dir = 'data_day'
        i = 0
        time_series = []
        times = set()
        for f in listdir(data_dir):
            file_path = join(data_dir, f)
            if isfile(file_path):
                try:
                    stations = Stations(file_path)
                    if stations.time not in times:
                        stations.run()
                        time_series.append((stations.time, stations.stations))
                        times.add(stations.time)
                except:
                    print "Error in file %s" % file_path
                print "Checking file %d" % i
                i += 1

        print "Creating file %s" % output_file_data
        try:
            with open(output_file_data, 'w') as f:
                json.dump(time_series, f)
        except:
            print "The output file couldn't be build"
    else:
        print "The file %s already exist" % output_file_data
