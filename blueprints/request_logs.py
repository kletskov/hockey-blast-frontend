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

CRAWLER_USER_AGENTS = [
    # Manual additions per eyeballing
    'Google-Read-Aloud',

    # Major Search Engines
    'Google',
    'Googlebot',
    'Bingbot',
    'Slurp',
    'DuckDuckBot',
    'Baiduspider',
    'YandexBot',
    'Sogou',
    'Exabot',
    'facebot',  # Facebook
    'facebookexternalhit',
    'ia_archiver',  # Alexa

    # AI and Data Crawlers
    'GPTBot',
    'Bytespider',
    'ClaudeBot',
    'openai',
    'InternetMeasurement',
    'Amazonbot',
    'CriteoBot',

    # Pen-testing and Research
    'zgrab',
    'zmap',
    'masscan',
    'nmap',
    'censys',
    'shodan',
    'httpx',

    # Dev tools / CLI / Libraries
    'curl',
    'wget',
    'python-requests',
    'httpie',
    'libwww-perl',
    'Go-http-client',
    'Apache-HttpClient',
    'java',
    'okhttp',
    'axios',
    'node-fetch',
    'scrapy',
    'aiohttp',
    'RestSharp',

    # Headless browsers
    'HeadlessChrome',
    'puppeteer',
    'phantomjs',
    'selenium',
    'Playwright',

    # Generic indicators
    'bot',
    'spider',
    'crawler',
    'scanner',
    'probe'
]

def get_request_logs_data(interval, top_n=20):
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
        return None, None, None, None, None

    logs = db.session.query(RequestLog).filter(RequestLog.timestamp >= start_time).all()
    if not logs:
        return pd.Series([], dtype='int64'), pd.Series([], dtype='int64'), pd.DataFrame(), pd.DataFrame(), []

    df = pd.DataFrame([(log.timestamp, log.path, log.client_ip, log.user_agent) for log in logs], columns=['timestamp', 'path', 'client_ip', 'user_agent'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Filter out non-existing endpoints
    registered_endpoints = [rule.rule for rule in current_app.url_map.iter_rules()]
    df = df[df['path'].isin(registered_endpoints)]

    # Filter out internal endpoints using regular expressions
    for pattern in INTERNAL_ENDPOINTS:
        df = df[~df['path'].str.match(pattern)]

    # Filter out known crawlers by inspecting the user_agent field

    import re

    pattern = re.compile('|'.join(CRAWLER_USER_AGENTS), flags=re.IGNORECASE)
    df = df[~df['user_agent'].str.contains(pattern, na=False)]

    # for crawler in CRAWLER_USER_AGENTS:
    #     df = df[~df['user_agent'].str.contains(crawler, case=False, na=False)]

    request_counts = df.resample(freq).size()
    unique_ip_counts = df.resample(freq)['client_ip'].nunique()

    endpoint_counts = df.groupby('path').resample(freq).size().unstack(level=0, fill_value=0)

    # Calculate average number of hits per session
    session_counts = df.groupby('client_ip').resample(freq).size()
    session_counts = session_counts[session_counts > 0]  # Filter out zeroes
    session_stats = session_counts.groupby(level=1).agg(['mean', 'min', 'max'])

    # Sample logs grouped by client_ip
    sample_logs = (
        df.reset_index()  # Ensure `timestamp` is preserved
        .groupby('client_ip')
        .apply(lambda group: group.iloc[0])  # Take the first log per client_ip
        .sort_values(by='timestamp', ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    sample_logs_data = sample_logs[['timestamp', 'client_ip', 'path', 'user_agent']].to_dict(orient='records')

    return request_counts, unique_ip_counts, endpoint_counts, session_stats, sample_logs_data

def simplify_endpoint(endpoint):
    parts = endpoint.strip('/').split('/')
    if len(parts) > 1 and parts[-1] == parts[-2]:
        return '/' + '/'.join(parts[:-1])
    return endpoint

@request_logs_bp.route('/request_logs', methods=['GET'])
def request_logs():
    interval = request.args.get('interval', 'daily')
    top_n = int(request.args.get('top_n', 20))
    request_counts, unique_ip_counts, endpoint_counts, session_stats, sample_logs_data = get_request_logs_data(interval, top_n)

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

    # Plot for average hits per session
    avg_hits_plot_data = [
        go.Scatter(x=session_stats.index, y=session_stats['mean'], mode='lines', name='Avg Hits per Session'),
        go.Scatter(x=session_stats.index, y=session_stats['min'], mode='lines', name='Min Hits per Session'),
        go.Scatter(x=session_stats.index, y=session_stats['max'], mode='lines', name='Max Hits per Session')
    ]

    avg_hits_plot_layout = go.Layout(
        title=f'Hits per Session ({interval.capitalize()})',
        xaxis=dict(title='Time'),
        yaxis=dict(title='Hits'),
        plot_bgcolor='#f9f9f9',
        paper_bgcolor='#ffffff',
        font=dict(color='#333')
    )

    avg_hits_plot_fig = go.Figure(data=avg_hits_plot_data, layout=avg_hits_plot_layout)
    avg_hits_plot_div = pio.to_html(avg_hits_plot_fig, full_html=False)

    return render_template(
        'request_logs.html',
        plot_div=plot_div,
        avg_hits_plot_div=avg_hits_plot_div,
        interval=interval,
        sample_logs_data=sample_logs_data
    )

@request_logs_bp.route('/request_logs/data', methods=['GET'])
def request_logs_data():
    interval = request.args.get('interval', 'daily')
    request_counts, unique_ip_counts, endpoint_counts, session_stats, sample_logs_data = get_request_logs_data(interval)

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
        'endpoint_counts': {f"{simplified_endpoint} {total_hits}": endpoint_counts[next(ep for ep in endpoint_counts.columns if simplify_endpoint(ep) == simplified_endpoint)].tolist() for simplified_endpoint, total_hits in endpoint_hits},
        'avg_hits_per_session': session_stats['mean'].values.tolist(),
        'min_hits_per_session': session_stats['min'].values.tolist(),
        'max_hits_per_session': session_stats['max'].values.tolist()
    }

    return jsonify(data)
