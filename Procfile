worker: python traditional_poker_service.py
worker: python texasholdem_poker_service.py
web: gunicorn -k flask_sockets.worker -b 127.0.0.1:5000 client_web:app
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -b 127.0.0.1:5000 /home/pypoker/client_web:app
