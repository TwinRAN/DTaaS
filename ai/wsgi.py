from app import create_app

# WSGI entrypoint for waitress/gunicorn
app = create_app()
