from app import create_app
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()

logger.debug('Registered routes:')
for rule in app.url_map.iter_rules():
    logger.debug(f'Route: {rule.rule}, Endpoint: {rule.endpoint}')

if __name__ == '__main__':
    # Initialize principal account before running app
    with app.app_context():
        try:
            from database.index import init_db
            init_db()
            logger.info("Database initialization completed")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            
    app.run(debug=True)
