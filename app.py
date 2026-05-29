from flask import Flask, render_template, jsonify
import glob, csv

app = Flask(__name__)

def latest_ranked():
    files = sorted(glob.glob('processed_data_*.csv'))
    return files[-1] if files else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def data():
    f = latest_ranked()
    if not f: return jsonify([])
    with open(f) as fp:
        return jsonify(list(csv.DictReader(fp)))

if __name__ == '__main__':
    app.run(port=5050)
