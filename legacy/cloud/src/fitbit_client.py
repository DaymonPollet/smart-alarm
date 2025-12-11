import logging
import fitbit
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class FitbitClient:
    def __init__(self, client_id, client_secret, access_token, refresh_token):
        logger.info("Initializing Fitbit client...")
        self.client = fitbit.Fitbit(
            client_id,
            client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
            system=fitbit.Fitbit.METRIC 
        )

    def fetch_sleep_data(self, date: Optional[str] = None) -> Dict:
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching sleep data for date: {date}")
        try:
            return self.client.sleep(date=date)
        except Exception as e:
            logger.error(f"Error fetching sleep data: {e}")
            raise

    def fetch_heart_rate_intraday(self, date: Optional[str] = None, detail_level: str = '1min') -> Dict:
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching heart rate intraday data for {date}")
        try:
            return self.client.intraday_time_series(
                'activities/heart',
                base_date=date,
                detail_level=detail_level
            )
        except Exception as e:
            logger.error(f"Error fetching heart rate data: {e}")
            raise

    def fetch_hrv_data(self, date: Optional[str] = None) -> Dict:
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching HRV data for date: {date}")
        try:
            return self.client.time_series(
                'hrv',
                base_date=date,
                end_date=date
            )
        except Exception as e:
            logger.error(f"Error fetching HRV data: {e}")
            raise
