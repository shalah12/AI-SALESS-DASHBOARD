import os
import csv
import dash
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from datetime import timedelta
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from io import StringIO
import plotly.io as pio
from dash import dash_table
import base64

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.permanent_session_lifetime = timedelta(days=30)
bcrypt = Bcrypt(app)

# Only initialize Dash if it hasn't been initialized before
if 'dash_app' not in app.extensions:
    dash_app = Dash(
        __name__,
        server=app,
        url_base_pathname='/dashboard/',
        suppress_callback_exceptions=True
    )
    app.extensions['dash_app'] = dash_app  # Store the instance in app's extensions

   
CREDENTIALS_FILE = 'users.csv'
DATA_FILE = r'C:\Users\FBDA21-023\Downloads\sales_data.csv' 
EXPORT_PATH = r'C:\Users\FBDA21-023\OneDrive - Botswana Accountancy College\Downloads'

def load_sales_data():
    try:
        # Read the CSV file directly into a DataFrame
        df = pd.read_csv(DATA_FILE)
        
        # Clean and convert date column if it exists
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.dropna(subset=['date'])  # Remove rows with invalid dates
        
        # Ensure numeric columns are properly typed
        numeric_cols = ['value', 'response_time', 'http_status']  # Add other numeric columns as needed
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()  # Fallback empty dataframe

# Load the cleaned data
df = load_sales_data()

def load_users():
    users = {}
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'username' in row and 'password' in row:
                    users[row['username']] = row['password']
    return users

