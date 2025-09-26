# For platforms that support multiple process types
web: cd fundlink_web && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:$PORT --workers 3 fundlink_backend.wsgi:application
bot: cd telbot_llm && python run_bot.py
verifier: cd donation_verifier && python main.py

# For single process platforms (use release for migrations)
release: cd fundlink_web && python manage.py migrate && python manage.py collectstatic --noinput