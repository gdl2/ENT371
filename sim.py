# Import the following libraries
import csv
import numpy as np
from random import sample, seed
import os
import compress_json
import requests
import time as t
from geopy.distance import great_circle

#import asyncio
#import aiohttp


# Supplement driver data
# Each driver has 3 features: home_zipcode [static], months_active [static], income_earned [dynamic], time_driving [dynamic], end_trip_time [dynamic]
# The driver wants to return to their home_zipcode at the end of the day
# The driver wants to maximize income_earned per day
# The driver wants to minimize time_driving per day
# (Currently ignoring cost of vehicle miles driven)

# Dictionary for driver objects
DRIVERS_DICT = {}

# Read the csv file
with open("Jan22Drivers.csv", 'r', encoding='utf-8-sig') as file:
    # Init csvreader object of file
    csvreader = csv.reader(file)
    # Extract column headers
    header = next(csvreader)
    # Find index for each column header
    month_reported_index = header.index("MONTH_REPORTED")
    driver_start_month_index = header.index("DRIVER_START_MONTH")
    home_zipcode_index = header.index("ZIP")

    driver_id = 0
    # Iterate through rows
    for row in csvreader:
        # Create driver object for each row in file
        driver = {}

        # Populate values for driver by indexing into the spreadsheet
        driver["home_zipcode"] = row[home_zipcode_index]

        curr_year_month = row[month_reported_index].split("-")
        start_year_month = row[driver_start_month_index].split("-")
        months_active = (int(curr_year_month[0]) - int(start_year_month[0])) * 12 + int(curr_year_month[1]) - int(start_year_month[1])
        driver["months_active"] = months_active

        driver["income_earned"] = 0 # Will be updated in matching
        driver["time_driving"] = 0 # Will be updated in matching
        driver["end_trip_time"] = 0 # Will be updated in matching
        driver["lat"] = None # Will be updated in matching
        driver["lon"] = None # Will be updated in matching

        driver_id += 1

        DRIVERS_DICT[str(driver_id)] = driver

print("NUMBER OF DRIVERS:", len(DRIVERS_DICT))


# Extract passenger-trip data
# Each passenger-trip has 7 features: trip_request_time (in seconds), trip_start_time (in seconds), trip_wait_time (in seconds), trip_duration (in seconds), trip_length (in miles), trip_cost (in dollars), pickup_lat, pickup_lon, dropoff_lat, dropoff_lon
# The passenger wants to minimize wait_time
# The passenger wants to minimize trip_cost
# The trip_request_time is the moment the passenger requests a vehicle


SINGLE_PASSENGER_TRIPS_DICT = {}

COST_PER_VEHICLE_MILE = 2
COST_PER_DRIVER_MINUTE = 0.5

# Read the csv file
with open("Jan0122Trips.csv", 'r', encoding='utf-8-sig') as file:
    csvreader = csv.reader(file)

    # Extract column headers
    header = next(csvreader)

    # Find index for each column header
    trip_start_time_index = header.index("Trip Start Timestamp")
    trip_duration_index = header.index("Trip Seconds")
    trip_length_index = header.index("Trip Miles")
    pickup_lat_index = header.index("Pickup Centroid Latitude")
    pickup_lon_index = header.index("Pickup Centroid Longitude")
    dropoff_lat_index = header.index("Dropoff Centroid Latitude")
    dropoff_lon_index = header.index("Dropoff Centroid Longitude")

    # Generate request start times for passenger trips
    mu, sigma = 1, 1 # mean and standard deviation
    trip_wait_time = np.random.lognormal(mu, sigma, 100000)
    trip_wait_time = [min(elem, 15) for elem in trip_wait_time]

    num_null_rows = 0
    rider_id = 0
    # Iterate through rows
    for row in csvreader:
        # Make sure row has no entries missing
        if row[trip_start_time_index] and row[trip_duration_index] and row[trip_length_index] and row[pickup_lat_index] and row[pickup_lon_index] and row[dropoff_lat_index] and row[dropoff_lon_index]:
            single_passenger_trip = {} # create passenger_trip

            date, time, ampm = row[trip_start_time_index].split()
            hour_to_seconds = (int(time.split(":")[0]) % 12) * 3600
            minutes_to_seconds = int(time.split(":")[1]) * 60
            pm_to_seconds = 0
            if ampm == "PM":
                pm_to_seconds = 12*60*60
            trip_start_time = hour_to_seconds + minutes_to_seconds + pm_to_seconds
            single_passenger_trip["trip_start_time"] = trip_start_time

            single_passenger_trip["trip_request_time"] = max(trip_start_time - trip_wait_time[rider_id], 0) # Cannot be negative

            trip_duration = int(row[trip_duration_index])
            single_passenger_trip["trip_duration"] = trip_duration

            trip_length = float(row[trip_length_index])
            single_passenger_trip["trip_length"] = trip_length

            trip_cost = COST_PER_VEHICLE_MILE * trip_length + COST_PER_DRIVER_MINUTE * (trip_duration % 60)
            single_passenger_trip["trip_cost"] = trip_cost

            pickup_lat = float(row[pickup_lat_index])
            single_passenger_trip["pickup_lat"] = pickup_lat
            pickup_lon = float(row[pickup_lon_index])
            single_passenger_trip["pickup_lon"] = pickup_lon
            dropoff_lat = float(row[dropoff_lat_index])
            single_passenger_trip["dropoff_lat"] = dropoff_lat
            dropoff_lon = float(row[dropoff_lon_index])
            single_passenger_trip["dropoff_lon"] = dropoff_lon

            rider_id += 1

            SINGLE_PASSENGER_TRIPS_DICT[str(rider_id)] = single_passenger_trip
        else:
            num_null_rows += 1


    #print("NUMBER OF NULL ROWS:", num_null_rows)

