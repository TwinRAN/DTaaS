from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    # Dev server with reload
    app.run(host=Config.HOST, port=Config.PORT, debug=True)
