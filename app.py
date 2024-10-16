import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import io
import requests

# Function to fetch stock indicators
def fetch_indicators(stock):
    ticker = yf.Ticker(stock)
    data = ticker.history(period="1y")

    if data.empty:
        return {
            'RSI': None,
            'MACD': None,
            'MACD_Signal': None,
            'MACD_Hist': None,
            'Upper_BB': None,
            'Lower_BB': None,
            'Volatility': None,
            'Beta': None,
            'Close': None,
            'Market_Cap': None,
            'Volume': None
        }

    # Calculate indicators
    data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()
    macd = ta.trend.MACD(data['Close'])
    data['MACD'] = macd.macd()
    data['MACD_Signal'] = macd.macd_signal()
    data['MACD_Hist'] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(data['Close'], window=20, window_dev=2)
    data['Upper_BB'] = bb.bollinger_hband()
    data['Lower_BB'] = bb.bollinger_lband()
    data['Volatility'] = data['Close'].pct_change().rolling(window=21).std() * 100
    beta = ticker.info.get('beta', None)
    market_cap = ticker.info.get('marketCap', None)
    volume = ticker.info.get('volume', None)

    try:
        return {
            'RSI': data['RSI'].iloc[-1],
            'MACD': data['MACD'].iloc[-1],
            'MACD_Signal': data['MACD_Signal'].iloc[-1],
            'MACD_Hist': data['MACD_Hist'].iloc[-1],
            'Upper_BB': data['Upper_BB'].iloc[-1],
            'Lower_BB': data['Lower_BB'].iloc[-1],
            'Volatility': data['Volatility'].iloc[-1],
            'Beta': beta,
            'Close': data['Close'].iloc[-1],
            'Market_Cap': market_cap,
            'Volume': volume
        }
    except IndexError:
        return {
            'RSI': None,
            'MACD': None,
            'MACD_Signal': None,
            'MACD_Hist': None,
            'Upper_BB': None,
            'Lower_BB': None,
            'Volatility': None,
            'Beta': None,
            'Close': None,
            'Market_Cap': None,
            'Volume': None
        }

# Function to fetch news from Upstox
def fetch_news_upstox():
    url = "https://service.upstox.com/content/open/v5/news/sub-category/news/list//market-news/stocks?page=1&pageSize=500"
    response = requests.get(url)
    if response.status_code == 200:
        news_data = response.json()
        if news_data.get("success"):
            return [
                {
                    "headline": article["headline"],
                    "date": article["publishedAt"],
                    "url": article["contentUrl"]
                }
                for article in news_data["data"]
            ]
    return []

# Function to fetch news from Groww
def fetch_news_groww():
    url = "https://groww.in/v1/api/groww_news/v1/stocks_news/news?page=1&size=600"
    response = requests.get(url)
    if response.status_code == 200:
        news_data = response.json()
        return [
            {
                "headline": article["title"],
                "date": article["pubDate"],
                "url": article["url"]
            }
            for article in news_data["results"]
        ]
    return []

# Function to fetch all news
def fetch_news():
    news_upstox = fetch_news_upstox()
    news_groww = fetch_news_groww()
    return news_upstox + news_groww

# Function to score stocks based on indicators for different terms
def score_stock(indicators, term):
    score = 0

    if term == 'Short Term':
        if indicators['RSI'] is not None:
            if indicators['RSI'] < 30 or indicators['RSI'] > 70:
                score += 2  # Good
            if 30 <= indicators['RSI'] <= 40 or 60 <= indicators['RSI'] <= 70:
                score += 1  # Neutral

        if indicators['MACD'] is not None:
            if indicators['MACD'] > 0 and indicators['MACD'] > indicators['MACD_Signal']:
                score += 2  # Good

    elif term == 'Medium Term':
        if indicators['RSI'] is not None:
            if 40 <= indicators['RSI'] <= 60:
                score += 2  # Good

        if indicators['MACD'] is not None:
            if abs(indicators['MACD']) < 0.01:  # Close to zero
                score += 1  # Neutral

    elif term == 'Long Term':
        if indicators['RSI'] is not None:
            if 40 <= indicators['RSI'] <= 60:
                score += 2  # Good

        if indicators['Beta'] is not None:
            if 0.9 <= indicators['Beta'] <= 1.1:
                score += 2  # Good

    return score

