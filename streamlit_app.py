import streamlit as st
from helpers import get_response, is_valid_vn_ticker, get_stock_dataframe, show_candlestick_chart

# --- Streamlit UI ---
st.set_page_config(page_title="VN Stock Advisor", layout="centered", initial_sidebar_state="auto")

st.title("📈 VN Stock Advisor", anchor=False)
st.subheader("🤖 Phân tích cổ phiếu Việt bằng AI Agent", anchor=False)

# Initialize session state variables if they don't exist
if 'ticker' not in st.session_state:
    st.session_state.ticker = ""
if 'result' not in st.session_state:
    st.session_state.result = None
if 'error' not in st.session_state:
    st.session_state.error = None
if 'analyzing' not in st.session_state: # To manage the spinner and button state
    st.session_state.analyzing = False

# Input form for the stock ticker
with st.form(key="stock_form"):
    ticker_input = st.text_input(
        label="Nhập mã cổ phiếu:",
        value=st.session_state.ticker,
        placeholder="Ví dụ: FPT, HPG, VCB...",
        help="Nhập 3 hoặc 4 ký tự của mã cổ phiếu (VD: FPT)."
    ).strip().upper() # Sanitize and convert to uppercase
    
    submit_button = st.form_submit_button(
        label="🔍 Phân tích ngay", 
        use_container_width=True,
        disabled=st.session_state.analyzing # Disable button while analyzing
    )

# This block runs if submit_botton is pressed, update session state then rerun to show spinner
if submit_button:
    st.session_state.ticker = ticker_input
    st.session_state.result = None # Reset previous result
    st.session_state.error = None   # Reset previous error
    st.session_state.analyzing = False  # Reset analyzing state
    
    if not st.session_state.ticker:
        st.session_state.error = "⚠️ Vui lòng nhập mã cổ phiếu."
        st.session_state.analyzing = False
    elif not is_valid_vn_ticker(st.session_state.ticker):
        st.session_state.error = "⚠️ Mã cổ phiếu không hợp lệ. Vui lòng nhập mã 3-4 kí tự (VD: FPT)."
        st.session_state.analyzing = False
    else:
        st.session_state.analyzing = True # Start analysis
        # Re-run to show spinner and disable button
        st.rerun() 

# Display error message if any
if st.session_state.error:
    st.error(st.session_state.error)
    # Exit early if there's an error - don't proceed with chart or analysis
    st.stop()

# This block runs if we have a valid ticker (no errors) (after the rerun from submit)
# Display the chart in Streamlit
if st.session_state.ticker:
    chart_data = get_stock_dataframe(st.session_state.ticker)
    if chart_data is not None:
        fig = show_candlestick_chart(chart_data, st.session_state.ticker)
        st.plotly_chart(fig, use_container_width=True)

        # Optional: Show the data table
        if st.checkbox("Show raw data"):
            st.dataframe(chart_data)
    else:
        # If no data is returned, set error state, set analyzing state and stop further processing
        st.session_state.error = "❌ Không thể tải dữ liệu cổ phiếu. Vui lòng kiểm tra mã cổ phiếu hoặc thử lại sau."
        st.session_state.analyzing = False
        st.error(st.session_state.error)
        st.rerun()
        st.stop()

# Only proceed with analysis if analyzing flag is true and we have no errors
if st.session_state.analyzing:
    with st.spinner(f"⏳ Các AI Agents đang tổng hợp và phân tích mã {st.session_state.ticker}... Thời gian chờ có thể lên tới 2-3 phút."):
        response_data = get_response(st.session_state.ticker)

    if response_data and response_data.get("status") == "error":
        st.session_state.error = f"❌ {response_data.get('error', 'Đã xảy ra lỗi không xác định trong quá trình phân tích.')}"
        st.session_state.analyzing = False
        st.error(st.session_state.error)
        st.stop()
    elif response_data:
        st.session_state.result = response_data
    else:
        st.session_state.error = "❌ Không nhận được phản hồi từ hệ thống phân tích."
        st.session_state.analyzing = False
        st.error(st.session_state.error)
        st.stop()

    st.session_state.analyzing = False # Analysis finished
    st.rerun() # Rerun to update UI based on new state (result or error)