print("NUMBER OF SINGLE-PASSENGER-TRIPS:", len(SINGLE_PASSENGER_TRIPS_DICT))

# async def get_route_distance_duration(session, url):
#     async with session.get(url) as resp:
#         res = await resp.json()
#         route_distance = res['routes'][0]['distance']
#         route_duration = res['routes'][0]['duration']
#         return route_distance, route_duration
#
#
# async def getDriversDriveTime(lst_driver_locations, passenger_location):
#     async with aiohttp.ClientSession() as session:
#         tasks = []
#         url = "http://127.0.0.1:5000/route/v1/driving/"
#         for driver_location in lst_driver_locations:
#             loc = "{},{};{},{}".format(driver_location[1], driver_location[0], passenger_location[1], passenger_location[0])
#             tasks.append(asyncio.ensure_future(get_route_distance_duration(session, url+loc)))
#         lst_route_distance_duration = await asyncio.gather(*tasks)
#
#         return lst_route_distance_duration

TRAVEL_TIME_PER_VEHICLE_MILE = 180

def by_second_elem(tuple):
    return tuple[1]

# Takes a single_passenger_trip object, driver_months_active_weight (how important is seniority), driver_income_earned_weight (how important is fairness), passenger_wait_time_weight (how important is decreasing passenger wait time), target_income_earned (how much should drivers be earning on the platform)
# Ranks all available drivers by summing positive driver weights and negative passenger weights
# Returns the driver object to be assigned to the single_passenger_trip
def rank_drivers(dict_drivers, single_passenger_trip, driver_seniority_weight, driver_fairness_weight, driver_waittime_weight):
    # Rankings of drivers within parameters (lower is better)
    # List of tuples: (driverid, seniority)
    seniority_ranking = []
    # List of tuples: (driverid, fairness)
    fairness_ranking = []
    # List of tuples: (driverid, waittime)
    waittime_ranking = []

    # Final ranking of drivers (lower is better)
    final_driver_ranking = []

    # lst_driver_locations = [(driver["lat"], driver["lon"]) for driver in dict_drivers.values()]
    # passenger_location = (single_passenger_trip["pickup_lat"], single_passenger_trip["pickup_lon"])
    # lst_route_distance_duration = asyncio.run(getDriversDriveTime(lst_driver_locations, passenger_location))
    # lst_drivers_drive_time = [tuple[1] for tuple in lst_route_distance_duration]

    for driverid, driver in dict_drivers.items():
        seniority_ranking.append((driverid, driver["months_active"]))
        fairness_ranking.append((driverid, driver["income_earned"]))
        driver_location = (driver["lat"], driver["lon"])
        passenger_location = (single_passenger_trip["pickup_lat"], single_passenger_trip["pickup_lon"])
        #route_distance, route_duration = getRouteMeta(driver_location, passenger_location)
        passenger_wait_time = max(0, driver["end_trip_time"] - single_passenger_trip["trip_request_time"]) + (great_circle(driver_location, passenger_location).miles * TRAVEL_TIME_PER_VEHICLE_MILE) #lst_drivers_drive_time[driverid]
        waittime_ranking.append((driverid, passenger_wait_time))

    seniority_ranking.sort(reverse=True, key=by_second_elem)
    fairness_ranking.sort(reverse=False, key=by_second_elem)
    waittime_ranking.sort(reverse=False, key=by_second_elem)

    seniority_ranking_driverid = [tuple[0] for tuple in seniority_ranking]
    fairness_ranking_driverid = [tuple[0] for tuple in fairness_ranking]
    waittime_ranking_driverid = [tuple[0] for tuple in waittime_ranking]

    for driverid in dict_drivers.keys():
        driver_seniority_ranking = seniority_ranking_driverid.index(driverid)
        driver_fairness_ranking = fairness_ranking_driverid.index(driverid)
        driver_waittime_ranking = waittime_ranking_driverid.index(driverid)

        driver_overall_score = driver_seniority_ranking * driver_seniority_weight + driver_fairness_ranking * driver_fairness_weight + driver_waittime_ranking * driver_waittime_weight

        final_driver_ranking.append((driverid, driver_overall_score))

    final_driver_ranking.sort(reverse=False, key=by_second_elem)
    print(final_driver_ranking)
    top_driver_id = final_driver_ranking[0][0]
    return top_driver_id, passenger_wait_time


