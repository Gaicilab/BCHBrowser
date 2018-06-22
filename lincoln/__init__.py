import os
import sys
import yaml
import logging
import inspect

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.local import LocalProxy
from bitcoin.rpc import Proxy
from redis import Redis

import lincoln.filters as filters

root = os.path.abspath(os.path.dirname(__file__) + '/../')
db = SQLAlchemy()

coinserv = LocalProxy(
    lambda: getattr(current_app, 'rpc_connection', None))
redis_conn = LocalProxy(
    lambda: getattr(current_app, 'redis', None))


def create_app(log_level="INFO", config="config.yml"):
    app = Flask(__name__)
    app.secret_key = 'test'
    app.config.from_object(__name__)

    config_vars = yaml.load(open(root + '/config.yml'))
    # inject all the yaml configs
    app.config.update(config_vars)
    db.init_app(app)
    Migrate(app, db)

    # Setup redis
    redis_config = app.config.get('redis_conn', dict(type='live'))
    typ = redis_config.pop('type')
    if typ == "mock_redis":
        from mockredis import mock_redis_client
        app.redis = mock_redis_client()
    else:
        app.redis = Redis(**redis_config)

    del app.logger.handlers[0]
    app.logger.setLevel(logging.NOTSET)
    log_format = logging.Formatter('%(asctime)s [%(name)s] [%(levelname)s]: %(message)s')
    log_level = getattr(logging, str(log_level), app.config.get('log_level', "INFO"))

    logger = logging.getLogger()
    logger.setLevel(log_level)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(log_format)
    logger.addHandler(handler)

    # Dynamically add all the filters in the filters.py file
    for name, func in inspect.getmembers(filters, inspect.isfunction):
        app.jinja_env.filters[name] = func

    app.rpc_connection = Proxy(
        "http://{0}:{1}@{2}:{3}/"
        .format(app.config['coinserv']['username'],
                app.config['coinserv']['password'],
                app.config['coinserv']['address'],
                app.config['coinserv']['port'])
        )

    from . import views
    app.register_blueprint(views.main)
    return app
