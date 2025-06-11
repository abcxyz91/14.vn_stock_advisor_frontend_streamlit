import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from vnstock import Vnstock
import requests
import os, time, json
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
# Make sure you have a .env file in the same directory with CREW_URL and BEARER_TOKEN
load_dotenv()

# Configuration for the crewAI API
CREW_URL = os.environ.get("CREW_URL")
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")

# Check if API credentials are loaded
if not CREW_URL or not BEARER_TOKEN:
    st.error("Lỗi cấu hình: Vui lòng đặt CREW_URL và BEARER_TOKEN trong file .env")
    st.stop() # Stop execution if config is missing

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json"
}

@st.cache_data(ttl=3600) # Cache for 1 hours
def get_response(user_input):
    """Get response from crewAI API"""
    # Start crew execution
    payload = {
        "inputs": {
            "symbol": user_input,
            "current_date": str(date.today())
        }
    }

    try:
        response = requests.post(f"{CREW_URL}/kickoff", headers=HEADERS, json=payload)
        kickoff_id = response.json()["kickoff_id"]
        print(f"Execution started with ID: {kickoff_id}")

        # Poll for results
        MAX_RETRIES = 20
        POLL_INTERVAL = 10  # seconds
        for i in range(MAX_RETRIES):
            time.sleep(3)
            print(f"Checking status (attempt {i+1}/{MAX_RETRIES})...")
            response = requests.get(f"{CREW_URL}/status/{kickoff_id}", headers=HEADERS)

            print(f"Response status code: {response.status_code}")
            print(f"Raw response text: {response.text[:50]}...")  # Print first 50 chars
            
            if response.status_code == 200 and response.text:
                try:
                    # Parse the main response
                    response_data = response.json()
                    print(f"State: {response_data.get('state')}")
                    print(f"Status: {response_data.get('status')}")

                    # Check if execution is complete
                    if response_data.get("state") == "SUCCESS":
                        # Return from crewAI API already in dict format
                        result = response_data.get("result_json", '{}')
                        if not result:
                            return {"status": "error", "error": "Lỗi phân tích dữ liệu từ server. Xin hãy thử lại sau ít phút."}
                        
                        print("Result data received:")
                        print(result)
                        return result
                    
                    elif response_data.get("state") == "ERROR":
                        print("❌ Task failed on server side")
                        return {"status": "error", "error": "Lỗi phân tích dữ liệu từ server. Xin hãy thử lại sau ít phút."}
                    
                    else:
                        print("⏳ Still processing...")

                except json.JSONDecodeError as e:
                    print(f"Error parsing response: {e}")

            print(f"Status: processing, waiting {POLL_INTERVAL} seconds...")
            time.sleep(POLL_INTERVAL)
        # If we get here, we've either hit an error or timed out
        return {"status": "error", "error": "Yêu cầu đến API bị hết thời gian chờ. Vui lòng thử lại sau."}

    except requests.exceptions.Timeout:
        return {"status": "error", "error": "Yêu cầu đến API bị hết thời gian chờ. Vui lòng thử lại sau."}
    except requests.exceptions.HTTPError as http_err:
        return {"status": "error", "error": f"Lỗi HTTP từ API: {http_err}"}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "error": f"Lỗi kết nối API: {req_err}"}
    except Exception as e:
        # Catch any other unexpected errors
        return {"status": "error", "error": f"Đã xảy ra lỗi không mong muốn: {str(e)}"}


def is_valid_vn_ticker(ticker):
    """
    Validates if the input is in correct Vietnamese stock ticker format.
    - Must not be empty.
    - Must be 3 or 4 characters long.
    - Must be alphanumeric.
    """
    if not ticker:
        return False
    if len(ticker) not in [3, 4]:
        return False
    if not ticker.isalnum(): # Ensures it consists of letters and numbers only
        return False
    return True

def get_stock_dataframe(ticker):
    """
    Fetches stock data for the given ticker symbol from Vnstock.
    Returns a DataFrame with historical prices or None if there's an error.
    """
    try:
        stock = Vnstock().stock(symbol=ticker, source='VCI')
        end_date = datetime.now()
        start_date = end_date - timedelta(days=200)
        
        # Fix the parameter name from 'inverval' to 'interval'
        df = stock.quote.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval="1D",
            to_df=True
        )
        
        # Verify we got valid data
        if df is None or df.empty:
            return None
            
        return df
        
    except Exception as e:
        print(f"Error fetching stock data: {str(e)}")
        return None

def show_candlestick_chart(df, ticker):
    """
    Displays a candlestick chart for the given DataFrame and ticker.
    """
    fig = go.Figure(data=[go.Candlestick(x=df['time'],
                                          open=df['open']*1000,
                                          high=df['high']*1000,
                                          low=df['low']*1000,
                                          close=df['close']*1000)])
    fig.update_layout(title=f"Biểu đồ giá {ticker}",
                      xaxis_title="Date",
                      yaxis_title="Price (VND)",
                      xaxis_rangeslider_visible=False)
    return fig