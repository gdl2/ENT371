from flask import Flask, render_template, make_response, request, redirect, url_for
import os
import compress_json
import numpy as np

global THIS_FOLDER
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

app = Flask("__main__", template_folder=os.path.join(THIS_FOLDER, "templates"))

@app.route("/")
@app.route("/index")
def index():
    # Render the graphs initially at all 0 weights
    seniority_weight = 0.0
    fairness_weight = 0.0
    waittime_weight = 0.0
    my_file = os.path.join(THIS_FOLDER, "static", "{} {} {}.json.gz".format(seniority_weight, fairness_weight, waittime_weight))
    calculations = compress_json.load(my_file)

    html = render_template("index.html", calculations = calculations, maxTableCols = int(calculations["DriverTableColumns"]))
    response = make_response(html)
    return response

@app.route("/update_graphs", methods=['GET'])
def update_graphs():
    # Get weight and parameters from user
    seniority_weight = request.args.get('seniority_weight', default = 0.0, type = float)
    fairness_weight = request.args.get('fairness_weight', default = 0.0, type = float)
    waittime_weight = request.args.get('waittime_weight', default = 0.0, type = float)
    seniority_optimize = True if request.args.get('seniority_checkbox') == "true" else False
    fairness_optimize = True if request.args.get('fairness_checkbox') == "true" else False
    waittime_optimize = True if request.args.get('waittime_checkbox') == "true" else False

    print(seniority_weight, fairness_weight, waittime_weight)
    print(seniority_optimize, fairness_optimize, waittime_optimize)

    # Optimize: Run through all possible combinations of unlocked values (values that user selected to optimize)
    # and return the combination of seniority, fairness, and wait time weights that minimize the difference between
    # averages of passenger wait time (less is better) and negative driver income (more is better)
    possible_combinations = []
    range_of_values = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    if seniority_optimize:
        seniority_values = range_of_values
    else:
        seniority_values = [seniority_weight]
    if fairness_optimize:
        fairness_values = range_of_values
    else:
        fairness_values = [fairness_weight]
    if waittime_optimize:
        waittime_values = range_of_values
    else:
        waittime_values = [waittime_weight]

    best_diff_averages = float('inf')
    best_combination = [0.0, 0.0, 0.0]
    for i in seniority_values:
        for j in fairness_values:
            for k in waittime_values:
                print(i, j, k)

                my_file = os.path.join(THIS_FOLDER, "static", "{} {} {}.json.gz".format(i, j, k))
                calculations = compress_json.load(my_file)

                # Try to minimize the sum of passenger wait time (smaller better) and negative driver incomes (larger better)
                diff_averages = np.mean(calculations["PassengerWaitTimes"]) - np.mean(calculations["DriverIncomes"]) * 1000
                if diff_averages < best_diff_averages:
                    best_diff_averages = diff_averages
                    best_combination = [i, j, k]
                    print("Update best:", best_combination)

    i, j, k = best_combination
    i, j, k = seniority_weight, fairness_weight, waittime_weight
    my_file = os.path.join(THIS_FOLDER, "static", "{} {} {}.json.gz".format(i, j, k))
    calculations = compress_json.load(my_file)
    calculations["i"] = i
    calculations["j"] = j
    calculations["k"] = k

    maxTableCols = int(calculations["DriverTableColumns"])
    thead_cols = ""
    for i in range(maxTableCols):
        thead_cols += """<th scope="col">Passenger Trip {}</th>""".format(i+1)

    tbody = ""
    for i in range(len(calculations["DriverObjects"])):
        tbody += "<tr><td>Income: ${}<br>Months Active: {}</td>".format(round(calculations["DriverObjects"][i]["income_earned"]), round(calculations["DriverObjects"][i]["months_active"]))
        for n in range(maxTableCols):
            if n >= len(calculations["DriverObjects"][i]["lst_passenger_trips"]):
                tbody += "<td></td>"
            else:
                tbody += "<td>Trip Start Time: {} s<br>Wait Time: {} s<br>Trip Cost: ${}<br>Trip Length: {} mi</td>".format(
                round(calculations["DriverObjects"][i]["lst_passenger_trips"][n]["trip_start_time"]),
                round(calculations["DriverObjects"][i]["lst_passenger_trips"][n]["trip_wait_time"]),
                round(calculations["DriverObjects"][i]["lst_passenger_trips"][n]["trip_cost"]),
                round(calculations["DriverObjects"][i]["lst_passenger_trips"][n]["trip_length"]))
        tbody += "</tr>"

    new_table_html = """<table class="table">
                            <thead>
                              <tr>
                                <th scope="col">Driver</th>
                                {}
                              </tr>
                             </thead>
                             <tbody>
                                {}
                             </tbody>
                        </table>
    """.format(thead_cols, tbody)

    calculations["new_driver_table"] = new_table_html

    return calculations

#Comment out before updating PythonAnywhere
#app.run()
