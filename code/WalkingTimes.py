#!/usr/bin/env python

import json
import requests
from requests.exceptions import ConnectionError
import os
from geopy.distance import vincenty


class OverQueryLimit(Exception):
    def __init__(self):
        self.value = "OverQueryLimit"

    def __str__(self):
        return repr(self.value)


class WalkingTimes(object):
    def __init__(self, use_cache=True, use_google_api=True):
        self.use_cache = use_cache
        self.use_google_api = use_google_api
        self.count_not_cache = 0
        self.max_count_not_cache = 50  # save cache every 50 queries
        self.google_distancematrix_api_url = "https://maps.googleapis.com/maps/api/distancematrix/json"

        try:
            self.google_api_key = os.environ['GOOGLE_API_KEY']
        except KeyError:
            self.google_api_key = None

        # Bike scale values. I got this values with information of my own tracks
        # in some stations
        self.bike_scale_factor = 2.13
        self.bike_ci_percentage = 0.2

        if use_cache:
            self.version = "1.0"
            self.update_cache = False
            self.cache_file = 'walking_cache.json'
            self.cache_data = {}

            # try to open a file with the cache
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)

                    # the data should be validated
                    try:
                        if self.version == cache_data['version']:
                            self.cache_data = cache_data['data']
                        else:
                            print "Version error load"
                    except:
                        print "Invalid cache file"
            except:
                print "Cache not found"

    def __del__(self):
        self.save_cache()

    def save_cache(self):
        if self.use_cache and self.update_cache:
            print "saving cache"
            try:
                with open(self.cache_file, 'w') as f:
                    json.dump({
                        "version": self.version,
                        "data": self.cache_data
                        }, f)
            except:
                print "It was imposible to save cache"

    def calculate(self, origin, destination):
        """
        Find the distance and the duration of going from
        one point to another by walking using the google
        distancematrix api if it is possible, or the vincenty
        algorithm if it is not possible.
        https://developers.google.com/maps/documentation/distancematrix/?hl=es
        """
        origin_str = self._coord_to_string(origin)
        destination_str = self._coord_to_string(destination)
        key_cache = "%s_%s" % (origin_str, destination_str)
        result = {'result': None}

        if self.use_cache:
            if key_cache in self.cache_data:
                result = {'result': self.cache_data[key_cache]}
            else:
                try:
                    result = self._get_distance(origin, destination)
                except:
                    if self.update_cache:
                        self.save_cache()
                        self.count_not_cache = 0
                        self.update_cache = False
                    raise

                # we save in cache only the google results
                if result and result['from_google']:
                    self.count_not_cache += 1
                    self.cache_data[key_cache] = result['result']

                    # save cache when max_count_not_cache is exceeded
                    if self.count_not_cache > self.max_count_not_cache:
                        self.save_cache()
                        self.count_not_cache = 0
                        self.update_cache = False
                    else:
                        self.update_cache = True
        else:
            result = self._get_distance(origin, destination)
        return result['result']

    def _get_distance(self, *args, **kwargs):
        from_google = False
        if self.use_google_api:
            try:
                result = self._google_distancematrix_api(*args, **kwargs)
                from_google = True
            except OverQueryLimit:
                self.use_google_api = False
                result = self._get_distance_vincenty(*args, **kwargs)
            except ConnectionError:
                result = self._get_distance_vincenty(*args, **kwargs)
        else:
            result = self._get_distance_vincenty(*args, **kwargs)

        return {'from_google': from_google, 'result': result}

    def _get_distance_vincenty(self, origin, destination):
        origin_tuple = (origin['lat'], origin['lon'])
        destination_tuple = (destination['lat'], destination['lon'])
        raw_distance = vincenty(origin_tuple, destination_tuple).km
        # TODO improve the factor using the google results as test set
        aprox_distance = raw_distance * 1.22  # we have to add a factor to compensate curves in the way.
        # acording wikipedia: average human walking speed is about 5.0 kilometres per hour
        # https://en.wikipedia.org/?title=Walking
        average_walking_speed = 5
        aprox_duration = (aprox_distance / average_walking_speed) * 60  # aprox. duration in minutes
        result = {
            "distance": {
                "text": "%2f km" % aprox_distance,
                "value": aprox_distance * 1000  # distance in meters
            },
            "duration": {
                "text": "%d min" % aprox_duration,
                "value": aprox_duration * 60  # duration in seconds
            }
        }
        return result

    def aproximate_bike_duration(self, walking_duration):
        bike_duration = walking_duration / self.bike_scale_factor
        bike_duration_min = bike_duration - bike_duration * self.bike_ci_percentage
        bike_duration_max = bike_duration + bike_duration * self.bike_ci_percentage

        result = {
            "min": bike_duration_min,
            "value": bike_duration,
            "max": bike_duration_max
            }
        return result

    def calculate_bike(self, *args, **kwargs):
        walking_results = self.calculate(*args, **kwargs)
        bike_results = None
        if walking_results:
            bike_aprox_duration = self.aproximate_bike_duration(walking_results["duration"]["value"])
            bike_results = {
                "duration": bike_aprox_duration,
                "distance": walking_results["distance"]
                }
        return bike_results

    def _coord_to_string(self, coord):
        return '%f,%f' % (coord['lat'], coord['lon'])

    def _google_distancematrix_api(self, origin, destination, mode="walking"):
        options = {
            "origins": self._coord_to_string(origin),
            "destinations": self._coord_to_string(destination),
            "mode": mode
            }

        if self.google_api_key:
            options["key"] = self.google_api_key

        req = requests.get(self.google_distancematrix_api_url, params=options)
        response = req.json()

        result = {}

        if response["status"] == "OK":
            if response["rows"][0]["elements"][0]["status"] == "OK":
                result = response["rows"][0]["elements"][0]
        elif response["status"] == "OVER_QUERY_LIMIT":
            raise OverQueryLimit()

        return result

if __name__ == "__main__":
    origin = {
        "lat": 41.375336,
        "lon": 2.168007
        }

    destination = {
        "lat": 41.388471,
        "lon": 2.192835
        }

    wtime = WalkingTimes()
    result = wtime.calculate(origin, destination)
    bike_result = wtime.calculate_bike(origin, destination)

    wtime.use_google_api = False
    wtime.use_cache = False
    result_no_google = wtime.calculate(origin, destination)

    print "distance: %s" % result["distance"]["text"]
    print "duration: %s" % result["duration"]["text"]
    print "distance no google: %s" % result_no_google["distance"]["text"]
    print "duration no google: %s" % result_no_google["duration"]["text"]
    print "bike duration: (min, aprox, max) (%d mins, %d mins, %d mins)" % (bike_result['duration']['min']/60, bike_result['duration']['value']/60, bike_result['duration']['max']/60)
