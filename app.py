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

# ... [rest of the functions remain unchanged] ...

# Streamlit app
st.image("png_2.3-removebg.png", width=400)
st.title("PredictRAM - Stock Analysis and Call Generator")

# User authentication
email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if check_credentials(email, password):
        st.success("Logged in successfully!")

        # Fetch data automatically after successful login
        st.info("Fetching data...")
        try:
            # Read stock symbols from stocks.xlsx
            stocks_df = pd.read_excel('stocks.xlsx')
            stocks = stocks_df['stocks'].tolist()

            # Fetch indicators for each stock
            indicators_list = {stock: fetch_indicators(stock) for stock in stocks}
            st.success("Data fetched successfully!")

            # Convert to DataFrame for easier manipulation
            indicators_df = pd.DataFrame(indicators_list).T

            # Filters
            st.subheader("Filter Stocks")
            market_cap_range = st.slider("Market Cap (in billions)", 0, 2000, (0, 2000), step=100)  # Example range
            beta_range = st.slider("Beta", 0.0, 3.0, (0.0, 3.0), step=0.1)
            volatility_range = st.slider("Volatility (%)", 0.0, 10.0, (0.0, 10.0), step=0.5)
            volume_range = st.slider("Volume", 0, 10000000, (0, 10000000), step=1000000)

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

            # Generate recommendations
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
