from flask import Blueprint, render_template, request, jsonify, current_app
from hockey_blast_common_lib.models import db, RequestLog
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
import re

request_logs_bp = Blueprint('request_logs', __name__)

# List of internal endpoints to filter out
INTERNAL_ENDPOINTS = [
    r'/dropdowns/.*',
    r'/.*filter_.*',
    r'/get_.*',
]

def get_request_logs_data(interval):
    now = datetime.now()
    if interval == 'minutely':
        start_time = now - timedelta(hours=1)
        freq = 'T'
    elif interval == 'hourly':
        start_time = now - timedelta(hours=24)
        freq = 'H'
    elif interval == 'daily':
        start_time = now - timedelta(days=30)
        freq = 'D'
    elif interval == 'weekly':
        start_time = now - timedelta(weeks=12)
        freq = 'W'
    elif interval == 'monthly':
        start_time = now - timedelta(days=365)
        freq = 'M'
    else:
        return None, None, None

    logs = db.session.query(RequestLog).filter(RequestLog.timestamp >= start_time).all()
    if not logs:
        return pd.Series([], dtype='int64'), pd.Series([], dtype='int64'), pd.DataFrame()

    df = pd.DataFrame([(log.timestamp, log.path, log.client_ip) for log in logs], columns=['timestamp', 'path', 'client_ip'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Filter out non-existing endpoints
    registered_endpoints = [rule.rule for rule in current_app.url_map.iter_rules()]
    df = df[df['path'].isin(registered_endpoints)]

    # Filter out internal endpoints using regular expressions
    for pattern in INTERNAL_ENDPOINTS:
        df = df[~df['path'].str.match(pattern)]

    request_counts = df.resample(freq).size()
    unique_ip_counts = df.resample(freq)['client_ip'].nunique()

    endpoint_counts = df.groupby('path').resample(freq).size().unstack(level=0, fill_value=0)

    return request_counts, unique_ip_counts, endpoint_counts

def simplify_endpoint(endpoint):
    parts = endpoint.strip('/').split('/')
    if len(parts) > 1 and parts[-1] == parts[-2]:
        return '/' + '/'.join(parts[:-1])
    return endpoint

@request_logs_bp.route('/request_logs', methods=['GET'])
def request_logs():
    interval = request.args.get('interval', 'daily')
    request_counts, unique_ip_counts, endpoint_counts = get_request_logs_data(interval)

    endpoint_hits = []
    for endpoint in endpoint_counts.columns:
        total_hits = endpoint_counts[endpoint].sum()
        simplified_endpoint = simplify_endpoint(endpoint)
        endpoint_hits.append((simplified_endpoint, total_hits))

    # Sort the endpoints by total hits in descending order
    endpoint_hits.sort(key=lambda x: x[1], reverse=True)

    plot_data = [
        go.Scatter(x=request_counts.index, y=request_counts.values, mode='lines', name='Total Requests')
    ]

    for simplified_endpoint, total_hits in endpoint_hits:
        endpoint = next(ep for ep in endpoint_counts.columns if simplify_endpoint(ep) == simplified_endpoint)
        plot_data.append(go.Scatter(x=endpoint_counts.index, y=endpoint_counts[endpoint], mode='lines', name=f"{simplified_endpoint} {total_hits}"))

    plot_layout = go.Layout(
        title=f'Request Logs ({interval.capitalize()})',
        xaxis=dict(title='Time'),
        yaxis=dict(title='Count'),
        plot_bgcolor='#f9f9f9',
        paper_bgcolor='#ffffff',
        font=dict(color='#333')
    )

    plot_fig = go.Figure(data=plot_data, layout=plot_layout)
    plot_div = pio.to_html(plot_fig, full_html=False)

    return render_template('request_logs.html', plot_div=plot_div, interval=interval)

@request_logs_bp.route('/request_logs/data', methods=['GET'])
def request_logs_data():
    interval = request.args.get('interval', 'daily')
    request_counts, unique_ip_counts, endpoint_counts = get_request_logs_data(interval)

    endpoint_hits = []
    for endpoint in endpoint_counts.columns:
        total_hits = endpoint_counts[endpoint].sum()
        simplified_endpoint = simplify_endpoint(endpoint)
        endpoint_hits.append((simplified_endpoint, total_hits))

    # Sort the endpoints by total hits in descending order
    endpoint_hits.sort(key=lambda x: x[1], reverse=True)

    data = {
        'timestamps': request_counts.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
        'request_counts': request_counts.values.tolist(),
        'unique_ip_counts': unique_ip_counts.values.tolist(),
        'endpoint_counts': {f"{simplified_endpoint} {total_hits}": endpoint_counts[next(ep for ep in endpoint_counts.columns if simplify_endpoint(ep) == simplified_endpoint)].tolist() for simplified_endpoint, total_hits in endpoint_hits}
    }

    return jsonify(data)
