# --------------------------------------------------------------
# Homepage.py – CRM Productivity Dashboard (FINAL POLISH)
# --------------------------------------------------------------
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
import numpy as np

st.set_page_config(page_title="GEOX Productivity", page_icon="", layout="wide")



# ------------------------------------------------------------------
# 1. MONTH MAPPING - CURRENT MONTH FIRST
# ------------------------------------------------------------------
month_mapping = {
    "November 2025": "2025-11.xlsx",
    "October 2025": "2025-10.xlsx",
    "Septembre 2025": "2025-09.xlsx",
    
}

# Default to current month - DYNAMIC APPROACH
current_month_num = datetime.now().month
current_year = datetime.now().year

# Create a mapping of month numbers to month names
month_number_to_name = {
    10: "October 2025",
    11: "November 2025",
    09: "Septembre 2025",
}

# Set default month based on current month, fallback to November if current month not in mapping
default_month = month_number_to_name.get(current_month_num, "November 2025")
# ------------------------------------------------------------------
# 2. SIDEBAR & SESSION STATE
# ------------------------------------------------------------------
if 'selected_month' not in st.session_state:
    st.session_state.selected_month = default_month
if 'selected_agent' not in st.session_state:
    st.session_state.selected_agent = None
if 'agent_sheets' not in st.session_state:
    st.session_state.agent_sheets = None
if 'file_path' not in st.session_state:
    st.session_state.file_path = None
if 'team_averages' not in st.session_state:
    st.session_state.team_averages = None
if 'overall_raw' not in st.session_state:
    st.session_state.overall_raw = None
if 'totals' not in st.session_state:
    st.session_state.totals = {}

with st.sidebar:
    st.image("geox.png", width=100)
    
    selected_month = st.selectbox(
        "",
        options=list(month_mapping.keys()),
        index=list(month_mapping.keys()).index(st.session_state.selected_month),
        key="month_selector"
    )

    # Reset on month change
    if selected_month != st.session_state.selected_month:
        for key in ['selected_month', 'selected_agent', 'agent_sheets', 'file_path', 'team_averages', 'overall_raw', 'totals']:
            if key in st.session_state:
                st.session_state[key] = None if key != 'selected_month' else selected_month
        st.rerun()

    
    st.subheader("")

# ------------------------------------------------------------------
# 3. LOAD EXCEL DATA
# ------------------------------------------------------------------
data_dir = "data"
file_path = os.path.join(data_dir, month_mapping[selected_month])

if not os.path.exists(file_path):
    st.error(f"File not found: `{month_mapping[selected_month]}`")
    st.info("Please place the Excel file in the `data/` folder.")
    st.stop()

