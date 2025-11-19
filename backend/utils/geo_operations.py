# Copyright 2025 Ashwin Raj
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import folium
import logging
import polyline
import requests
import googlemaps
import numpy as np
import streamlit as st


class LocationServices:
    def __init__(self):
        self.gmaps = googlemaps.Client(
            key=st.secrets["GOOGLE_MAPS_DISTANCE_MATRIX_API_KEY"]
        )

    def _get_route_data(self, origin, destination):
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={
            origin}&destination={
                destination}&key={
                    str(st.secrets['GOOGLE_MAPS_DISTANCE_MATRIX_API_KEY'])}"

        response = requests.get(url)
        return response.json()

    def display_route_with_folium(self, origin, destination):
        route_data = self._get_route_data(origin, destination)
        route_coordinates = []

        if route_data["status"] == "OK":
            map_polyline = route_data["routes"][0][
                "overview_polyline"]["points"]

            route_coordinates = polyline.decode(map_polyline)

        folium_map = folium.Map(
            location=route_coordinates[int(len(route_coordinates) / 2)],
            tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&key=" 
            + str(st.secrets['GOOGLE_MAPS_DISTANCE_MATRIX_API_KEY']),
            attr='<a href="https://www.google.com/maps/">Google</a>',
            zoom_start=13,
        )

        folium.PolyLine(
            route_coordinates, 
            color="#4285F4", 
            weight=5, 
            opacity=1,
        ).add_to(folium_map)

        folium_map.fit_bounds([route_coordinates[0], route_coordinates[-1]])
        return folium_map

    def get_city_and_state_from_zipcode(self, zipcode):
        url = f"https://api.opencagedata.com/geocode/v1/json?q={zipcode}&key={
            st.secrets['OPENCAGE_GEOCODING_API_KEY']}"

        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            if data["results"]:
                result = data["results"][0]

                try:
                    city = result["components"]["state_district"]
                except BaseException as e:
                    logging.error(f"Error extracting city: {e}")
                    city = None

                try:
                    state = result["components"]["state"]
                except BaseException as e:
                    logging.error(f"Error extracting state: {e}")
                    state = None

                return city, state

        else:
            return None, None

    def validate_address(self, address):
        result = self.gmaps.addressvalidation(address)

        if "result" in result and "verdict" in result["result"]:
            if result["result"]["verdict"]["validationGranularity"] != "OTHER":
                return True

        return False

    def fetch_nearby_districts(self, district_name):
        geocode_result = self.gmaps.geocode(district_name)

        location = geocode_result[0]["geometry"]["location"]

        latitude = location["lat"]
        longitude = location["lng"]

        nearby_result = self.gmaps.places_nearby(
            location=(latitude, longitude),
            radius=50000,
            type="locality",
        )

        nearby_districts = []

        for place in nearby_result["results"]:
            reverse_geocode_result = self.gmaps.reverse_geocode(
                (
                    place["geometry"]["location"]["lat"],
                    place["geometry"]["location"]["lng"],
                )
            )

            for component in reverse_geocode_result[0]["address_components"]:
                if "administrative_area_level_3" in component["types"]:
                    nearby_districts.append(component["long_name"])

        return list(set(nearby_districts))

    def get_batch_travel_distance_and_time_for_engineers(
        self, origins, destination
    ):
        result = self.gmaps.distance_matrix(origins, [destination])

        distances = []

        for element in result["rows"]:
            if element["elements"][0]["status"] == "OK":
                distances.append(
                    element["elements"][0]["distance"]["value"] / 1000)
            else:
                distances.append(float("inf"))

        return distances

    def get_travel_distance_and_time(self, origin, destination):
        distance_matrix = self.gmaps.distance_matrix(
            origins=origin,
            destinations=destination,
            mode="driving",
        )

        if distance_matrix["status"] == "OK":
            element = distance_matrix["rows"][0]["elements"][0]

            if element["status"] == "OK":
                distance = round(element["distance"]["value"] / 1000, 1)
                duration = round(element["duration"]["value"] / 60, 1)

                return distance, duration

            elif element["status"] == "NOT_FOUND":
                return False, "NOT_FOUND"

            else:
                return False, "ZERO_RESULTS"

        else:
            return False, element["status"]
        
    def _get_distance_matrix(self, addresses):
        api_key = st.secrets['GOOGLE_MAPS_DISTANCE_MATRIX_API_KEY']

        origins = '|'.join([addr['full_address'] for addr in addresses])
        destinations = origins

        url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origins}&destinations={destinations}&key={api_key}"
        
        response = requests.get(url)
        data = response.json()
        
        matrix = []
        for row in data['rows']:
            distances = []

            for element in row['elements']:
                if element['status'] == 'OK':
                    distances.append(element['distance']['value'])
                else:
                    distances.append(float('inf'))

            matrix.append(distances)
        
        return np.array(matrix)


    def _held_karp_algorithm(self, distance_matrix, start_idx=0):
        n = len(distance_matrix)
        memo = {}
        
        def dp(visited, last):
            if visited == (1 << start_idx):
                return distance_matrix[last][start_idx], start_idx
            
            if (visited, last) in memo:
                return memo[(visited, last)]
            
            min_cost = float('inf')
            prev_city = -1
            
            for city in range(n):
                if visited & (1 << city) and city != last:
                    new_visited = visited ^ (1 << last)
                    cost, _ = dp(new_visited, city)

                    total_cost = cost + distance_matrix[city][last]
                    
                    if total_cost < min_cost:
                        min_cost = total_cost
                        prev_city = city
            
            memo[(visited, last)] = (min_cost, prev_city)
            return min_cost, prev_city
        
        all_visited = (1 << n) - 1
        min_total = float('inf')
        last_city = -1
        
        for city in range(n):
            if city != start_idx:
                cost, _ = dp(all_visited, city)

                if cost < min_total:
                    min_total = cost
                    last_city = city
        
        route = []
        visited = all_visited
        current = last_city
        
        while current != -1:
            route.append(current)
            _, prev = memo.get((visited, current), (0, -1))

            if prev == -1:
                break
            
            visited ^= (1 << current)
            current = prev

        route.reverse()
        return route, min_total


    def optimize_route(self, addresses: list[str]):
        n = len(addresses)
        
        if n <= 1:
            return {
                "status": "success",
                "optimized_route": addresses,
                "distance (in km)": 0
            }
        
        try:
            distance_matrix = self._get_distance_matrix(addresses)
            route, distance = self._held_karp_algorithm(distance_matrix)

            optimized_route = [addresses[i] for i in route]
            return {
                "status": "success",
                "optimized_route": optimized_route,
                "distance (in km)": float(distance / 1000)
            }
        
        except Exception as error:
            return {
                "status": "error",
                "optimized_route": addresses,
                "distance (in km)": 0
            }