def assign_drivers_to_passengers(dict_passenger_trips, dict_drivers, driver_months_active_weight, driver_income_earned_weight, passenger_wait_time_weight):
    for passengerid, passenger_trip in dict_passenger_trips.items():
        #print("passengerid:", passengerid)
        # Get top ranked driver
        driverid, passenger_wait_time = rank_drivers(dict_drivers, passenger_trip, driver_months_active_weight, driver_income_earned_weight, passenger_wait_time_weight)
        # Assign top driver to passenger
        #print(driverid)
        top_driver = dict_drivers[driverid]
        top_driver["lat"] = passenger_trip["dropoff_lat"]
        top_driver["lon"] = passenger_trip["dropoff_lon"]
        top_driver["time_driving"] += passenger_trip["trip_duration"]
        top_driver["income_earned"] += passenger_trip["trip_cost"]
        passenger_trip["trip_wait_time"] = passenger_wait_time
        passenger_trip["trip_start_time"] = passenger_trip["trip_request_time"] + passenger_wait_time
        top_driver["end_trip_time"] = passenger_trip["trip_start_time"] + passenger_trip["trip_duration"]


seed(42)
# Take a random sample of _ passenger trips
random_sample_p = sample(range(1, len(SINGLE_PASSENGER_TRIPS_DICT)), 10)

# Take a random sample of _ drivers
random_sample_d = sample(range(1, len(DRIVERS_DICT)), 10)

# Cache all possible combinations of parameters - reduces CPU usage on server and allows low latency to user
range_of_values = [0, .2, .4, .6, .8, 1]
for i in range_of_values:
    for j in range_of_values:
        for k in range_of_values:
            print(i, j, k)
            start_time = t.time()

            # Make copy of random sample of passenger trips each iteration, otherwise values from previous iteration are passed over
            random_sample_passenger_trips_dict = {}
            for idx in random_sample_p:
                random_sample_passenger_trips_dict[str(idx)] = SINGLE_PASSENGER_TRIPS_DICT[str(idx)].copy()

            # Make copy of random sample of drivers each iteration, otherwise values from previous iteration are passed over
            random_sample_drivers_dict = {}
            for idx in random_sample_d:
                random_sample_drivers_dict[str(idx)] = DRIVERS_DICT[str(idx)].copy()

            # Last 4 variables correspond to: driver_months_active_weight, driver_income_earned_weight, passenger_wait_time_weight
            assign_drivers_to_passengers(random_sample_passenger_trips_dict, random_sample_drivers_dict, i, j, k)

            calculations = {"DriverIncomes": [], "PassengerWaitTimes": []}
            # Record the driver income for each driver in our sample
            for id, driver in random_sample_drivers_dict.items():
                calculations["DriverIncomes"].append(driver["income_earned"])

            # Record the passenger wait time for each passenger in our sample
            for id, passenger in random_sample_passenger_trips_dict.items():
                calculations["PassengerWaitTimes"].append(passenger["trip_wait_time"])

            my_file = "static/{} {} {}.json.gz".format(i, j, k)
            print(my_file)

            # Cache the compressed driver incomes and passenger wait times in the static folder
            compress_json.dump(calculations, my_file)

            print("TIME PASSED:", t.time() - start_time)

            #
            # lst_of_driver_months_active = []
            #
            # lst_driver_incomes_vs_months_active = list(zip(lst_of_driver_months_active, lst_of_driver_incomes))
            #
            # header =  ["Driver Income"]
            # with open('driverincome.csv', 'w', encoding='UTF8', newline='') as f:
            #     writer = csv.writer(f)
            #     # write the header
            #     writer.writerow(header)
            #
            #     # write multiple rows
            #     writer.writerows([[elem] for elem in lst_of_driver_incomes])
            #
            # print("DISTRIBUTION OF DRIVER INCOMES")
            # print("mean:", np.mean(lst_of_driver_incomes))
            # print("median:", np.median(lst_of_driver_incomes))
            # print("std:", np.std(lst_of_driver_incomes))
            #
            # for id, passenger in random_sample_passenger_trips_dict.items():
            #     lst_of_passenger_waittimes.append(passenger["trip_wait_time"])
            #
            # lst_driver_incomes_vs_waittimes = list(zip(lst_of_passenger_waittimes, lst_of_driver_incomes))
            #
            # header =  ["Passenger Wait Time", "Driver Income"]
            # with open('passengerwaittime.csv', 'w', encoding='UTF8', newline='') as f:
            #     writer = csv.writer(f)
            #     # write the header
            #     writer.writerow(header)
            #
            #     # write multiple rows
            #     writer.writerows(lst_driver_incomes_vs_waittimes)
            #
            # print("DISTRIBUTION OF PASSENGER WAIT TIMES")
            # print("mean:", np.mean(lst_of_passenger_waittimes))
            # print("median:", np.median(lst_of_passenger_waittimes))
            # print("std:", np.std(lst_of_passenger_waittimes))
