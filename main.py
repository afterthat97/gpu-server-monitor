import os
import flask
import logging
import config as cfg
from markdown2 import markdown
from apscheduler.schedulers.background import BackgroundScheduler
from query import query


body = 'Loading...'
app = flask.Flask(__name__)
app.logger.setLevel(logging.INFO)
app.logger.handlers[0].setFormatter(logging.Formatter(
    '[%(asctime)s][%(levelname)s] - %(message)s'
))


@app.route('/')
def index():
    with open('templates/index.html', 'r') as f:
        page = f.read()
        page = page.replace('placeholder', body)
        return page


@app.route('/css/style.css')
def css1():
    return flask.send_from_directory('templates', 'css/style.css')


@app.route('/css/bootstrap.min.css')
def css2():
    return flask.send_from_directory('templates', 'css/bootstrap.min.css')


def refresh():
    global body
    body = markdown(query(cfg.GPU_SERVER_LIST, app.logger), extras=["tables"])


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    sched = BackgroundScheduler(daemon=True)
    sched.add_job(refresh, trigger='interval', seconds=cfg.REFRESH_INTERVAL)
    sched.start()

    app.run(host=cfg.LISTEN_HOST, port=cfg.LISTEN_PORT, threaded=False)
