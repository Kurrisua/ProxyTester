from api.app_factory import create_app
from utils import configure_logging

configure_logging()
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
