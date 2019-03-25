import requests
import math
from dateutil import parser
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Flask
from flask import Markup
from flask import Flask
from flask import render_template

app = Flask(__name__)


@app.route("/")
def index():

    req = requests.get("https://odileeds.org/projects/petitions/241584.csv")
    data = req.content.decode("ascii")
    lines = data.splitlines()
    lines.pop(0)

    highest_count = lines[-1].split(",")[1]

    agg = defaultdict(lambda: defaultdict(list))

    now = None
    prev = None
    for row in lines:
        datestr, count = row.split(",")
        date = parser.parse(datestr)
        count = int(count)

        if not prev:
            prev = (date, count)
            continue

        elapsed = (date - prev[0]).total_seconds()
        signatures = count - prev[1]

        agg[(date.month, date.day)][date.hour].append(signatures / elapsed)
        now = datetime(year=date.year, month=date.month, day=date.day, hour=date.hour)

        prev = (date, count)

    sps_history = {}
    prev_rate = None
    for date, hours in agg.items():
        for hour in range(0, 24):
            rate = None
            if hour in hours:
                rate = sum(hours[hour]) / len(hours[hour])
                prev_rate = rate
            else:
                rate = prev_rate

            if rate:
                dt = datetime(year=now.year, month=date[0], day=date[1], hour=hour)
                if dt <= now:
                    sps_history[dt] = rate

    deltas = []
    for offset in range(0, 24):
        now_td = datetime(
            year=now.year, month=now.month, day=now.day, hour=now.hour
        ) - timedelta(hours=offset)
        now_yd = now_td - timedelta(days=1)
        deltas.append((1 / sps_history[now_yd]) * sps_history[now_td])

    delta_pct = sum(deltas) / len(deltas)

    current = int(highest_count)
    target = round(current, -6) + 1000000

    future_hours = 0
    one_day_ago = datetime(
        year=now.year, month=now.month, day=now.day, hour=now.hour
    ) - timedelta(days=1)
    prev_td = one_day_ago

    decayed_delta_pct = delta_pct

    while current < target:
        future_hours += 1
        prev_td += timedelta(hours=1)

        predict = sps_history[prev_td] * decayed_delta_pct
        predict_increase = predict * 60 * 60
        current += predict_increase

        if prev_td >= now:
            prev_td = one_day_ago

        if future_hours % 24 == 0:
            decayed_delta_pct = decayed_delta_pct * delta_pct

        if current >= target:
            break

    future_td = datetime(
        year=now.year, month=now.month, day=now.day, hour=now.hour
    ) + timedelta(hours=future_hours)
    print("%s votes at %s" % (target, future_td))

    labels = sps_history.keys()
    values = [int(v * 60 * 60) for v in sps_history.values()]
    return render_template(
        "index.html", values=values, labels=labels, target=target, countdown=future_td
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0")