# Display result if available, and analysis is not in progress
if st.session_state.result and not st.session_state.analyzing:
    result = st.session_state.result
    
    st.markdown("---") # Visual separator
    
    # Using columns for layout
    col1, col2 = st.columns([0.8, 1.2]) # Adjusted column ratio for better balance

    with col1:
        # Display the ticker prominently using st.subheader
        st.subheader(f"Mã: {result.get('stock_ticker', 'N/A')}", anchor=False)
        
        # Display the investment decision using Streamlit's colored message boxes
        decision = result.get('decision', 'N/A')
        if decision and isinstance(decision, str): # Ensure decision is a non-empty string
            decision_lower = decision.lower()
            if "mua" in decision_lower:
                st.success(f"**Khuyến nghị: {decision.upper()}** 👍")
            elif "bán" in decision_lower: # More flexible check for "Bán"
                st.error(f"**Khuyến nghị: {decision.upper()}** 👎")
            else: # For "Trung lập" or other neutral decisions
                st.warning(f"**Khuyến nghị: {decision.upper()}** ⚖️")
        else:
            st.info("**Khuyến nghị: Không có**")


    with col2:
        # Display company name, industry, and analysis date
        st.markdown(f"**Tên công ty:** {result.get('full_name', 'Không có thông tin')}")
        st.caption(f"**Ngành:** {result.get('industry', 'N/A')}")
        st.caption(f"**Ngày phân tích:** {result.get('today_date', 'N/A')}")
        if "giữ" in decision_lower:
            buy_price = result.get('buy_price')
            sell_price = result.get('sell_price')
            
            if isinstance(buy_price, (int, float)) and buy_price > 0:
                st.caption(f"Giá mua khuyến nghị: {buy_price:,.0f} VND")
            else:
                st.caption('Không có giá mua khuyến nghị.')
                
            if isinstance(sell_price, (int, float)) and sell_price > 0:
                st.caption(f"Giá bán khuyến nghị: {sell_price:,.0f} VND")
            else:
                st.caption('Không có giá bán khuyến nghị.')

    st.markdown("---") # Visual separator
    st.markdown("### 📝 Phân tích chi tiết")

    # Using expanders for different analysis sections
    with st.expander("**🌍 Phân tích thị trường vĩ mô**", expanded=False):
        st.write(result.get('macro_reasoning', 'Không có dữ liệu phân tích thị trường.'))

    with st.expander("**🏢 Phân tích cơ bản (Doanh nghiệp)**", expanded=False):
        st.write(result.get('fund_reasoning', 'Không có dữ liệu phân tích cơ bản.'))

    with st.expander("**📊 Phân tích kĩ thuật**", expanded=False):
        st.write(result.get('tech_reasoning', 'Không có dữ liệu phân tích kĩ thuật.'))

# ---  Disclaimer Section ---
st.markdown("---") # Visual separator
disclaimer_text = """
Dự án này được phát triển với mục đích chính là học tập và nghiên cứu về các công nghệ Large Language Model (LLM), Prompt Engineering và CrewAI framework, cũng như ứng dụng chúng vào việc phân tích cổ phiếu một cách tự động.

Các báo cáo và thông tin phân tích được **VN Stock Advisor** tổng hợp từ nhiều nguồn dữ liệu công khai trên Internet và được xử lý, phân tích bởi trí tuệ nhân tạo (AI). Do đó, tất cả các quan điểm, nhận định, luận điểm, và khuyến nghị mua/bán/nắm giữ cổ phiếu mà **VN Stock Advisor** đưa ra chỉ mang tính chất tham khảo, không cấu thành lời khuyên đầu tư chính thức.

Người dùng cần tự chịu trách nhiệm cho các quyết định đầu tư của mình. **VN Stock Advisor** và người phát triển không chịu trách nhiệm đối với bất kỳ khoản tổn thất hoặc thiệt hại nào phát sinh từ việc sử dụng các thông tin và báo cáo phân tích này. Hãy luôn tham khảo ý kiến từ các chuyên gia tài chính có chứng chỉ trước khi đưa ra bất kỳ quyết định đầu tư nào.
"""
# Using st.info to display the disclaimer in a styled box
st.caption(disclaimer_text)

# --- Footer ---
st.markdown("---")  # Visual separator
st.markdown("\n")  # Add some spacing
st.markdown(":copyright: 2025 Dương Anh Minh. All Rights Reserved.")
st.markdown("Liên hệ: [My github](https://github.com/abcxyz91/vn_stock_advisor)")