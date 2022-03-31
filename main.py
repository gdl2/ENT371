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
    seniority_weight = 0
    fairness_weight = 0
    waittime_weight = 0
    my_file = os.path.join(THIS_FOLDER, "static", "{} {} {}.json.gz".format(seniority_weight, fairness_weight, waittime_weight))
    calculations = compress_json.load(my_file)

    html = render_template("index.html", calculations = calculations)
    response = make_response(html)
    return response

@app.route("/update_graphs", methods=['GET'])
def update_graphs():
    seniority_weight = request.args.get('seniority_weight', default = 0, type = int)
    fairness_weight = request.args.get('fairness_weight', default = 0, type = int)
    waittime_weight = request.args.get('waittime_weight', default = 0, type = int)
    seniority_optimize = True if request.args.get('seniority_checkbox') == "true" else False
    fairness_optimize = True if request.args.get('fairness_checkbox') == "true" else False
    waittime_optimize = True if request.args.get('waittime_checkbox') == "true" else False

    print(seniority_optimize, fairness_optimize, waittime_optimize)

    possible_combinations = []
    range_of_values = range(0, 120, 20)
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
    best_combination = [0, 0, 0]
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
                    print("BEST", best_combination)

    i, j, k = best_combination
    my_file = os.path.join(THIS_FOLDER, "static", "{} {} {}.json.gz".format(i, j, k))
    calculations = compress_json.load(my_file)
    calculations["i"] = i
    calculations["j"] = j
    calculations["k"] = k

    return calculations

#Comment out before updating PythonAnywhere
#app.run()
