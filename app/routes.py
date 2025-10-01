from app import app, db

@app.route('/healthz')
def healthz():
    """Health check endpoint"""
    try:
        db.session.execute('SELECT 1')
        return {'status': 'healthy', 'database': 'connected'}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500

@app.route('/')
def index():
    return "Quiz Application is running!"
