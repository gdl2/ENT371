from flask import Flask, render_template, make_response, request, redirect, url_for
import os
import compress_json

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
    my_file = os.path.join(THIS_FOLDER, "static", "{} {} {}.json.gz".format(seniority_weight, fairness_weight, waittime_weight))
    calculations = compress_json.load(my_file)

    return calculations

#Comment out before updating PythonAnywhere
app.run()