# Load only if file changed or data missing
if st.session_state.file_path != file_path or st.session_state.overall_raw is None:
    with st.spinner(f"Loading {selected_month} data..."):
        try:
            excel = pd.ExcelFile(file_path)
            skip_sheets = {"DB zammad", "db hours", "MIX Zammad with HRs", "Regalas"}
            valid_sheets = [s for s in excel.sheet_names if s not in skip_sheets]
            if not valid_sheets:
                st.error("No valid sheets found.")
                st.stop()

            overall_sheet = valid_sheets[0]
            agent_sheets = sorted(valid_sheets[1:])

            # --- Load Overall Sheet ---
            overall_df = pd.read_excel(file_path, sheet_name=overall_sheet, header=None)

            # KPI totals are ALWAYS in the last row
            last_row_idx = len(overall_df) - 1
            
            # Extract totals from the LAST ROW
            def safe_float(val, default=0.0):
                try:
                    return float(val) if pd.notna(val) else default
                except:
                    return default

            total_touch = safe_float(overall_df.iloc[last_row_idx, 1])
            total_solved = safe_float(overall_df.iloc[last_row_idx, 2])
            total_hours = safe_float(overall_df.iloc[last_row_idx, 3])
            avg_solved_hour = safe_float(overall_df.iloc[last_row_idx, 4])
            avg_touch_hour = safe_float(overall_df.iloc[last_row_idx, 5])
            avg_conversion = safe_float(overall_df.iloc[last_row_idx, 6])

            # Store totals in session state
            st.session_state.totals = {
                "total_touch": total_touch,
                "total_solved": total_solved,
                "total_hours": total_hours,
                "avg_solved_hour": avg_solved_hour,
                "avg_touch_hour": avg_touch_hour,
                "avg_conversion": avg_conversion
            }

            # Continue with existing overall data processing (skip the last row which contains totals)
            overall_raw = pd.read_excel(file_path, sheet_name=overall_sheet, skiprows=6, usecols=range(7))
            overall_raw.columns = ["Agent","Touch","Solved","Hours","Solved_by_Hour","Touch_by_Hour","Solved_vs_Touch_%"]
            overall_raw = overall_raw.dropna(subset=["Agent"])
            overall_raw = overall_raw[overall_raw["Agent"] != "Suma total"]  # Remove the totals row

            def clean_agent(name):
                if pd.isna(name): return name
                s = str(name).strip()
                if "@" not in s: return s
                return s.split("@")[0].replace(".", " ").title()
            overall_raw["Agent"] = overall_raw["Agent"].apply(clean_agent)

            num_cols = ["Touch","Solved","Hours","Solved_by_Hour","Touch_by_Hour","Solved_vs_Touch_%"]
            overall_raw[num_cols] = overall_raw[num_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

            team_averages = {
                "avg_touch": overall_raw["Touch"].mean(),
                "avg_solved": overall_raw["Solved"].mean(),
                "avg_hours": overall_raw["Hours"].mean(),
                "avg_solved_by_hour": overall_raw["Solved_by_Hour"].mean(),
                "avg_touch_by_hour": overall_raw["Touch_by_Hour"].mean(),
                "avg_conversion": overall_raw["Solved_vs_Touch_%"].mean()
            }

            # Cache in session state
            st.session_state.update({
                "file_path": file_path,
                "excel": excel,
                "overall_sheet": overall_sheet,
                "agent_sheets": agent_sheets,
                "team_averages": team_averages,
                "overall_raw": overall_raw
            })
            
        except Exception as e:
            st.error(f"Error loading file: {e}")
            st.stop()

# Unpack session state
excel = st.session_state.excel
overall_sheet = st.session_state.overall_sheet
agent_sheets = st.session_state.agent_sheets
team_averages = st.session_state.team_averages
overall_raw = st.session_state.overall_raw
totals = st.session_state.totals

# ------------------------------------------------------------------
# 4. AGENT SELECTOR
# ------------------------------------------------------------------
with st.sidebar:
    if agent_sheets:
        agent_options = ["Overall View"] + agent_sheets  # CHANGED: "-- Select Agent --" to "Overall View"
        default_index = 0
        if st.session_state.selected_agent in agent_sheets:
            default_index = agent_sheets.index(st.session_state.selected_agent) + 1

        selected_agent = st.selectbox(
            "Choose Agent",
            options=agent_options,
            index=default_index,
            key="agent_selector"
        )

        if selected_agent != "Overall View" and selected_agent != st.session_state.selected_agent:  # CHANGED
            st.session_state.selected_agent = selected_agent
            st.rerun()
        elif selected_agent == "Overall View" and st.session_state.selected_agent is not None:  # CHANGED
            st.session_state.selected_agent = None
            st.rerun()
    else:
        st.info("No agent sheets found.")

# ------------------------------------------------------------------
# 5. AGENT DETAIL VIEW
# ------------------------------------------------------------------

if st.session_state.selected_agent and st.session_state.selected_agent != "Overall View":  # CHANGED
    selected_agent_sheet = st.session_state.selected_agent
    
    # Find the agent's full name from the overview data
    def clean_for_match(name):
        if pd.isna(name): return ""
        return str(name).strip().lower().replace(".", " ").replace("@", " ").replace("-", " ")
    
    target_agent_clean = clean_for_match(selected_agent_sheet)
    
    # Search for the agent in the overview data to get the full formatted name
    full_agent_name = selected_agent_sheet  # Default to sheet name if not found
    for idx, row in overall_raw.iterrows():
        agent_name_clean = clean_for_match(row["Agent"])
        if target_agent_clean in agent_name_clean or agent_name_clean in target_agent_clean:
            full_agent_name = row["Agent"]  # Use the formatted name from overview
            break
    
    # If we found a match in overview, use that formatted name, otherwise clean the sheet name
    if full_agent_name != selected_agent_sheet:
        formatted_agent_name = full_agent_name
    else:
        # Fallback: clean the sheet name
        def clean_agent_display(name):
            if pd.isna(name): return name
            s = str(name).strip()
            if "@" not in s: return s
            return s.split("@")[0].replace(".", " ").title()
        formatted_agent_name = clean_agent_display(selected_agent_sheet)
    
    st.title(f"{formatted_agent_name}")

    with st.spinner(f"Loading data for {formatted_agent_name}..."):
        df = pd.read_excel(file_path, sheet_name=selected_agent_sheet, header=None).fillna("")

    def clean_numeric(x):
        if pd.isna(x): return 0.0
        s = str(x).strip().replace(",", ".").replace("%", "").replace(" ", "")
        try:
            return float(s)
        except:
            return 0.0

    metrics = {}

    # Extract rows by label
    for idx in df.index:
        first_col = str(df.iloc[idx, 0]).strip()
        row = df.iloc[idx].apply(clean_numeric)

        if first_col == 'Touch':
            metrics["total_touch"] = float(row.iloc[-1])
            metrics["touch_by_day"] = row.iloc[1:-1].tolist()
        elif first_col == 'Solved':
            metrics["total_solved"] = float(row.iloc[-1])
            metrics["solved_by_day"] = row.iloc[1:-1].tolist()
        elif first_col == 'Hours by Day':
            metrics["total_hours"] = float(row.iloc[-1])
            metrics["hours_by_day"] = row.iloc[1:-1].tolist()
        elif first_col == 'Solved by Hour':
            metrics["total_solved_by_hour"] = float(row.iloc[-1])
            metrics["solved_by_hour_by_day"] = row.iloc[1:-1].tolist()
        elif first_col == 'Touch by Hour':
            metrics["total_touch_by_hour"] = float(row.iloc[-1])
            metrics["touch_by_hour_by_day"] = row.iloc[1:-1].tolist()

    # Get conversion from overall_raw using the same matching logic
    agent_row = overall_raw[overall_raw["Agent"].apply(lambda x: target_agent_clean in clean_for_match(x) or clean_for_match(x) in target_agent_clean)]
    agent_conversion = agent_row["Solved_vs_Touch_%"].iloc[0] if not agent_row.empty else 0.0

    if agent_conversion == 0 and metrics.get("total_touch", 0) > 0:
        agent_conversion = metrics["total_solved"] / metrics["total_touch"]
    metrics["total_conversion"] = agent_conversion

    # Daily conversion
    conv_row = df[df.iloc[:, 0].astype(str).str.strip() == '% Solved vs Touch']
    if not conv_row.empty:
        daily_conv = []
        for col in range(1, len(conv_row.columns)-1):
            daily_val = clean_numeric(conv_row.iloc[0, col])
            if daily_val > 1:
                daily_conv.append(daily_val / 100.0)
            else:
                daily_conv.append(daily_val)
        metrics["conversion_by_day"] = daily_conv
    else:
        t = metrics.get("touch_by_day", [])
        s = metrics.get("solved_by_day", [])
        metrics["conversion_by_day"] = [s[i]/t[i] if t[i] > 0 else 0.0 for i in range(len(t))]

    # Set defaults
    defaults = {
        "total_touch": 0, "total_solved": 0, "total_hours": 0,
        "total_solved_by_hour": 0, "total_touch_by_hour": 0, "total_conversion": 0
    }
    for k, v in defaults.items():
        metrics.setdefault(k, v)

    # --- Extract Dates from Row 32 ---
    dates = []
    if len(df) > 31:
        date_row = df.iloc[31, 1:-1]  # Row 32, exclude first and last
        for col_idx, val in enumerate(date_row):
            if pd.isna(val):
                dates.append(f"Day {col_idx + 1}")
                continue
            try:
                if isinstance(val, datetime):
                    date_str = val.strftime("%d/%m")
                else:
                    date_str = str(val).strip()
                    if ' ' in date_str:
                        date_str = date_str.split()[0]
                    if '-' in date_str:
                        parts = date_str.split('-')
                        if len(parts) == 3:
                            # Assume YYYY-MM-DD, take DD/MM
                            day = parts[2].split(' ')[0]  # Remove time if present
                            month = parts[1]
                            date_str = f"{day}/{month}"
                    elif '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) >= 2:
                            # Assume DD/MM/YYYY
                            day = parts[0]
                            month = parts[1]
                            date_str = f"{day}/{month}"
                dates.append(date_str)
            except:
                dates.append(f"Day {col_idx + 1}")
    else:
        n = len(metrics.get("touch_by_day", []))
        dates = [f"Day {i+1}" for i in range(n)]

    days = dates[:len(metrics.get("touch_by_day", []))]

    # --- KPI Function ---
        # --- KPI Function with Rank ---
        # --- KPI Function with Correct Rank ---
    def kpi_with_rank(label, value, avg_key, data_column, is_percent=False, is_decimal=False):
        avg = team_averages[avg_key]
        delta = value - avg
        
        # Calculate rank compared to other agents
        # For all metrics, higher values are better (more touches, more solved, higher rates)
        better_agents = (overall_raw[data_column] > value).sum()
        rank = better_agents + 1
        total_agents = len(overall_raw)

        if is_percent:
            value_str = f"{value:.1%}"
            avg_str = f"{avg:.1%}"
            delta_str = f"{delta:+.1%}"
        elif is_decimal:
            value_str = f"{value:.2f}"
            avg_str = f"{avg:.2f}"
            delta_str = f"{delta:+.2f}"
        else:
            value_str = f"{value:,.0f}"
            avg_str = f"{avg:,.0f}"
            delta_str = f"{delta:+,.0f}"

        st.metric(label, value_str, delta_str, delta_color="normal")
        st.caption(f"Team avg: {avg_str}")
        st.caption(f"Rank: #{rank}/{total_agents}")

    # --- KPIs ---
        # --- KPIs with Rank ---
        # --- KPIs with Correct Rank ---
    cols = st.columns(6)
    with cols[0]: kpi_with_rank("Total Touched", metrics["total_touch"], "avg_touch", "Touch")
    with cols[1]: kpi_with_rank("Total Solved", metrics["total_solved"], "avg_solved", "Solved")
    with cols[2]: kpi_with_rank("Total Hours", metrics["total_hours"], "avg_hours", "Hours")
    with cols[3]: kpi_with_rank("Avg Solved/Hour", metrics["total_solved_by_hour"], "avg_solved_by_hour", "Solved_by_Hour", is_decimal=True)
    with cols[4]: kpi_with_rank("Avg Touch/Hour", metrics["total_touch_by_hour"], "avg_touch_by_hour", "Touch_by_Hour", is_decimal=True)
    with cols[5]: kpi_with_rank("Quality", metrics["total_conversion"], "avg_conversion", "Solved_vs_Touch_%", is_percent=True)

    st.markdown("---")

    # --- Charts ---
    if len(metrics.get("touch_by_day", [])) > 0:
        vol = pd.DataFrame({"Day": days, "Touched": metrics["touch_by_day"], "Solved": metrics["solved_by_day"]})
        fig = go.Figure()
        fig.add_bar(x=vol["Day"], y=vol["Touched"], name="Touched", marker_color="#4FC3F7")
        fig.add_bar(x=vol["Day"], y=vol["Solved"], name="Solved", marker_color="#81C784")
        fig.update_layout(title="Daily Volume", barmode="group", height=350)
        st.plotly_chart(fig, use_container_width=True)

    if len(metrics.get("solved_by_hour_by_day", [])) > 0:
        eff = pd.DataFrame({"Day": days, "Solved/Hour": metrics["solved_by_hour_by_day"], "Touch/Hour": metrics["touch_by_hour_by_day"]})
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=eff["Day"], 
            y=eff["Touch/Hour"], 
            fill='tozeroy',
            fillcolor='rgba(0, 112, 192, 0.2)',   # Very subtle blue
            line=dict(color='#0070C0', width=2.5), # Corporate blue
            name='Touch/Hour',
            mode='lines'
        ))
        
        # Solved/Hour - Professional green
        fig.add_trace(go.Scatter(
            x=eff["Day"], 
            y=eff["Solved/Hour"], 
            fill='tozeroy',
            fillcolor='rgba(0, 176, 80, 0.2)',    # Very subtle green
            line=dict(color='#00B050', width=2.5), # Corporate green
            name='Solved/Hour',
            mode='lines'
        ))
        
        fig.update_layout(
            title="Efficiency",
            height=350, 
            yaxis_title="Tickets / Hour",
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family="Arial", size=12),
            showlegend=True,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)

    if len(metrics.get("conversion_by_day", [])) > 0:
        conv = pd.DataFrame({"Day": days, "Conversion": metrics["conversion_by_day"]})
        fig = go.Figure()
        fig.add_scatter(x=conv["Day"], y=conv["Conversion"], mode='lines+markers', line_color='Orange', name='Quality')
        fig.update_layout(title="Quality Trend", height=350, yaxis_tickformat=".1%", yaxis_title="Quality")
        st.plotly_chart(fig, use_container_width=True)

    if "solved_by_day" in metrics and "hours_by_day" in metrics:
        sh = [s/h if h > 0 else 0 for s, h in zip(metrics["solved_by_day"], metrics["hours_by_day"])]
        perf = pd.DataFrame({"Day": days, "S/H": sh})
        fig = px.line(perf, x="Day", y="S/H", title="Solved per Hour Trend", markers=True, color_discrete_sequence=["#00B050"])
        fig.update_layout(height=350, yaxis_title="Solved / Hour")
        st.plotly_chart(fig, use_container_width=True)

    # Daily Table
    required = ["touch_by_day", "solved_by_day", "hours_by_day", "solved_by_hour_by_day", "touch_by_hour_by_day", "conversion_by_day"]
    if all(k in metrics and len(metrics[k]) > 0 for k in required):
        table = pd.DataFrame({
            "Day": days,
            "Hours": [f"{h:.1f}" for h in metrics["hours_by_day"]],
            "Touched": [f"{t:.0f}" for t in metrics["touch_by_day"]],
            "Solved": [f"{s:.0f}" for s in metrics["solved_by_day"]],
            "S/H": [f"{v:.2f}" for v in metrics["solved_by_hour_by_day"]],
            "T/H": [f"{v:.2f}" for v in metrics["touch_by_hour_by_day"]],
            "Quality": [f"{c:.1%}" for c in metrics["conversion_by_day"]]
        })
        st.subheader("Daily Metrics")
        st.dataframe(table, use_container_width=True)

        