def save_user(username, password_hash):
    exists = os.path.exists(CREDENTIALS_FILE)
    with open(CREDENTIALS_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(['username', 'password'])
        writer.writerow([username, password_hash])

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        remember = 'remember' in request.form

        if username in users and bcrypt.check_password_hash(users[username], password):
            session['user'] = username
            session.permanent = remember
            return redirect('/dashboard/')
        else:
            flash('Invalid username or password')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        users = load_users()

        if username in users:
            flash("Username already exists.")
        else:
            hashed = bcrypt.generate_password_hash(password).decode('utf-8')
            save_user(username, hashed)
            flash("Registered successfully!")
            return redirect(url_for('login'))
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        users = load_users()
        username = session['user']
        if bcrypt.check_password_hash(users[username], current_password):
            users[username] = bcrypt.generate_password_hash(new_password).decode('utf-8')
            with open(CREDENTIALS_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['username', 'password'])
                for u, p in users.items():
                    writer.writerow([u, p])
            flash("Password changed.")
        else:
            flash("Incorrect current password.")
    return render_template_string(CHANGE_PASSWORD_TEMPLATE)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return dash_app.index()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Login Page Template
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
<style>
body { background-color: #f8f9fa; color: #212529; font-family: Arial, sans-serif; }
.container { max-width: 400px; margin-top: 100px; }
.form-control { border-radius: 25px; }
.btn-primary { border-radius: 25px; }
.alert { border-radius: 25px; }
</style>
</head>
<body>
<div class="container">
<h3 class="mb-4 text-center">Login</h3>
<form method="POST" class="p-4 border rounded bg-white shadow-sm">
{% with messages = get_flashed_messages() %}
{% if messages %}
<div class="alert alert-danger">{{ messages[0] }}</div>
{% endif %}
{% endwith %}
<div class="mb-3">
<label class="form-label">Username</label>
<input name="username" class="form-control" required>
</div>
<div class="mb-3">
<label class="form-label">Password</label>
<input name="password" type="password" id="password" class="form-control" required>
<input type="checkbox" onclick="togglePassword()"> Show Password
</div>
<div class="form-check mb-3">
<input type="checkbox" name="remember" class="form-check-input" id="remember">
<label class="form-check-label" for="remember">Remember Me</label>
</div>
<button type="submit" class="btn btn-primary w-100">Login</button>
<div class="mt-3 text-center">
<a href="/register" class="text-primary">Register</a>
</div>
</form>
</div>
<script>
function togglePassword() {
  var x = document.getElementById("password");
  x.type = x.type === "password" ? "text" : "password";
}
</script>
</body>
</html>
"""

REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Register</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
<style>
body { background-color: #f8f9fa; color: #212529; font-family: Arial, sans-serif; }
.container { max-width: 400px; margin-top: 100px; }
.form-control { border-radius: 25px; }
.btn-success { border-radius: 25px; }
</style>
</head>
<body>
<div class="container">
<h3 class="mb-4 text-center">Register</h3>
<form method="POST" class="p-4 border rounded bg-white shadow-sm">
{% with messages = get_flashed_messages() %}
{% if messages %}
<div class="alert alert-info">{{ messages[0] }}</div>
{% endif %}
{% endwith %}
<div class="mb-3">
<label class="form-label">Username</label>
<input name="username" class="form-control" required>
</div>
<div class="mb-3">
<label class="form-label">Password</label>
<input name="password" type="password" class="form-control" required>
</div>
<button type="submit" class="btn btn-success w-100">Register</button>
<div class="mt-3 text-center">
<a href="/" class="text-primary">Back to Login</a>
</div>
</form>
</div>
</body>
</html>
"""

CHANGE_PASSWORD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Change Password</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
<style>
body { background-color: #f8f9fa; color: #212529; font-family: Arial, sans-serif; }
.container { max-width: 400px; margin-top: 100px; }
.form-control { border-radius: 25px; }
.btn-warning { border-radius: 25px; }
</style>
</head>
<body>
<div class="container">
<h3 class="mb-4 text-center">Change Password</h3>
<form method="POST" class="p-4 border rounded bg-white shadow-sm">
{% with messages = get_flashed_messages() %}
{% if messages %}
<div class="alert alert-info">{{ messages[0] }}</div>
{% endif %}
{% endwith %}
<div class="mb-3">
<label class="form-label">Current Password</label>
<input name="current_password" type="password" class="form-control" required>
</div>
<div class="mb-3">
<label class="form-label">New Password</label>
<input name="new_password" type="password" class="form-control" required>
</div>
<button type="submit" class="btn btn-warning w-100">Change Password</button>
<div class="mt-3 text-center">
<a href="/dashboard" class="text-primary">Back to Dashboard</a>
</div>
</form>
</div>
</body>
</html>
"""



# Light theme colors
BACKGROUND_COLOR = '#f5f7fa'  # Changed to a light gray background
CARD_COLOR = '#ffffff'
TEXT_COLOR = '#212529'
PRIMARY_COLOR = '#0d6efd'
SECONDARY_COLOR = '#6c757d'
SUCCESS_COLOR = '#198754'
WARNING_COLOR = '#ffc107'
DANGER_COLOR = '#dc3545'
INFO_COLOR = '#0dcaf0'

# Card style
CARD_STYLE = {
    'backgroundColor': CARD_COLOR,
    'borderRadius': '8px',
    'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
    'padding': '12px',
    'margin': '6px',
    'color': TEXT_COLOR,
    'flex': '1',
    'minWidth': '140px',
    'textAlign': 'center'
}

DASH_NO_SCROLL_CSS = {
    'backgroundColor': BACKGROUND_COLOR,
    'height': '100vh',
    'overflow': 'hidden',
    'padding': '0',
    'fontFamily': 'Segoe UI, Arial, sans-serif',
    'display': 'flex',
    'flexDirection': 'column'
}

filter_dropdown_style = {
    'backgroundColor': CARD_COLOR,
    'color': TEXT_COLOR,
    'fontSize': '12px',
    'border': '1px solid #ced4da',
    'width': '100%',
    'minHeight': '32px',  # Reduced height
    'zIndex': 9999  # Ensure dropdowns appear above other elements
}

filter_container_style = {
    'backgroundColor': CARD_COLOR,
    'padding': '8px',
    'borderRadius': '8px',
    'marginBottom': '12px',
    'display': 'flex',
    'flexWrap': 'wrap',
    'gap': '8px',
    'alignItems': 'center'
}

def dashboard_overview_layout():
    if df.empty:
        return html.Div("No data available", style={'color': TEXT_COLOR, 'padding': '20px'})

    # Calculate metrics
    total_jobs = len(df)
    demo_requests = len(df[df['job_type'] == 'Demo']) if 'job_type' in df.columns else 0
    promo_requests = len(df[df['job_type'] == 'Promo Event']) if 'job_type' in df.columns else 0
    ai_requests = len(df[df['job_type'] == 'AI Assistant']) if 'job_type' in df.columns else 0

    # Job type distribution
    if 'job_type' in df.columns:
        job_counts = df['job_type'].value_counts().reset_index()
        job_counts.columns = ['job_type', 'count']
        job_types = job_counts['job_type'].tolist()
        job_values = job_counts['count'].tolist()
    else:
        job_types = []
        job_values = []

    # Group by continent
    if 'continent' in df.columns:
        geo_counts = df['continent'].value_counts().reset_index()
        geo_counts.columns = ['continent', 'count']
        geo_labels = geo_counts['continent'].tolist()
        geo_values = geo_counts['count'].tolist()
    else:
        geo_labels = []
        geo_values = []

    # Age group distribution
    if 'age_group' in df.columns:
        age_counts = df['age_group'].value_counts().reset_index()
        age_counts.columns = ['age_group', 'count']
        age_groups = age_counts['age_group'].tolist()
        age_values = age_counts['count'].tolist()
    else:
        age_groups = []
        age_values = []

    return html.Div([
        # Metric Cards
        html.Div([
            html.Div([
                html.H4("Total Jobs", style={'color': TEXT_COLOR, 'fontSize': '16px', 'marginBottom': '0'}),
                html.H2(f"{total_jobs}", style={'color': PRIMARY_COLOR, 'fontSize': '24px', 'marginTop': '0'}),
            ], style={**CARD_STYLE, 'height': '80px', 'padding': '8px'}),

            html.Div([
                html.H4("Demo Requests", style={'color': TEXT_COLOR, 'fontSize': '16px', 'marginBottom': '0'}),
                html.H2(f"{demo_requests}", style={'color': INFO_COLOR, 'fontSize': '24px', 'marginTop': '0'}),
            ], style={**CARD_STYLE, 'height': '80px', 'padding': '8px'}),

            html.Div([
                html.H4("Promo Event Requests", style={'color': TEXT_COLOR, 'fontSize': '16px', 'marginBottom': '0'}),
                html.H2(f"{promo_requests}", style={'color': WARNING_COLOR, 'fontSize': '24px', 'marginTop': '0'}),
            ], style={**CARD_STYLE, 'height': '80px', 'padding': '8px'}),

            html.Div([
                html.H4("AI Assistant Requests", style={'color': TEXT_COLOR, 'fontSize': '16px', 'marginBottom': '0'}),
                html.H2(f"{ai_requests}", style={'color': DANGER_COLOR, 'fontSize': '24px', 'marginTop': '0'}),
            ], style={**CARD_STYLE, 'height': '80px', 'padding': '8px'}),
        ], style={
            'display': 'flex',
            'flexWrap': 'nowrap',
            'justifyContent': 'space-between',
            'marginBottom': '12px',
            'marginTop': '0',
        }),

        # Graphs
        html.Div([
            # Job Types Graph
            html.Div([
                dcc.Graph(
                    id='job-types-graph',
                    figure=go.Figure(
                        data=[go.Bar(x=job_types, y=job_values, marker_color=[DANGER_COLOR, PRIMARY_COLOR, WARNING_COLOR, INFO_COLOR])],
                        layout=go.Layout(
                            title='Types of Jobs Requested',
                            paper_bgcolor=CARD_COLOR,
                            plot_bgcolor=CARD_COLOR,
                            font=dict(color=TEXT_COLOR),
                        )
                    ),
                    style={'height': '300px'},
                ),
                html.Button('Export Graph', id='export-job-types', n_clicks=0),
                dcc.Download(id='download-job-types')
            ], style={**CARD_STYLE, 'flex': '1', 'marginRight': '10px', 'marginBottom': '10px'}),

            # Continent Pie Chart
            html.Div([
                dcc.Graph(
                    id='geo-graph',
                    figure=go.Figure(
                        data=[go.Pie(labels=geo_labels, values=geo_values)],
                        layout=go.Layout(
                            title='Geographic Distribution (by Continent)',
                            paper_bgcolor=CARD_COLOR,
                            plot_bgcolor=CARD_COLOR,
                            font=dict(color=TEXT_COLOR),
                        )
                    ),
                    style={'height': '300px'},
                ),
                html.Button('Export Graph', id='export-geo', n_clicks=0),
                dcc.Download(id='download-geo')
            ], style={**CARD_STYLE, 'flex': '1', 'marginRight': '10px', 'marginBottom': '10px'}),

            # Age Group Chart
            html.Div([
                dcc.Graph(
                    id='age-graph',
                    figure=go.Figure(
                        data=[go.Bar(x=age_groups, y=age_values)],
                        layout=go.Layout(
                            title='Age Group Distribution',
                            paper_bgcolor=CARD_COLOR,
                            plot_bgcolor=CARD_COLOR,
                            font=dict(color=TEXT_COLOR),
                        )
                    ),
                    style={'height': '300px'},
                ),
                html.Button('Export Graph', id='export-age', n_clicks=0),
                dcc.Download(id='download-age')
            ], style={**CARD_STYLE, 'flex': '1', 'marginBottom': '10px'}),
        ], style={
            'display': 'flex',
            'justifyContent': 'space-between',
            'marginTop': '0',
        }),
        
        # Hidden download components for full report exports
        dcc.Download(id='download-overview-pdf')
    ], style={
        'padding': '20px',
        'height': '100%',
        'overflowY': 'auto',
        'paddingBottom': '20px',
    })

def create_filters(include_chart_type=False, include_time_granularity=False):
    # Get metrics from actual data
    metrics = df['metric'].dropna().unique().tolist() if not df.empty else []
    age_groups = df['age_group'].dropna().unique().tolist() if not df.empty else []
    job_types = df['job_type'].dropna().unique().tolist() if not df.empty else []
    continents = df['continent'].dropna().unique().tolist() if not df.empty else []
    countries = df['country'].dropna().unique().tolist() if not df.empty else []
    # Common dropdown style
    dropdown_style = {
        'backgroundColor': CARD_COLOR,
        'color': TEXT_COLOR,
        'fontSize': '12px',
        'border': '1px solid #ced4da',
        'height': '32px',
        'minHeight': '32px',
        'zIndex': 9999
    }

    filters = html.Div([
        # Metric filter
        dcc.Dropdown(
            id='metric-filter',
            options=[{'label': m, 'value': m} for m in metrics],
            multi=True,
            placeholder="Metric",
            style={**dropdown_style, 'minWidth': '120px'}
        ),
        
        # Continent filter
        dcc.Dropdown(
            id='continent-filter',
            options=[{'label': cont, 'value': cont} for cont in continents],
            multi=True,
            placeholder="Continent",
            style={**dropdown_style, 'minWidth': '120px'}
        ),
        
        # Country filter
        dcc.Dropdown(
            id='country-filter',
            options=[{'label': c, 'value': c} for c in countries],
            multi=True,
            placeholder="Country",
            style={**dropdown_style, 'minWidth': '120px'}
        ),
        
        # Job Type filter
        dcc.Dropdown(
            id='job-filter',
            options=[{'label': job, 'value': job} for job in job_types],
            multi=True,
            placeholder="Job Type",
            style={**dropdown_style, 'minWidth': '120px'}
        ),
        
        # Compact Date Range filter
        dcc.DatePickerRange(
            id='date-range',
            min_date_allowed=df['date'].min() if not df.empty else pd.Timestamp('today'),
            max_date_allowed=df['date'].max() if not df.empty else pd.Timestamp('today'),
            start_date=df['date'].min() if not df.empty else pd.Timestamp('today'),
            end_date=df['date'].max() if not df.empty else pd.Timestamp('today'),
            display_format='MMM D',
            style={'fontSize': '12px', 'minWidth': '220px'}
        ),
        
        # Chart Type filter (conditionally included)
        dcc.Dropdown(
            id='chart-type',
            options=[
                {'label': 'Line', 'value': 'line'},
                {'label': 'Bar', 'value': 'bar'},
                {'label': 'Area', 'value': 'area'},
                {'label': 'Heatmap', 'value': 'heatmap'}
            ],
            value='line',
            clearable=False,
            style={**dropdown_style, 'minWidth': '100px'}
        ) if include_chart_type else None,
        
        # Time Granularity filter (conditionally included)
        dcc.Dropdown(
            id='time-granularity',
            options=[
                {'label': 'Hour', 'value': 'hour'},
                {'label': 'Day', 'value': 'day'},
                {'label': 'Week', 'value': 'week'},
                {'label': 'Month', 'value': 'month'},
                {'label': 'Quarter', 'value': 'quarter'},
                {'label': 'Year', 'value': 'year'}
            ],
            value='day',
            clearable=False,
            style={**dropdown_style, 'minWidth': '100px'}
        ) if include_time_granularity else None,
        
        # Apply Filters button
        html.Button(
            'Apply Filters',
            id='apply-filters',
            n_clicks=0,
            style={
                'backgroundColor': PRIMARY_COLOR,
                'color': 'white',
                'border': 'none',
                'padding': '6px 12px',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'height': '32px',
                'fontSize': '12px'
            }
        )
    ], style={
        'display': 'flex',
        'flexWrap': 'wrap',
        'gap': '8px',
        'alignItems': 'center',
        'padding': '8px',
        'backgroundColor': CARD_COLOR,
        'borderRadius': '8px',
        'marginBottom': '8px',
        'marginTop': '0px'  # Added to move filters closer to nav
    })

    return filters

def geographic_analysis_layout():
    return html.Div([
        create_filters(include_chart_type=True),

        # Export button above the graphs
        html.Div([
            html.Button('Export Report', id='export-geo-pdf', n_clicks=0, style={
                'backgroundColor': PRIMARY_COLOR,
                'color': 'white',
                'border': 'none',
                'padding': '6px 12px',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'marginBottom': '10px',
                'width': 'auto',
                'fontSize': '12px'
            }),
            dcc.Download(id='download-geo-pdf')
        ], style={'textAlign': 'right'}), 
        
        # Map and chart in one row
        html.Div([
            html.Div([
                dcc.Graph(
                    id='geo-map',
                    config={'displayModeBar': True},
                    style={'height': '300px'}
                )
            ], style={
                'backgroundColor': CARD_COLOR,
                'borderRadius': '8px',
                'padding': '15px',
                'flex': '1',
                'margin': '5px'
            }),
            
            html.Div([
                dcc.Graph(
                    id='geo-chart',
                    config={'displayModeBar': True},
                    style={'height': '300px'}
                )
            ], style={
                'backgroundColor': CARD_COLOR,
                'borderRadius': '8px',
                'padding': '15px',
                'flex': '1',
                'margin': '5px'
            })
        ], style={
            'display': 'flex',
            'flexDirection': 'row',
            'justifyContent': 'space-between',
            'width': '100%',
            'height': '320px'
        })
    ], style={
        'padding': '12px',
        'height': 'calc(100vh - 150px)',
        'overflow': 'hidden'
    })

def time_based_analysis_layout():
    return html.Div([
        create_filters(include_chart_type=True),
       
        # Export button
        html.Div([
            html.Button('Export Report', id='export-time-pdf', n_clicks=0, style={
                'backgroundColor': PRIMARY_COLOR,
                'color': 'white',
                'border': 'none',
                'padding': '6px 12px',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'marginBottom': '10px',
                'width': 'auto',
                'fontSize': '12px',
                'float': 'right'
            }),
            dcc.Download(id='download-time-pdf')
        ], style={'clear': 'both'}),
        
        # Three graphs in one row
        html.Div([
            # Daily trend
            html.Div([
                dcc.Graph(
                    id='daily-trend-graph',
                    config={'displayModeBar': True},
                    style={'height': '300px'}
                )
            ], style={
                'backgroundColor': CARD_COLOR,
                'borderRadius': '8px',
                'padding': '10px',
                'flex': '1',
                'margin': '5px'
            }),
            
            # Weekly trend
            html.Div([
                dcc.Graph(
                    id='weekly-trend-graph',
                    config={'displayModeBar': True},
                    style={'height': '300px'}
                )
            ], style={
                'backgroundColor': CARD_COLOR,
                'borderRadius': '8px',
                'padding': '10px',
                'flex': '1',
                'margin': '5px'
            }),
            
            # Monthly trend
            html.Div([
                dcc.Graph(
                    id='monthly-trend-graph',
                    config={'displayModeBar': True},
                    style={'height': '300px'}
                )
            ], style={
                'backgroundColor': CARD_COLOR,
                'borderRadius': '8px',
                'padding': '10px',
                'flex': '1',
                'margin': '5px'
            })
        ], style={
            'display': 'flex',
            'flexDirection': 'row',
            'justifyContent': 'space-between',
            'width': '100%',
            'height': '270px',
            'marginBottom': '10px'
        })
    ], style={
        'padding': '12px',
        'height': 'calc(100vh - 150px)',
        'overflow': 'hidden'
    })
    
def age_analysis_layout():
    return html.Div([
        create_filters(include_chart_type=True),

        # Export button
        html.Div([
            html.Button('Export Report', id='export-age-pdf', n_clicks=0, style={
                'backgroundColor': PRIMARY_COLOR,
                'color': 'white',
                'border': 'none',
                'padding': '6px 12px',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'marginBottom': '10px',
                'width': 'auto',
                'fontSize': '12px',
                'float': 'right'
            }),
            dcc.Download(id='download-age-pdf')
        ], style={'clear': 'both'}),
        
        # Two graphs in one row
        html.Div([
            # Age Distribution Chart
            html.Div([
                dcc.Graph(
                    id='age-distribution-chart',
                    config={'displayModeBar': True},
                    style={'height': '300px'}
                )
            ], style={
                'backgroundColor': CARD_COLOR,
                'borderRadius': '8px',
                'padding': '15px',
                'flex': '1',
                'margin': '5px',
                'height': '320px'
            }),
            
            # Second Chart (Age vs Metric)
            html.Div([
                dcc.Graph(
                    id='age-metric-chart',
                    config={'displayModeBar': True},
                    style={'height': '300px'}
                )
            ], style={
                'backgroundColor': CARD_COLOR,
                'borderRadius': '8px',
                'padding': '15px',
                'flex': '1',
                'margin': '5px',
                'height': '320px'
            })
        ], style={
            'display': 'flex',
            'flexDirection': 'row',
            'justifyContent': 'space-between',
            'width': '100%',
            'marginBottom': '10px'
        })
    ], style={
        'padding': '12px',
        'height': 'calc(100vh - 150px)',
        'overflow': 'hidden'
    })
    
def server_analytics_layout():
    return html.Div([
        create_filters(),
        
        html.Div(id='server-analytics-heading', style={
            'fontSize': '18px',
            'fontWeight': 'bold',
            'margin': '10px 0',
            'color': TEXT_COLOR
        }),
        
        html.Div([
            html.Button('Export Report', id='export-analytics-pdf', n_clicks=0, style={
                'backgroundColor': PRIMARY_COLOR,
                'color': 'white',
                'border': 'none',
                'padding': '6px 12px',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'marginBottom': '10px',
                'width': 'auto',
                'fontSize': '12px',
                'float': 'right'
            }),
            dcc.Download(id='download-analytics-pdf')
        ], style={'clear': 'both'}),
        
        html.Div([
            html.Div([
                html.H4("Key Metrics", style={
                    'color': PRIMARY_COLOR,
                    'marginBottom': '15px',
                    'textAlign': 'center'
                }),
                dash_table.DataTable(
                    id='server-stats-table',
                    columns=[
                        {'name': 'Metric', 'id': 'metric', 'type': 'text'},
                        {'name': 'Value', 'id': 'value', 'type': 'text'}
                    ],
                    style_table={'overflowX': 'auto'},
                    style_header={
                        'backgroundColor': PRIMARY_COLOR,
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    style_cell={
                        'textAlign': 'center',
                        'padding': '10px',
                        'backgroundColor': CARD_COLOR,
                        'color': TEXT_COLOR
                    }
                )
            ], style={
                'backgroundColor': CARD_COLOR,
                'borderRadius': '8px',
                'padding': '20px',
                'flex': '1',
                'margin': '10px',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
            }),
            
            html.Div([
                html.H4("Value Trend Over Time", style={
                    'color': PRIMARY_COLOR,
                    'marginBottom': '15px',
                    'textAlign': 'center'
                }),
                dcc.Graph(
                    id='server-analytics-graph',
                    config={'displayModeBar': True},
                    style={'height': '100%'}
                )
            ], style={
                'backgroundColor': CARD_COLOR,
                'borderRadius': '8px',
                'padding': '20px',
                'flex': '1',
                'margin': '10px',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
            })
        ], style={
            'display': 'flex',
            'flexDirection': 'row',
            'justifyContent': 'space-between',
            'marginBottom': '20px',
            'height': '400px'
        })
    ], style={
        'padding': '20px',
        'height': '100%',
        'overflowY': 'auto'
    })

# Now define the main layout
dash_app.layout = html.Div([
    html.Div([
        html.H2("Sales Performance Dashboard", style={'color': TEXT_COLOR, 'margin': '0', 'display': 'inline-block'}),
        html.A('Logout', href='/logout', style={
            'float': 'right', 'margin': '10px', 'color': '#fff', 'backgroundColor': DANGER_COLOR,
            'padding': '8px 18px', 'borderRadius': '25px', 'textDecoration': 'none', 'fontWeight': 'bold'
        }),
    ], style={'backgroundColor': PRIMARY_COLOR, 'padding': '12px 18px 8px 18px', 'borderBottom': '2px solid #0b5ed7', 'flex': '0 0 auto'}),
    
    dcc.Tabs(
        id='tabs',
        value='overview',
        children=[
            dcc.Tab(label='📊 Dashboard Overview', value='overview'),
            dcc.Tab(label='🌍 Geographic Analysis', value='geo'),
            dcc.Tab(label='⏱️ Time-Based Analysis', value='time'),
            dcc.Tab(label='👥 Age by Sales', value='age'),
            dcc.Tab(label='🖥️ Server Analytics', value='analytics'),
        ],
        colors={
            "border": "#dee2e6",
            "primary": PRIMARY_COLOR,
            "background": BACKGROUND_COLOR
        },
        parent_className='custom-tabs',
        className='custom-tabs'
    ),

    html.Div(id='tab-content', style={'padding': '12px', 'flex': '1 1 auto', 'overflow': 'hidden', 'height': '100%'})
], style={'backgroundColor': BACKGROUND_COLOR, 'height': '100vh', 'overflow': 'hidden', 'padding': '0', 'fontFamily': 'Segoe UI, Arial, sans-serif', 'display': 'flex', 'flexDirection': 'column'})

# callback for tab content
@dash_app.callback(
    Output('tab-content', 'children'),
    Input('tabs', 'value')
)
def render_tab_content(tab):
    if tab == 'overview':
        return dashboard_overview_layout()
    elif tab == 'geo':
        return geographic_analysis_layout()
    elif tab == 'time':
        return time_based_analysis_layout()
    elif tab == 'age':
        return age_analysis_layout()
    elif tab == 'analytics':
        return server_analytics_layout()
    return html.Div("Select a tab", style={'color': TEXT_COLOR})


# Update these callbacks to match the download component IDs
@dash_app.callback(
    Output('download-geo-pdf', 'data'),
    Input('export-geo-pdf', 'n_clicks'),
    [State('geo-map', 'figure'),
     State('geo-chart', 'figure')],
    prevent_initial_call=True
)
def export_geo_pdf(n_clicks, geo_map_fig, geo_chart_fig):
    if not n_clicks:
        return dash.no_update
    
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Add first figure
        img_bytes = pio.to_image(geo_map_fig, format="png", engine="kaleido")
        img = ImageReader(BytesIO(img_bytes))
        c.drawImage(img, 50, 400, width=500, height=300, preserveAspectRatio=True)
        c.drawString(50, 380, "Geographic Distribution Map")
        
        # Add second figure
        img_bytes = pio.to_image(geo_chart_fig, format="png", engine="kaleido")
        img = ImageReader(BytesIO(img_bytes))
        c.drawImage(img, 50, 50, width=500, height=300, preserveAspectRatio=True)
        c.drawString(50, 30, "Geographic Distribution Chart")
        
        c.showPage()
        c.save()
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return dcc.send_bytes(pdf_data, "geographic_analysis.pdf")
    except Exception as e:
        print(f"PDF export error: {e}")
        return dash.no_update

@dash_app.callback(
    Output('download-time-pdf', 'data'),
    Input('export-time-pdf', 'n_clicks'),
    [State('daily-trend-graph', 'figure'),
     State('weekly-trend-graph', 'figure'),
     State('monthly-trend-graph', 'figure')],
    prevent_initial_call=True
)
def export_time_pdf(n_clicks, daily_fig, weekly_fig, monthly_fig):
    if not n_clicks:
        return dash.no_update
    
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Add daily trend
        img_bytes = pio.to_image(daily_fig, format="png", engine="kaleido")
        img = ImageReader(BytesIO(img_bytes))
        c.drawImage(img, 50, 550, width=500, height=250, preserveAspectRatio=True)
        c.drawString(50, 530, "Daily Trend")
        
        # Add weekly trend
        img_bytes = pio.to_image(weekly_fig, format="png", engine="kaleido")
        img = ImageReader(BytesIO(img_bytes))
        c.drawImage(img, 50, 300, width=500, height=250, preserveAspectRatio=True)
        c.drawString(50, 280, "Weekly Trend")
        
        # Add monthly trend
        img_bytes = pio.to_image(monthly_fig, format="png", engine="kaleido")
        img = ImageReader(BytesIO(img_bytes))
        c.drawImage(img, 50, 50, width=500, height=250, preserveAspectRatio=True)
        c.drawString(50, 30, "Monthly Trend")
        
        c.showPage()
        c.save()
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return dcc.send_bytes(pdf_data, "time_analysis.pdf")
    except Exception as e:
        print(f"Time PDF export error: {e}")
        return dash.no_update

@dash_app.callback(
    Output('download-age-pdf', 'data'),
    Input('export-age-pdf', 'n_clicks'),
    [State('age-distribution-chart', 'figure'),
     State('age-metric-chart', 'figure')],
    prevent_initial_call=True
)
def export_age_pdf(n_clicks, age_dist_fig, age_metric_fig):
    if not n_clicks:
        return dash.no_update
    
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Add age distribution
        img_bytes = pio.to_image(age_dist_fig, format="png", engine="kaleido")
        img = ImageReader(BytesIO(img_bytes))
        c.drawImage(img, 50, 400, width=500, height=300, preserveAspectRatio=True)
        c.drawString(50, 380, "Age Group Distribution")
        
        # Add age vs metric
        img_bytes = pio.to_image(age_metric_fig, format="png", engine="kaleido")
        img = ImageReader(BytesIO(img_bytes))
        c.drawImage(img, 50, 50, width=500, height=300, preserveAspectRatio=True)
        c.drawString(50, 30, "Age vs Metric Analysis")
        
        c.showPage()
        c.save()
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return dcc.send_bytes(pdf_data, "age_analysis.pdf")
    except Exception as e:
        print(f"Age PDF export error: {e}")
        return dash.no_update

@dash_app.callback(
    Output('download-analytics-pdf', 'data'),
    Input('export-analytics-pdf', 'n_clicks'),
    [State('server-stats-table', 'data'),
     State('server-analytics-graph', 'figure')],
    prevent_initial_call=True
)
def export_analytics_pdf(n_clicks, table_data, graph_fig):
    if not n_clicks:
        return dash.no_update
    
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Add graph
        img_bytes = pio.to_image(graph_fig, format="png", engine="kaleido")
        img = ImageReader(BytesIO(img_bytes))
        c.drawImage(img, 50, 400, width=500, height=300, preserveAspectRatio=True)
        c.drawString(50, 380, "Server Analytics Graph")
        
        # Add table
        if table_data:
            data = [['Metric', 'Value']] + [[item['metric'], item['value']] for item in table_data]
            t = Table(data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            t.wrapOn(c, 500, 300)
            t.drawOn(c, 50, 100)
            c.drawString(50, 80, "Server Metrics Table")
        
        c.showPage()
        c.save()
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return dcc.send_bytes(pdf_data, "server_analytics.pdf")
    except Exception as e:
        print(f"Analytics PDF export error: {e}")
        return dash.no_update


# Callback to update country dropdown based on selected continents
@dash_app.callback(
    Output('country-filter', 'options'),
    [Input('continent-filter', 'value')]
)
def update_country_options(selected_continents):
    if not selected_continents:
        return [{'label': c, 'value': c} for c in df['country'].unique()]
    
    filtered_df = df[df['continent'].isin(selected_continents)]
    countries = filtered_df['country'].unique()
    return [{'label': c, 'value': c} for c in countries]

def apply_filters(metrics, continents, countries, ages, job_types, start_date, end_date):
    filtered_df = df.copy()
    
    # Apply date range first
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df['date'] >= pd.to_datetime(start_date)) &
            (filtered_df['date'] <= pd.to_datetime(end_date))
        ]
    
    # Then apply other filters if they exist
    if continents:
        filtered_df = filtered_df[filtered_df['continent'].isin(continents)]
    if countries:
        filtered_df = filtered_df[filtered_df['country'].isin(countries)]
    if job_types:
        filtered_df = filtered_df[filtered_df['job_type'].isin(job_types)]
    if ages:
        filtered_df = filtered_df[filtered_df['age_group'].isin(ages)]
    if metrics:
        filtered_df = filtered_df[filtered_df['metric'].isin(metrics)]
    
    return filtered_df

def resample_data(df, granularity):
    df_time = df.copy()
    if granularity == 'hour':
        df_time['period'] = df_time['date'].dt.floor('H')
    elif granularity == 'day':
        df_time['period'] = df_time['date'].dt.floor('D')
    elif granularity == 'week':
        df_time['period'] = df_time['date'].dt.to_period('W').apply(lambda r: r.start_time)
    elif granularity == 'month':
        df_time['period'] = df_time['date'].dt.to_period('M').apply(lambda r: r.start_time)
    elif granularity == 'quarter':
        df_time['period'] = df_time['date'].dt.to_period('Q').apply(lambda r: r.start_time)
    elif granularity == 'year':
        df_time['period'] = df_time['date'].dt.to_period('Y').apply(lambda r: r.start_time)
    return df_time

def generate_chart_title(filters, base_title):
    title_parts = [base_title]
    
    if filters.get('metrics'):
        title_parts.append(f"Metrics: {', '.join(filters['metrics'])}")
    if filters.get('continents'):
        title_parts.append(f"Continents: {', '.join(filters['continents'])}")
    if filters.get('countries'):
        title_parts.append(f"Countries: {', '.join(filters['countries'])}")
    if filters.get('job_types'):
        title_parts.append(f"Job Types: {', '.join(filters['job_types'])}")
    if filters.get('start_date') and filters.get('end_date'):
        title_parts.append(f"Date Range: {filters['start_date']} to {filters['end_date']}")
    
    return " | ".join(title_parts)

@dash_app.callback(
    [Output('geo-map', 'figure'),
     Output('geo-chart', 'figure')],
    [Input('apply-filters', 'n_clicks'),
     Input('chart-type', 'value')],
    [State('metric-filter', 'value'),
     State('continent-filter', 'value'),
     State('country-filter', 'value'),
     State('job-filter', 'value'),
     State('date-range', 'start_date'),
     State('date-range', 'end_date')]
)
def update_geo_analysis(n_clicks, chart_type, metrics, continents, countries, job_types, start_date, end_date):
    if df.empty:
        return go.Figure(), go.Figure()
    
    # Use only the first selected metric if multiple are selected
    selected_metric = metrics[0] if metrics and len(metrics) > 0 else None
    
    filtered_df = apply_filters([selected_metric] if selected_metric else None, 
                              continents, countries, None, job_types, start_date, end_date)
    
    # Generate title with filters
    filters = {
        'metrics': [selected_metric] if selected_metric else [],
        'continents': continents or [],
        'countries': countries or [],
        'job_types': job_types or [],
        'start_date': pd.to_datetime(start_date).strftime('%Y-%m-%d'),
        'end_date': pd.to_datetime(end_date).strftime('%Y-%m-%d')
    }
    base_title = "Geographic Distribution"
    full_title = generate_chart_title(filters, base_title)
    
    # Map visualization
    geo_data = filtered_df.groupby('country')['value'].sum().reset_index()
    map_fig = px.choropleth(
        geo_data,
        locations='country',
        locationmode='country names',
        color='value',
        hover_name='country',
        color_continuous_scale='Blues',
        title=f"{full_title} - Map"
    )
    map_fig.update_layout(
        paper_bgcolor=CARD_COLOR,
        plot_bgcolor=CARD_COLOR,
        font=dict(color=TEXT_COLOR),
        margin=dict(l=10, r=10, t=60, b=10),
        geo=dict(bgcolor='rgba(0,0,0,0)'),
        showlegend=False  # Remove legend
    )

    # Chart visualization based on selected type - showing only selected metric
    if selected_metric:
        chart_data = filtered_df.groupby('country')['value'].sum().reset_index()
    else:
        chart_data = filtered_df.groupby('country')['value'].sum().reset_index()
    
    if chart_type == 'line':
        chart_fig = px.line(
            chart_data, 
            x='country', 
            y='value',
            title=f"{full_title} - {selected_metric if selected_metric else 'All Metrics'}"
        )
    elif chart_type == 'bar':
        chart_fig = px.bar(
            chart_data, 
            x='country', 
            y='value',
            title=f"{full_title} - {selected_metric if selected_metric else 'All Metrics'}"
        )
    elif chart_type == 'area':
        chart_fig = px.area(
            chart_data, 
            x='country', 
            y='value',
            title=f"{full_title} - {selected_metric if selected_metric else 'All Metrics'}"
        )
    else:  # heatmap
        heatmap_data = filtered_df.pivot_table(index='country', columns='metric', values='value', aggfunc='sum', fill_value=0)
        chart_fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='Blues'
        ))
        chart_fig.update_layout(title=f"{full_title} - Heatmap")
    
    # Remove legend from the chart
    chart_fig.update_layout(
        paper_bgcolor=CARD_COLOR,
        plot_bgcolor=CARD_COLOR,
        font=dict(color=TEXT_COLOR),
        margin=dict(l=10, r=10, t=60, b=10),
        showlegend=False  # This removes the legend
    )
    
    return map_fig, chart_fig

# Callback for Time-Based Analysis
@dash_app.callback(
    [Output('daily-trend-graph', 'figure'),
     Output('weekly-trend-graph', 'figure'),
     Output('monthly-trend-graph', 'figure')],
    [Input('apply-filters', 'n_clicks'),
     Input('chart-type', 'value')],
    [State('metric-filter', 'value'),
     State('continent-filter', 'value'),
     State('country-filter', 'value'),
     State('job-filter', 'value'),
     State('date-range', 'start_date'),
     State('date-range', 'end_date')]
)
def update_time_analysis(n_clicks, chart_type, metrics, continents, countries, job_types, start_date, end_date):
    if df.empty:
        return go.Figure(), go.Figure(), go.Figure()
    
    # Use only the first selected metric if multiple are selected
    selected_metric = metrics[0] if metrics and len(metrics) > 0 else None
    
    filtered_df = apply_filters([selected_metric] if selected_metric else None, 
                             continents, countries, None, job_types, start_date, end_date)
    
    # Generate title with filters
    filters = {
        'metrics': [selected_metric] if selected_metric else [],
        'continents': continents or [],
        'countries': countries or [],
        'job_types': job_types or [],
        'start_date': pd.to_datetime(start_date).strftime('%Y-%m-%d'),
        'end_date': pd.to_datetime(end_date).strftime('%Y-%m-%d')
    }
    base_title = "Time Trend"
    full_title = generate_chart_title(filters, base_title)
    
    # Create figures for each granularity
    figures = []
    for granularity in ['day', 'week', 'month']:
        df_time = resample_data(filtered_df, granularity)
        time_data = df_time.groupby('period')['value'].sum().reset_index()
        
        if chart_type == 'line':
            fig = px.line(
                time_data,
                x='period',
                y='value',
                title=f"{full_title} - {granularity.capitalize()}ly"
            )
        elif chart_type == 'bar':
            fig = px.bar(
                time_data,
                x='period',
                y='value',
                title=f"{full_title} - {granularity.capitalize()}ly"
            )
        elif chart_type == 'area':
            fig = px.area(
                time_data,
                x='period',
                y='value',
                title=f"{full_title} - {granularity.capitalize()}ly"
            )
        
        fig.update_layout(
            paper_bgcolor=CARD_COLOR,
            plot_bgcolor=CARD_COLOR,
            font=dict(color=TEXT_COLOR),
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=False
        )
        figures.append(fig)
    
    return figures[0], figures[1], figures[2]

# Callback for Age Analysis
@dash_app.callback(
    [Output('age-distribution-chart', 'figure'),
     Output('age-metric-chart', 'figure')],
    [Input('apply-filters', 'n_clicks'),
     Input('chart-type', 'value')],
    [State('metric-filter', 'value'),
     State('continent-filter', 'value'),
     State('country-filter', 'value'),
     State('job-filter', 'value'),
     State('date-range', 'start_date'),
     State('date-range', 'end_date')]
)
def update_age_analysis(n_clicks, chart_type, metrics, continents, countries, job_types, start_date, end_date):
    if df.empty:
        return go.Figure(), go.Figure()
    
    # Use only the first selected metric if multiple are selected
    selected_metric = metrics[0] if metrics and len(metrics) > 0 else None
    
    filtered_df = apply_filters([selected_metric] if selected_metric else None, 
                              continents, countries, None, job_types, start_date, end_date)
    
    # Generate title with filters
    filters = {
        'metrics': [selected_metric] if selected_metric else [],
        'continents': continents or [],
        'countries': countries or [],
        'job_types': job_types or [],
        'start_date': pd.to_datetime(start_date).strftime('%Y-%m-%d'),
        'end_date': pd.to_datetime(end_date).strftime('%Y-%m-%d')
    }
    base_title = "Age Analysis"
    full_title = generate_chart_title(filters, base_title)
    
    # Chart 1: Age Distribution
    age_counts = filtered_df['age_group'].value_counts().reset_index()
    age_counts.columns = ['age_group', 'count']
    
    if chart_type == 'line':
        age_fig = px.line(
            age_counts,
            x='age_group',
            y='count',
            title=f"{full_title} - Distribution"
        )
    elif chart_type == 'bar':
        age_fig = px.bar(
            age_counts,
            x='age_group',
            y='count',
            title=f"{full_title} - Distribution"
        )
    elif chart_type == 'area':
        age_fig = px.area(
            age_counts,
            x='age_group',
            y='count',
            title=f"{full_title} - Distribution"
        )
    
    age_fig.update_layout(
        paper_bgcolor=CARD_COLOR,
        plot_bgcolor=CARD_COLOR,
        font=dict(color=TEXT_COLOR),
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False
    )
    
    # Chart 2: Age vs Metric
    if selected_metric:
        age_metric_data = filtered_df.groupby('age_group')['value'].mean().reset_index()
        if chart_type == 'line':
            metric_fig = px.line(
                age_metric_data,
                x='age_group',
                y='value',
                title=f"{full_title} - {selected_metric} by Age"
            )
        elif chart_type == 'bar':
            metric_fig = px.bar(
                age_metric_data,
                x='age_group',
                y='value',
                title=f"{full_title} - {selected_metric} by Age"
            )
        elif chart_type == 'area':
            metric_fig = px.area(
                age_metric_data,
                x='age_group',
                y='value',
                title=f"{full_title} - {selected_metric} by Age"
            )
    else:
        metric_fig = go.Figure()
        metric_fig.update_layout(
            title="Select a metric to view data",
            paper_bgcolor=CARD_COLOR,
            plot_bgcolor=CARD_COLOR
        )
    
    metric_fig.update_layout(
        paper_bgcolor=CARD_COLOR,
        plot_bgcolor=CARD_COLOR,
        font=dict(color=TEXT_COLOR),
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False
    )
    
    return age_fig, metric_fig

# Callbacks for Server Analytics tab
@dash_app.callback(
    [Output('server-stats-table', 'data'),
     Output('server-analytics-heading', 'children'),
     Output('server-analytics-graph', 'figure')],
    [Input('apply-filters', 'n_clicks')],
    [State('metric-filter', 'value'),
     State('continent-filter', 'value'),
     State('country-filter', 'value'),
     State('job-filter', 'value'),
     State('date-range', 'start_date'),
     State('date-range', 'end_date')]
)
def update_server_analytics(n_clicks, metrics, continents, countries, job_types, start_date, end_date):
    if df.empty:
        return [], "No data available", go.Figure()
    
    filtered_df = apply_filters(metrics, continents, countries, None, job_types, start_date, end_date)
    
    # Calculate metrics based on available columns
    total_requests = len(filtered_df)
    
    # If you have a column that indicates success/failure, use that instead of http_status
    # For now, we'll just show total requests and value metrics
    avg_value = filtered_df['value'].mean() if 'value' in filtered_df.columns else 0
    max_value = filtered_df['value'].max() if 'value' in filtered_df.columns else 0
    min_value = filtered_df['value'].min() if 'value' in filtered_df.columns else 0
    
    # Create table data
    table_data = [
        {'metric': 'Total Requests', 'value': f"{total_requests:,}"},
        {'metric': 'Average Value', 'value': f"{avg_value:.2f}"},
        {'metric': 'Maximum Value', 'value': f"{max_value:.2f}"},
        {'metric': 'Minimum Value', 'value': f"{min_value:.2f}"}
    ]
    
    # Create heading text
    heading = "Server Analytics"
    if metrics:
        heading += f" | Metrics: {', '.join(metrics)}"
    if continents:
        heading += f" | Continents: {', '.join(continents)}"
    if countries:
        heading += f" | Countries: {', '.join(countries)}"
    
    # Create graph using available data
    if not filtered_df.empty and 'date' in filtered_df.columns and 'value' in filtered_df.columns:
        df_time = filtered_df.copy()
        df_time['date_day'] = df_time['date'].dt.floor('D')
        time_series = df_time.groupby('date_day')['value'].mean().reset_index()
        
        fig = px.line(
            time_series,
            x='date_day',
            y='value',
            title=f"{heading} - Value Trend"
        )
        
        fig.update_layout(
            paper_bgcolor=CARD_COLOR,
            plot_bgcolor=CARD_COLOR,
            font=dict(color=TEXT_COLOR),
            margin=dict(l=20, r=20, t=60, b=20),
            showlegend=False
        )
    else:
        fig = go.Figure()
        fig.update_layout(
            title="No value data available for selected filters",
            paper_bgcolor=CARD_COLOR,
            plot_bgcolor=CARD_COLOR
        )
    
    return table_data, heading, fig

@dash_app.callback(
    [Output('download-job-types', 'data'),
     Output('download-geo', 'data'),
     Output('download-age', 'data')],
    [Input('export-job-types', 'n_clicks'),
     Input('export-geo', 'n_clicks'),
     Input('export-age', 'n_clicks')],
    [State('job-types-graph', 'figure'),
     State('geo-graph', 'figure'),
     State('age-graph', 'figure')],
    prevent_initial_call=True
)
def export_overview_graphs(job_clicks, geo_clicks, age_clicks, job_fig, geo_fig, age_fig):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        if button_id == 'export-job-types' and job_clicks:
            img_bytes = pio.to_image(job_fig, format="png")
            return dcc.send_bytes(img_bytes, "job_types.png"), dash.no_update, dash.no_update
        elif button_id == 'export-geo' and geo_clicks:
            img_bytes = pio.to_image(geo_fig, format="png")
            return dash.no_update, dcc.send_bytes(img_bytes, "geo_distribution.png"), dash.no_update
        elif button_id == 'export-age' and age_clicks:
            img_bytes = pio.to_image(age_fig, format="png")
            return dash.no_update, dash.no_update, dcc.send_bytes(img_bytes, "age_distribution.png")
    except Exception as e:
        print(f"Export error: {e}")
        return dash.no_update
    
    return dash.no_update


server=app

if __name__ == '__main__':
    app.run(debug=True)