# スレッドで定期的にリソース状況を確認してStreamlitで可視化する
import streamlit as st
import psutil
import threading
import time
import pandas as pd

# リソース状況を定期的に取得するスレッド
class ResourceMonitor(threading.Thread):
    def __init__(self):
        super().__init__()
        self.cpu_usage = []
        self.memory_usage = []
        self.process_count = []
        self.python_process_count = []
        self.terminate = False

    def run(self):
        while not self.terminate:
            # 0.1秒ごとにCPUとメモリの使用率、スレッド数を取得する
            self.cpu_usage.append(psutil.cpu_percent())
            self.memory_usage.append(psutil.virtual_memory().percent)
            self.process_count.append(len(psutil.pids()))
            self.python_process_count.append(len([p.info for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower()]))

            # 直近300秒＝3,000回分だけ保持する
            if len(self.cpu_usage) > 3000:
                self.cpu_usage.pop(0)
                self.memory_usage.pop(0)
                self.process_count.pop(0)
                self.python_process_count.pop(0)

            time.sleep(0.1)

# トグルボタンで監視の開始・停止を切り替える
st.title("Resource Monitor")
start_monitoring = st.toggle("Start Monitoring", value=False)

# 現在の数はここに表示する
ph1 = st.empty()
ph2 = st.empty()

# スレッドのインスタンスをセッション状態に保存する
if start_monitoring and st.session_state.get("thread") is None:
    st.session_state.thread = ResourceMonitor()
    st.session_state.thread.daemon = True
    st.session_state.thread.start()
elif not start_monitoring and st.session_state.get("thread") is not None:
    st.session_state.thread.terminate = True
    st.session_state.thread = None

# グラフを描画するfragment
@st.fragment(run_every="3s")
def update_charts():
    # グラフの描画はPlotlyを使う
    import plotly.graph_objects as go

    # 最新データのX軸値は0、1秒前が-1.0、2秒前が-2.0、...、300秒前が-300.0となる
    len_x = len(st.session_state.thread.cpu_usage)
    x = [round((i - len_x + 1) * 0.1, 1) for i in range(len_x)]

    # CPUとメモリの使用率をPlotlyで描画する。デフォルトの最大値を100%にする
    fig1 = go.Figure()
    fig1.add_trace(
        go.Scatter(
            x=x,
            y=st.session_state.thread.cpu_usage,
            mode='lines',
            name='CPU usage (%)',
            line=dict(color='blue')
        )
    )
    fig1.add_trace(
        go.Scatter(
            x=x,
            y=st.session_state.thread.memory_usage,
            mode='lines',
            name='Memory usage (%)',
            line=dict(color='red')
        )
    )
    fig1.update_layout(
        title='CPU and Memory usage',
        xaxis_title='Time (seconds)',
        yaxis_title='Usage (%)',
        yaxis=dict(range=[0, 100]),
        legend=dict(x=0, y=1)
    )
    ph1.plotly_chart(fig1, use_container_width=True)

    # プロセス数とPythonプロセス数をPlotlyで描画する
    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=x,
            y=st.session_state.thread.process_count,
            mode='lines',
            name='Total processes',
            line=dict(color='green')
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=x,
            y=st.session_state.thread.python_process_count,
            mode='lines',
            name='Python processes',
            line=dict(color='orange')
        )
    )
    fig2.update_layout(
        title='Process counts',
        xaxis_title='Time (seconds)',
        yaxis_title='Count',
        legend=dict(x=0, y=1)
    )
    ph2.plotly_chart(fig2, use_container_width=True)

# グラフを描画する
if start_monitoring:
    update_charts()