# ------------------------------------------------------------------
# 6. MAIN DASHBOARD
# ------------------------------------------------------------------
else:  # This runs when no agent is selected (Overall View)
    st.title(f"Productivity {selected_month}")
   

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Touched", f"{totals['total_touch']:,.0f}")
    c2.metric("Total Solved", f"{totals['total_solved']:,.0f}")
    c3.metric("Total Hours", f"{totals['total_hours']:.1f}")
    c4.metric("Avg Solved/Hour", f"{totals['avg_solved_hour']:.2f}")
    c5.metric("Avg Touch/Hour", f"{totals['avg_touch_hour']:.2f}")
    c6.metric("Avg Quality", f"{totals['avg_conversion']:.1%}")

   

    def hover(row):
        insight = "Star" if row["Solved_by_Hour"] >= 7 else "Strong" if row["Solved_by_Hour"] >= 5 else "Good" if row["Solved_by_Hour"] >= 4 else "Needs help"
        conv = "Excellent closer" if row["Solved_vs_Touch_%"] >= 0.7 else "Solid" if row["Solved_vs_Touch_%"] >= 0.6 else "Improve"
        return f"<b>{row['Agent']}</b><br>Touch: {row['Touch']:,}<br>Solved: {row['Solved']:,}<br>Hours: {row['Hours']:.1f}<br>S/H: {row['Solved_by_Hour']:.2f}<br>Quality: {row['Solved_vs_Touch_%']:.1%}<br><b>{insight} | {conv}</b>"

    overall_raw["hover"] = overall_raw.apply(hover, axis=1)

    # Bar Chart
    df_bar = overall_raw.sort_values("Solved_by_Hour", ascending=False)
    team_avg = overall_raw["Solved_by_Hour"].mean()
    
    fig1 = px.bar(df_bar, x="Agent", y="Solved_by_Hour", title="Solved per hour", color="Solved_by_Hour",
                  text="Solved_by_Hour", hover_data={"hover": True})
    
    # Add average line with better styling
    fig1.add_hline(y=team_avg, line_dash="dash", line_color="red", line_width=3,
                   annotation_text=f"Team Average: {team_avg:.2f}",
                   annotation_position="top right",
                   annotation_font_size=14,
                   annotation_font_color="red")
    
    fig1.update_traces(
        texttemplate='%{text:.2f}', 
        textposition='outside', 
        hovertemplate="%{customdata[0]}",
        showlegend=False  # Remove legend from traces
    )
    df_bar = overall_raw.sort_values("Solved_by_Hour", ascending=False)
    team_avg = overall_raw["Solved_by_Hour"].mean()
    
    fig1 = px.bar(df_bar, x="Agent", y="Solved_by_Hour", title="Solved Per Hour", color="Solved_by_Hour",
                  text="Solved_by_Hour", hover_data={"hover": True})
    
    # Add average line with better styling
    fig1.add_hline(y=team_avg, line_dash="dash", line_color="red", line_width=3,
                   annotation_text=f"Team Average: {team_avg:.2f}",
                   annotation_position="top right",
                   annotation_font_size=14,
                   annotation_font_color="red")
    
    fig1.update_traces(
        texttemplate='%{text:.2f}', 
        textposition='outside', 
        hovertemplate="%{customdata[0]}",
        showlegend=False
    )
    fig1.update_layout(
        xaxis_tickangle=-45, 
        height=600,
        yaxis_title="Solved Per Hour",
        showlegend=False,
        coloraxis_showscale=False,  # This removes the color bar legend
        xaxis=dict(showgrid=False),  # Remove vertical grid lines
        yaxis=dict(showgrid=False)   # Remove horizontal grid lines
    )
    st.plotly_chart(fig1, use_container_width=True)



  

    # -------------------------------------------------
    # 1. Data range for color scaling
    # -------------------------------------------------
    touch_vals = overall_raw["Touch"]
    c_min = touch_vals.min()
    c_max = touch_vals.max()

    st.markdown("")
    

        # -------------------------------------------------
    # 2. Build figure
    # -------------------------------------------------
    fig2 = go.Figure()

    for idx, row in overall_raw.iterrows():
        # Bubble size (relative to mean, clamped)
        rel_size = row["Touch"] / overall_raw["Touch"].mean() * 100
        bubble_size = max(60, min(200, rel_size))

        # Text inside bubble: First name + Touch count (on new line)
        bubble_text = f"{row['Agent'].split()[0]}<br>{row['Touch']:,}"

        fig2.add_trace(go.Scatter(
            x=[idx],
            y=[row["Touch"]],
            mode="markers+text",
            marker=dict(
                size=bubble_size,
                color=[row["Touch"]],        # scalar in list → correct mapping
                colorscale="Blues",          # pure blue: light → dark
                cmin=c_min,
                cmax=c_max,
                opacity=0.85,
                line=dict(width=0)           # NO BORDER
            ),
            text=[bubble_text],
            textposition="middle center",
            textfont=dict(color="white", size=11, family="Arial"),
            name=row["Agent"],
            showlegend=False,                # hide legend per trace
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Touch: %{y:,}<br>"
                "Solved: %{customdata[0]:,}<br>"
                "Solved/Hour: %{customdata[1]:.2f}<extra></extra>"
            ).replace("%{text}", row["Agent"]),  # full name in hover
            customdata=[[row["Solved"], row["Solved_by_Hour"]]]
        ))

    # -------------------------------------------------
    # 3. Layout – clean & professional
    # -------------------------------------------------
    fig2.update_layout(
        title="<b>Touch Volume</b>",
        xaxis=dict(
            title="Agents",
            showgrid=False,
            showticklabels=False,
            zeroline=False
        ),
        yaxis=dict(
            title="Total Touched",
            showgrid=False,  # REMOVED GRID
            zeroline=False
        ),
        height=600,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12),
        showlegend=False,                    # FINAL: no legend at all
        margin=dict(l=60, r=60, t=80, b=60)
    )

    # -------------------------------------------------
    # 4. Display in Streamlit
    # -------------------------------------------------
    st.plotly_chart(fig2, use_container_width=True)

    # Conversion Rate Performance - Blue Color Scale
        # Conversion Rate Performance - Blue Color Scale
    df_sorted = overall_raw.sort_values("Solved_vs_Touch_%", ascending=True)
    
    fig3 = go.Figure()
    
    # Add horizontal bars with blue color scale (strong to light)
    fig3.add_trace(go.Bar(
        y=df_sorted["Agent"],
        x=df_sorted["Solved_vs_Touch_%"],
        orientation='h',
        marker=dict(
            color=df_sorted["Solved_vs_Touch_%"],
            colorscale='Blues',  # Strong blue to light blue
            cmin=df_sorted["Solved_vs_Touch_%"].min(),
            cmax=df_sorted["Solved_vs_Touch_%"].max(),
            showscale=False  # REMOVE COLOR BAR LEGEND
        ),
        hovertemplate="<b>%{y}</b><br>" +
                     "Conversion Rate: <b>%{x:.1%}</b><br>" +
                     "Touched: %{customdata[0]:,}<br>" +
                     "Solved: %{customdata[1]:,}<br>" +
                     "Solved/Hour: %{customdata[2]:.2f}<br>" +
                     "<extra></extra>",
        customdata=np.column_stack((
            df_sorted["Touch"],
            df_sorted["Solved"], 
            df_sorted["Solved_by_Hour"]
        )),
        showlegend=False
    ))
    
    # Add average line with same red dash style and red text
    avg_conversion = df_sorted["Solved_vs_Touch_%"].mean()
    fig3.add_vline(x=avg_conversion, line_dash="dash", line_color="red", line_width=2,
                   annotation_text=f"Team Average: {avg_conversion:.1%}",
                   annotation_position="top right",
                   annotation_font_color="red")  # Add this line for red text
    
    # Match the exact layout styling from figure 1
    fig3.update_layout(
        title="Quality",
        xaxis_title="Quality",
        yaxis_title="Agents",
        xaxis_tickformat=".0%",
        height=max(600, len(df_sorted) * 40),
        showlegend=False,
        plot_bgcolor='white',
        xaxis=dict(showgrid=False),  # REMOVED GRID
        yaxis=dict(showgrid=False, categoryorder='total ascending')  # REMOVED GRID
    )
    
    st.plotly_chart(fig3, use_container_width=True)