# Function to generate recommendations based on different strategies
def generate_recommendations(indicators_list):
    recommendations = {
        'Short Term': [],
        'Medium Term': [],
        'Long Term': []
    }
    
    for stock, indicators in indicators_list.items():
        current_price = indicators['Close']
        
        if current_price is not None:
            lower_buy_range = current_price * 0.995  # 0.5% lower
            upper_buy_range = current_price * 1.005  # 0.5% higher
            short_stop_loss = current_price * (1 - 0.03)  # Max 3%
            short_target = current_price * (1 + 0.05)  # Min 5%
            medium_stop_loss = current_price * (1 - 0.04)  # Max 4%
            medium_target = current_price * (1 + 0.10)  # Min 10%
            long_stop_loss = current_price * (1 - 0.05)  # Max 5%
            long_target = current_price * (1 + 0.15)  # Min 15%

            short_score = score_stock(indicators, 'Short Term')
            medium_score = score_stock(indicators, 'Medium Term')
            long_score = score_stock(indicators, 'Long Term')

            if short_score > 0:
                recommendations['Short Term'].append({
                    'Stock': stock.replace('.NS', ''),  # Remove .NS
                    'Current Price': current_price,
                    'Lower Buy Range': lower_buy_range,
                    'Upper Buy Range': upper_buy_range,
                    'Stop Loss': short_stop_loss,
                    'Target Price': short_target,
                    'Score': short_score,
                    'RSI': indicators['RSI'],
                    'MACD': indicators['MACD'],
                    'MACD_Signal': indicators['MACD_Signal'],
                    'Upper_BB': indicators['Upper_BB'],
                    'Lower_BB': indicators['Lower_BB'],
                    'Volatility': indicators['Volatility'],
                    'Beta': indicators['Beta']
                })

            if medium_score > 0:
                recommendations['Medium Term'].append({
                    'Stock': stock.replace('.NS', ''),  # Remove .NS
                    'Current Price': current_price,
                    'Lower Buy Range': lower_buy_range,
                    'Upper Buy Range': upper_buy_range,
                    'Stop Loss': medium_stop_loss,
                    'Target Price': medium_target,
                    'Score': medium_score,
                    'RSI': indicators['RSI'],
                    'MACD': indicators['MACD'],
                    'MACD_Signal': indicators['MACD_Signal'],
                    'Upper_BB': indicators['Upper_BB'],
                    'Lower_BB': indicators['Lower_BB'],
                    'Volatility': indicators['Volatility'],
                    'Beta': indicators['Beta']
                })

            if long_score > 0:
                recommendations['Long Term'].append({
                    'Stock': stock.replace('.NS', ''),  # Remove .NS
                    'Current Price': current_price,
                    'Lower Buy Range': lower_buy_range,
                    'Upper Buy Range': upper_buy_range,
                    'Stop Loss': long_stop_loss,
                    'Target Price': long_target,
                    'Score': long_score,
                    'RSI': indicators['RSI'],
                    'MACD': indicators['MACD'],
                    'MACD_Signal': indicators['MACD_Signal'],
                    'Upper_BB': indicators['Upper_BB'],
                    'Lower_BB': indicators['Lower_BB'],
                    'Volatility': indicators['Volatility'],
                    'Beta': indicators['Beta']
                })

    return recommendations

# Function to check user credentials
def check_credentials(email, password):
    users_df = pd.read_excel('user.xlsx')
    for _, row in users_df.iterrows():
        if row['email'] == email and row['password'] == password:
            return True
    return False

# Streamlit app
st.image("png_2.3-removebg.png", width=400)
st.title("PredictRAM - Stock Analysis and Call Generator")

# User authentication
email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if check_credentials(email, password):
        st.success("Logged in successfully!")

        # Filter options after successful login
        st.subheader("Select Filters")

        # Read stock symbols from stocks.xlsx
        stocks_df = pd.read_excel('stocks.xlsx')
        stocks = stocks_df['stocks'].tolist()

        # Filters
        market_cap_range = st.slider("Market Cap (in billions)", 0, 2000, (0, 2000), step=100)
        beta_range = st.slider("Beta", 0.0, 3.0, (0.0, 3.0), step=0.1)
        volatility_range = st.slider("Volatility (%)", 0.0, 10.0, (0.0, 10.0), step=0.5)
        volume_range = st.slider("Volume", 0, 10000000, (0, 10000000), step=1000000)

        if st.button("Fetch Stock Details"):
            st.info("Fetching data...")  # Inform user that data fetching is in progress
            try:
                # Fetch indicators for each stock
                indicators_list = {stock: fetch_indicators(stock) for stock in stocks}
                st.success("Data fetched successfully!")

                # Convert to DataFrame for easier manipulation
                indicators_df = pd.DataFrame(indicators_list).T

                # Apply filters
                filtered_df = indicators_df[
                    (indicators_df['Market_Cap'] >= market_cap_range[0] * 1e9) & 
                    (indicators_df['Market_Cap'] <= market_cap_range[1] * 1e9) &
                    (indicators_df['Beta'] >= beta_range[0]) & 
                    (indicators_df['Beta'] <= beta_range[1]) &
                    (indicators_df['Volatility'] >= volatility_range[0]) & 
                    (indicators_df['Volatility'] <= volatility_range[1]) &
                    (indicators_df['Volume'] >= volume_range[0]) & 
                    (indicators_df['Volume'] <= volume_range[1])
                ]

                # Generate recommendations based on filtered stocks
                recommendations = generate_recommendations(filtered_df.to_dict(orient='index'))

                # Display top 20 recommendations for each term
                st.subheader("Top 20 Short Term Trades")
                short_term_df = pd.DataFrame(recommendations['Short Term']).sort_values(by='Score', ascending=False).head(20)
                st.table(short_term_df)

                st.subheader("Top 20 Medium Term Trades")
                medium_term_df = pd.DataFrame(recommendations['Medium Term']).sort_values(by='Score', ascending=False).head(20)
                st.table(medium_term_df)

                st.subheader("Top 20 Long Term Trades")
                long_term_df = pd.DataFrame(recommendations['Long Term']).sort_values(by='Score', ascending=False).head(20)
                st.table(long_term_df)

                # Fetch and display news
                st.subheader("Latest Stock News")
                news = fetch_news()
                if news:
                    for article in news:
                        st.write(f"**{article['headline']}** - {article['date']} [Read more]({article['url']})")
                else:
                    st.write("No news available.")

                # Export to Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    short_term_df.to_excel(writer, sheet_name='Short Term', index=False)
                    medium_term_df.to_excel(writer, sheet_name='Medium Term', index=False)
                    long_term_df.to_excel(writer, sheet_name='Long Term', index=False)
                output.seek(0)

                st.download_button(
                    label="Download Recommendations",
                    data=output,
                    file_name="stock_recommendations.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.error("Invalid email or password.")
